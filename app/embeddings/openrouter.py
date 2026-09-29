"""Embeddings via OpenRouter (OpenAI-compatible /v1/embeddings)."""

from langchain_core.embeddings import Embeddings
from langchain_openai import OpenAIEmbeddings

from app.config import get_settings


def get_embeddings() -> Embeddings:
    """Dimension must match `embedding_dim` in config and `vector(N)` in sql/init.sql."""
    s = get_settings()
    default_headers: dict[str, str] = {}
    if s.openrouter_http_referer:
        default_headers["HTTP-Referer"] = s.openrouter_http_referer
    if s.openrouter_app_title:
        default_headers["X-Title"] = s.openrouter_app_title

    return OpenAIEmbeddings(
        model=s.openrouter_embedding_model,
        dimensions=s.embedding_dim,
        openai_api_key=s.openrouter_api_key,
        openai_api_base=s.openrouter_base_url,
        check_embedding_ctx_length=False,
        default_headers=default_headers or None,
    )


def embed_documents(texts: list[str]) -> list[list[float]]:
    emb = get_embeddings()
    return emb.embed_documents(texts)


def embed_query(text: str) -> list[float]:
    emb = get_embeddings()
    return emb.embed_query(text)
