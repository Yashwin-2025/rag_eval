from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # Required: set DATABASE_URL in the environment or in .env (no default in code).
    database_url: str = Field(..., description="PostgreSQL connection URL")
    huggingface_hub_token: str | None = None

    embedding_model_name: str = "BAAI/bge-base-en-v1.5"
    embedding_dim: int = 768


def get_settings() -> Settings:
    return Settings()
