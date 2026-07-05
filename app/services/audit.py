import json
import logging
from typing import Any
from app.db.pool import get_connection

logger = logging.getLogger(__name__)

def log_transaction(
    user_id: str,
    question: str,
    retrieved_chunks: list[dict] | None,
    answer: str,
    guardrail_results: dict[str, Any] | None,
    metadata: dict[str, Any] | None = None,
) -> None:
    """Inserts a new transaction log row into the audit_logs database table."""
    sql = """
        INSERT INTO audit_logs (user_id, question, retrieved_chunks, answer, guardrail_results, metadata)
        VALUES (%s, %s, %s::jsonb, %s, %s::jsonb, %s::jsonb)
    """
    
    chunks_json = json.dumps(retrieved_chunks) if retrieved_chunks is not None else None
    guardrails_json = json.dumps(guardrail_results) if guardrail_results is not None else None
    metadata_json = json.dumps(metadata) if metadata is not None else None

    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    sql,
                    (user_id, question, chunks_json, answer, guardrails_json, metadata_json),
                )
            conn.commit()
    except Exception as e:
        logger.error(f"Failed to log transaction to audit_logs: {e}", exc_info=True)
