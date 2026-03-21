from langchain_core.documents import Document


def chunk_documents(raw_text: str, doc_id: str, user_id: str) -> list[Document]:
    ...


def upsert_chunks(documents: list[Document], embeddings: list[list[float]]) -> None:
    """Insert or update rows in rag_chunks (pgvector)."""
    ...
