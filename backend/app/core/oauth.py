from authlib.integrations.starlette_client import OAuth

from app.core.config import settings

oauth = OAuth()
oauth.register(
    name="oidc",
    client_id=settings.AuthClientId,
    client_secret=settings.AuthClientSecret,
    server_metadata_url=f"{settings.AuthAuthority.rstrip('/')}/.well-known/openid-configuration",
    client_kwargs={"scope": "openid profile email"},
)

if settings.YandexClientId:
    # Yandex ID is plain OAuth 2.0 (no OIDC discovery); the profile comes from login.yandex.ru/info.
    oauth.register(
        name="yandex",
        client_id=settings.YandexClientId,
        client_secret=settings.YandexClientSecret,
        authorize_url="https://oauth.yandex.ru/authorize",
        access_token_url="https://oauth.yandex.ru/token",
        api_base_url="https://login.yandex.ru/",
        client_kwargs={"scope": "login:info login:email"},
    )

if settings.GoogleClientId:
    oauth.register(
        name="google",
        client_id=settings.GoogleClientId,
        client_secret=settings.GoogleClientSecret,
        server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
        client_kwargs={"scope": "openid email profile"},
    )


def enabled_providers() -> list[str]:
    """Sign-in providers offered to users, in display order."""
    providers = ["oidc"]
    if settings.YandexClientId:
        providers.append("yandex")
    if settings.GoogleClientId:
        providers.append("google")
    return providers
