import hashlib
import json
from typing import Any
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
from pgvector.psycopg import register_vector

from app.db.pool import get_connection
from app.embeddings.openrouter import embed_documents

def _chunk_id(user_id: str, doc_id: str, index: int, text: str) -> str:
    """Generate a stable unique id for the chunk."""
    raw = f"{user_id}|{doc_id}|{index}|{text}".encode()
    return "chk_" + hashlib.sha256(raw).hexdigest()[:32]


def chunk_documents(raw_text: str, doc_id: str, user_id: str) -> list[Document]:
    splitter = RecursiveCharacterTextSplitter(chunk_size=1200, chunk_overlap=150)
    docs=splitter.create_documents([raw_text])
    for i,d in enumerate(docs):
        d.metadata['user_id']=user_id
        d.metadata['doc_id']=doc_id
        d.metadata['chunk_index']=i
        d.metadata['chunk_id']=_chunk_id(user_id,doc_id,i,d.page_content)
    return docs


def upsert_chunks(documents: list[Document], embeddings: list[list[float]]) -> None:
    """Insert or update rows in rag_chunks (pgvector)."""
    if len(documents) != len(embeddings):
        raise ValueError("documents and embeddings length mismatch")
    
    sql = """
        INSERT INTO rag_chunks (chunk_id, user_id, doc_id, content, embedding, metadata)
        VALUES (%s, %s, %s, %s, %s, %s::jsonb)
        ON CONFLICT (chunk_id) DO UPDATE SET
            user_id = EXCLUDED.user_id,
            doc_id = EXCLUDED.doc_id,
            content = EXCLUDED.content,
            embedding = EXCLUDED.embedding,
            metadata = EXCLUDED.metadata;
    """

    with get_connection() as conn:
        register_vector(conn)
        rows: list[tuple[Any, ...]] = []
        for doc, emb in zip(documents, embeddings, strict=True):
            meta = {k: v for k, v in doc.metadata.items() if k not in {"chunk_id", "user_id", "doc_id"}}
            rows.append(
                (
                    doc.metadata["chunk_id"],
                    doc.metadata["user_id"],
                    doc.metadata["doc_id"],
                    doc.page_content,
                    emb,
                    json.dumps(meta),
                )
            )
        with conn.cursor() as cur:
            cur.executemany(sql, rows)
        conn.commit()
