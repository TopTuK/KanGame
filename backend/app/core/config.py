from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    DATABASE_URL: str = "postgresql+asyncpg://kanban:kanban@db:5432/kanban"
    CORS_ORIGINS: list[str] = ["http://localhost", "http://localhost:80", "http://localhost:5173"]

    class Config:
        env_file = ".env"


settings = Settings()
