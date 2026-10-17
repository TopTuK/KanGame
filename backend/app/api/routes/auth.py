from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.responses import RedirectResponse

from app.core.auth import get_current_user
from app.core.config import settings
from app.core.database import get_db
from app.core.oauth import enabled_providers, oauth
from app.core.username import resolve_initial_username
from app.models.user import User
from app.schemas.user import UserResponse, UserUpdate

router = APIRouter()

TEST_USER_SUB = "e2e-test-user"

# Social providers' callback paths. Their users' subs are prefixed with the
# provider name so they never collide with the organization OIDC subs.
SOCIAL_CALLBACKS = {
    "yandex": settings.YandexCallbackUrl,
    "google": settings.GoogleCallbackUrl,
}


async def _sign_in(request: Request, db: AsyncSession, sub: str, name: str | None, email: str | None):
    result = await db.execute(select(User).where(User.sub == sub))
    user = result.scalar_one_or_none()
    if user:
        user.email = email
        user.name = name
    else:
        user = User(sub=sub, email=email, name=name, username=resolve_initial_username(name, email))
        db.add(user)
    await db.flush()

    request.session["user_id"] = str(user.id)
    await db.commit()

    return RedirectResponse(settings.BASE_URL, status_code=303)


@router.get("/api/auth/providers")
async def providers():
    return {"providers": enabled_providers()}


@router.get("/auth/login")
async def login(request: Request):
    redirect_uri = f"{settings.BASE_URL}{settings.AuthCallbackUrl}"
    return await oauth.oidc.authorize_redirect(request, redirect_uri)


@router.get("/auth/login/{provider}")
async def login_social(provider: str, request: Request):
    if provider not in SOCIAL_CALLBACKS or provider not in enabled_providers():
        raise HTTPException(status_code=404, detail="Not found")
    redirect_uri = f"{settings.BASE_URL}{SOCIAL_CALLBACKS[provider]}"
    return await oauth.create_client(provider).authorize_redirect(request, redirect_uri)


@router.get("/auth/signin-oidc")
async def signin_callback(request: Request, db: AsyncSession = Depends(get_db)):
    token = await oauth.oidc.authorize_access_token(request)
    userinfo = token.get("userinfo")
    if not userinfo:
        userinfo = await oauth.oidc.userinfo(token=token)

    return await _sign_in(request, db, userinfo["sub"], userinfo.get("name"), userinfo.get("email"))


async def signin_yandex(request: Request, db: AsyncSession = Depends(get_db)):
    if "yandex" not in enabled_providers():
        raise HTTPException(status_code=404, detail="Not found")
    token = await oauth.yandex.authorize_access_token(request)
    # Yandex documents the "OAuth" auth scheme, not Bearer, so send the header ourselves.
    resp = await oauth.yandex.get(
        "info",
        params={"format": "json"},
        headers={"Authorization": f"OAuth {token['access_token']}"},
        withhold_token=True,
    )
    resp.raise_for_status()
    info = resp.json()

    name = info.get("real_name") or info.get("display_name") or info.get("login")
    return await _sign_in(request, db, f"yandex:{info['id']}", name, info.get("default_email"))


async def signin_google(request: Request, db: AsyncSession = Depends(get_db)):
    if "google" not in enabled_providers():
        raise HTTPException(status_code=404, detail="Not found")
    token = await oauth.google.authorize_access_token(request)
    userinfo = token.get("userinfo")
    if not userinfo:
        userinfo = await oauth.google.userinfo(token=token)

    return await _sign_in(request, db, f"google:{userinfo['sub']}", userinfo.get("name"), userinfo.get("email"))


router.add_api_route(settings.YandexCallbackUrl, signin_yandex, methods=["GET"])
router.add_api_route(settings.GoogleCallbackUrl, signin_google, methods=["GET"])


@router.post("/api/dev/test-login", response_model=UserResponse)
async def test_login(request: Request, db: AsyncSession = Depends(get_db)):
    """E2E-test-only login that bypasses OIDC. 404s unless ENABLE_TEST_LOGIN is set."""
    if not settings.ENABLE_TEST_LOGIN:
        raise HTTPException(status_code=404, detail="Not found")

    result = await db.execute(select(User).where(User.sub == TEST_USER_SUB))
    user = result.scalar_one_or_none()
    if not user:
        user = User(sub=TEST_USER_SUB, email="e2e@test.local", name="E2E Test User", username="E2E Test User")
        db.add(user)
        await db.flush()

    request.session["user_id"] = str(user.id)
    await db.commit()

    return user


@router.get("/api/auth/me", response_model=UserResponse)
async def me(current_user: User = Depends(get_current_user)):
    return current_user


@router.patch("/api/auth/me", response_model=UserResponse)
async def update_me(
    payload: UserUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    current_user.username = payload.username
    await db.commit()
    await db.refresh(current_user)
    return current_user


@router.post("/api/auth/logout")
async def logout(request: Request):
    request.session.clear()
    return {"status": "ok"}
