import os

from langchain_core.embeddings import Embeddings
from langchain_huggingface import HuggingFaceEmbeddings

from app.config import get_settings


def get_embeddings() -> Embeddings:
    """768-dim model must match sql/init.sql and config.embedding_dim."""
    settings = get_settings()
    if settings.huggingface_hub_token:
        os.environ.setdefault("HF_TOKEN", settings.huggingface_hub_token)

    return HuggingFaceEmbeddings(
        model_name=settings.embedding_model_name,
        model_kwargs={"device": "cpu"},
        encode_kwargs={"normalize_embeddings": True},
    )


def embed_documents(texts: list[str]) -> list[list[float]]:
    emb = get_embeddings()
    return emb.embed_documents(texts)


def embed_query(text: str) -> list[float]:
    emb = get_embeddings()
    return emb.embed_query(text)