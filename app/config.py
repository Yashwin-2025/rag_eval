from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # Required: set in the environment or in .env (no defaults in code where noted).
    database_url: str = Field(..., description="PostgreSQL connection URL")
    openrouter_api_key: str = Field(..., description="OpenRouter API key (embeddings + optional chat)")

    openrouter_base_url: str = "https://openrouter.ai/api/v1"
    openrouter_embedding_model: str = "openai/text-embedding-3-small"
    openrouter_chat_model: str = "openai/gpt-4o-mini"
    openrouter_temperature: float = 0.2
    # Must match the chosen embedding model output size and sql/init.sql vector(N).
    embedding_dim: int = 1536
    rag_top_k: int = 5

    openrouter_http_referer: str | None = None
    openrouter_app_title: str | None = None


def get_settings() -> Settings:
    return Settings()
