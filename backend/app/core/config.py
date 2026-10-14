from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    DATABASE_URL: str = "postgresql+asyncpg://kanban:kanban@db:5432/kanban"
    CORS_ORIGINS: list[str] = [
        "http://localhost", "http://localhost:80", "http://localhost:5173",
        "http://localhost:8000",
    ]

    AuthClientId: str
    AuthClientSecret: str
    AuthAuthority: str
    AuthCallbackUrl: str
    BASE_URL: str = "http://localhost"
    SESSION_SECRET_KEY: str
    SESSION_COOKIE_SECURE: bool = False

    # Only for e2e tests: enables POST /api/dev/test-login to bypass OIDC.
    # Must stay false outside of test environments.
    ENABLE_TEST_LOGIN: bool = False

    # AI agent player (Microsoft Agent Framework). The provider API key comes
    # from the user per run and is never stored.
    AGENT_ENABLED: bool = True
    AGENT_MAX_RUN_MINUTES: int = 30
    AGENT_DAY_TOOL_CALL_LIMIT: int = 40
    # Defaults pre-filled in the agent form: OpenRouter + OpenAI's fast, cheap
    # GPT-6 Luna. AGENT_DEFAULT_API_KEY is optional: when set, users may leave
    # the key blank and runs against AGENT_DEFAULT_BASE_URL use this key. It is
    # never sent to any other base URL and never returned by the API.
    AGENT_DEFAULT_BASE_URL: str = "https://openrouter.ai/api/v1"
    AGENT_DEFAULT_MODEL: str = "openai/gpt-6-luna"
    AGENT_DEFAULT_API_KEY: str = ""

    class Config:
        env_file = ".env"


settings = Settings()
