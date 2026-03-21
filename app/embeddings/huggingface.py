from langchain_core.embeddings import Embeddings


def get_embeddings() -> Embeddings:
    """Return a LangChain Embeddings instance (Hugging Face / sentence-transformers). Output dim must be 768."""
    ...


def embed_documents(texts: list[str]) -> list[list[float]]:
    ...


def embed_query(text: str) -> list[float]:
    ...
