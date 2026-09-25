from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    PROJECT_NAME: str = "Codoric FastAPI E-Commerce Core"
    DEBUG: bool = True
    DATABASE_URL: str = "sqlite+aiosqlite:///./ecommerce.db"
    DATABASE_ECHO: bool = True  # Log raw SQL queries to console to inspect ORM behavior

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

settings = Settings()
