from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    DATABASE_URL: str = "postgresql+asyncpg://kanban:kanban@db:5432/kanban"
    CORS_ORIGINS: list[str] = [
        "http://localhost", "http://localhost:80", "http://localhost:5173",
        "https://localhost:8000",
    ]

    AuthClientId: str
    AuthClientSecret: str
    AuthAuthority: str
    AuthCallbackUrl: str
    BACKEND_PUBLIC_URL: str = "https://localhost:8000"
    FRONTEND_URL: str = "http://localhost"
    SESSION_SECRET_KEY: str
    SESSION_COOKIE_SECURE: bool = False

    # Only for e2e tests: enables POST /api/dev/test-login to bypass OIDC.
    # Must stay false outside of test environments.
    ENABLE_TEST_LOGIN: bool = False

    class Config:
        env_file = ".env"


settings = Settings()
