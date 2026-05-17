from app.ingest.docling_loader import load_document_text
from app.ingest.pipeline import chunk_documents, upsert_chunks
from app.embeddings.openrouter import embed_documents


def ingest_file(file_path: str, doc_id: str, user_id: str) -> int:
    """Parse, chunk, embed, and upsert one file. Returns number of chunks stored."""
    raw = load_document_text(file_path)
    docs = chunk_documents(raw, doc_id=doc_id, user_id=user_id)
    if not docs:
        return 0
    vectors = embed_documents([d.page_content for d in docs])
    upsert_chunks(docs, vectors)
    return len(docs)
