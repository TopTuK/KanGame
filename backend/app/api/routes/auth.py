from fastapi import APIRouter, Depends, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.responses import RedirectResponse

from app.core.auth import get_current_user
from app.core.config import settings
from app.core.database import get_db
from app.core.oauth import oauth
from app.models.user import User
from app.schemas.user import UserResponse

router = APIRouter()


@router.get("/auth/login")
async def login(request: Request):
    redirect_uri = f"{settings.BACKEND_PUBLIC_URL}{settings.AuthCallbackUrl}"
    return await oauth.oidc.authorize_redirect(request, redirect_uri)


@router.get("/auth/signin-oidc")
async def signin_callback(request: Request, db: AsyncSession = Depends(get_db)):
    token = await oauth.oidc.authorize_access_token(request)
    userinfo = token.get("userinfo")
    if not userinfo:
        userinfo = await oauth.oidc.userinfo(token=token)

    sub = userinfo["sub"]
    result = await db.execute(select(User).where(User.sub == sub))
    user = result.scalar_one_or_none()
    if user:
        user.email = userinfo.get("email")
        user.name = userinfo.get("name")
    else:
        user = User(sub=sub, email=userinfo.get("email"), name=userinfo.get("name"))
        db.add(user)
    await db.flush()

    request.session["user_id"] = str(user.id)
    await db.commit()

    return RedirectResponse(settings.FRONTEND_URL, status_code=303)


@router.get("/api/auth/me", response_model=UserResponse)
async def me(current_user: User = Depends(get_current_user)):
    return current_user


@router.post("/api/auth/logout")
async def logout(request: Request):
    request.session.clear()
    return {"status": "ok"}
