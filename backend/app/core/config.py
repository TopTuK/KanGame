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
    # Runs are background server tasks (closing the page does not stop them);
    # this caps a whole run, retries included.
    AGENT_MAX_RUN_MINUTES: int = 120
    AGENT_DAY_TOOL_CALL_LIMIT: int = 40
    # Model calls: per-request timeout and the client's own quick retries, then
    # a guard around a whole day and how many times a failed day is retried.
    AGENT_LLM_TIMEOUT_SECONDS: int = 120
    AGENT_LLM_REQUEST_RETRIES: int = 2
    AGENT_DAY_TIMEOUT_SECONDS: int = 900
    AGENT_LLM_RETRIES: int = 4
    # Context management. The conversation is kept across days; older days are
    # summarized once the estimated context passes THRESHOLD x WINDOW tokens,
    # and the client compacts tool results within a day if a day alone grows
    # toward the window.
    AGENT_CONTEXT_WINDOW_TOKENS: int = 200_000
    AGENT_CONTEXT_SUMMARY_THRESHOLD: float = 0.3
    AGENT_CONTEXT_KEEP_RECENT_DAYS: int = 2
    AGENT_MAX_OUTPUT_TOKENS: int = 8_192
    # Defaults pre-filled in the agent form: RouterAI (OpenAI-compatible) +
    # OpenAI's fast, cheap GPT-4.1 nano. AGENT_DEFAULT_API_KEY is optional: when set, users may leave
    # the key blank and runs against AGENT_DEFAULT_BASE_URL use this key. It is
    # never sent to any other base URL and never returned by the API.
    AGENT_DEFAULT_BASE_URL: str = "https://routerai.ru/api/v1"
    AGENT_DEFAULT_MODEL: str = "openai/gpt-4.1-nano"
    AGENT_DEFAULT_API_KEY: str = ""

    class Config:
        env_file = ".env"


settings = Settings()
