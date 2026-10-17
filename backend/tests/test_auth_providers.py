"""Yandex and Google sign-in: provider listing, login redirects and callbacks (providers mocked)."""
import httpx
import pytest
import pytest_asyncio
from sqlalchemy import select

from app.core.config import settings
from app.core.oauth import oauth
from app.models.user import User


@pytest_asyncio.fixture
async def anon_client(db_session):
    """Unauthenticated HTTP client against the FastAPI app (no startup hooks)."""
    from app.main import app

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        yield client


async def _user_by_sub(db_session, sub):
    result = await db_session.execute(select(User).where(User.sub == sub))
    return result.scalar_one_or_none()


@pytest.mark.asyncio
async def test_providers_lists_configured_providers(anon_client):
    resp = await anon_client.get("/api/auth/providers")
    assert resp.status_code == 200
    assert resp.json() == {"providers": ["oidc", "yandex", "google"]}


@pytest.mark.asyncio
async def test_providers_hides_unconfigured_provider(anon_client, monkeypatch):
    monkeypatch.setattr(settings, "GoogleClientId", "")
    resp = await anon_client.get("/api/auth/providers")
    assert resp.json() == {"providers": ["oidc", "yandex"]}

    resp = await anon_client.get("/auth/login/google")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_login_unknown_provider_404(anon_client):
    resp = await anon_client.get("/auth/login/github")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_login_yandex_redirects_to_yandex(anon_client):
    resp = await anon_client.get("/auth/login/yandex")
    assert resp.status_code == 302
    location = resp.headers["location"]
    assert location.startswith("https://oauth.yandex.ru/authorize")
    assert httpx.URL(location).params["redirect_uri"] == f"{settings.BASE_URL}{settings.YandexCallbackUrl}"


@pytest.mark.asyncio
async def test_yandex_callback_creates_prefixed_user(anon_client, db_session, monkeypatch):
    async def fake_token(request):
        return {"access_token": "yandex-token", "token_type": "bearer"}

    sent = []

    def info_endpoint(request: httpx.Request):
        sent.append(request)
        return httpx.Response(200, json={
            "id": "12345",
            "login": "ivan",
            "real_name": "Ivan Petrov",
            "default_email": "ivan@yandex.ru",
        })

    monkeypatch.setattr(oauth.yandex, "authorize_access_token", fake_token)
    # The real Authlib request goes through a mock transport, so the test sees the header actually sent.
    monkeypatch.setitem(oauth.yandex.client_kwargs, "transport", httpx.MockTransport(info_endpoint))

    resp = await anon_client.get(settings.YandexCallbackUrl)
    assert resp.status_code == 303
    assert "kangame_session" in resp.cookies

    assert len(sent) == 1
    assert sent[0].url.copy_with(query=None) == "https://login.yandex.ru/info"
    assert sent[0].url.params["format"] == "json"
    assert sent[0].headers["Authorization"] == "OAuth yandex-token"

    user = await _user_by_sub(db_session, "yandex:12345")
    assert user is not None
    assert user.name == "Ivan Petrov"
    assert user.email == "ivan@yandex.ru"


@pytest.mark.asyncio
async def test_google_callback_creates_prefixed_user(anon_client, db_session, monkeypatch):
    async def fake_token(request):
        return {"userinfo": {"sub": "g-777", "name": "Jane Doe", "email": "jane@gmail.com"}}

    monkeypatch.setattr(oauth.google, "authorize_access_token", fake_token)

    resp = await anon_client.get(settings.GoogleCallbackUrl)
    assert resp.status_code == 303
    assert "kangame_session" in resp.cookies

    user = await _user_by_sub(db_session, "google:g-777")
    assert user is not None
    assert user.name == "Jane Doe"
    assert user.email == "jane@gmail.com"
