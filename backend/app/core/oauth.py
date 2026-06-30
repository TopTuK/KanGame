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
