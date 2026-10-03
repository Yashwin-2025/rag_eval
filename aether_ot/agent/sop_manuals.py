"""
AETHER-OT: SOP knowledge base, served by the shared RAG pipeline (Postgres + pgvector).

The manuals below are embedded into the same `rag_chunks` table the chatbot uses, under their own
user_id, so retrieval goes through `app.retrieval.rbac.retrieve` (user-isolated) like any other doc.
"""

import logging
from typing import Any, Dict, List

from langchain_core.documents import Document

from app.config import get_settings
from app.db.pool import get_connection
from app.embeddings.openrouter import embed_documents
from app.ingest.pipeline import _chunk_id, upsert_chunks
from app.retrieval.rbac import Principal, retrieve

logger = logging.getLogger("aether_ot.sop")

SOP_USER_ID = "aether-ot"

# Realistic Industrial Standard Operating Procedures (SOPs)
DEFAULT_MANUALS = [
    {
        "doc_id": "SOP-AGV-001",
        "title": "AGV Fleet Operating Limits & Restricted Zone Rules",
        "category": "safety_spec",
        "content": (
            "Standard AGV operating speed on warehouse floor is 1.0 m/s. Maximum permissible speed is 1.2 m/s. "
            "RESTRICTED ZONE B: Located in sector X:[12-18], Y:[4-10]. Zone B houses high-speed mechanical lifters. "
            "AGVs traversing Zone B must NEVER exceed 0.80 m/s. If any AGV enters Zone B with speed > 0.80 m/s, "
            "laser barrier SENSOR-17 will instantly trip the master safety interlock, cutting power to CONV-01 "
            "to prevent mechanical collision. Recovery requires physical safety inspection and manual PLC coil reset."
        )
    },
    {
        "doc_id": "SOP-CONV-002",
        "title": "Conveyor Belt Speed Dynamics & Buffer Jam Protocol",
        "category": "operating_procedure",
        "content": (
            "Conveyor CONV-01 nominal operating speed is 40%. At normal speed, packing station capacity is 15 items/min. "
            "If conveyor speed setpoint (Modbus Register 40004) exceeds 80%, packages accumulate faster than packing stations "
            "can process, causing physical box pileups. Optical sensor SENSOR-21 will trigger on conveyor jam. "
            "Never increase speed setpoint without prior mechanical clearance."
        )
    },
    {
        "doc_id": "SOP-SEC-003",
        "title": "OT Industrial Cybersecurity Incident Response: Modbus Injection",
        "category": "incident_response",
        "content": (
            "Standard plant engineering workstations reside on 10.0.0.10. Any Modbus TCP write request from an uncataloged "
            "IP address (such as 10.0.0.99 or external subnet) indicates unauthorized access (MITRE ATT&CK for ICS T0855). "
            "If an unauthorized write modifies Register 40001-40004 (T0836 Modify Parameter), immediately: "
            "1. Physically isolate the rogue switch port on OT-SW-01. "
            "2. Verify physical process state (check AGV positions and conveyor buffer). "
            "3. Manually restore safe register setpoints from engineering console EWS-01. "
            "4. NEVER allow automated software to blindly restart field PLCs without human safety verification."
        )
    },
    {
        "doc_id": "SOP-BATT-004",
        "title": "Charging Station Automation & Battery Starvation Safeguards",
        "category": "maintenance",
        "content": (
            "AGVs require automated dock engagement when battery drops below 30%. Modbus Coils 00004-00006 govern charge "
            "relay enablement. If an unauthorized client clears these coils to 0 (Disabled), AGVs will deplete battery to 0% "
            "and stall on active transport aisles, blocking other vehicles and triggering ALM-BATT-01."
        )
    }
]


def seed_manuals() -> int:
    """Embed the default SOPs into rag_chunks if not already there. Returns chunks written (0 if already seeded)."""
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT count(*) FROM rag_chunks WHERE user_id = %s", (SOP_USER_ID,))
            if cur.fetchone()[0] >= len(DEFAULT_MANUALS):
                return 0

    docs = []
    for m in DEFAULT_MANUALS:
        text = f"{m['title']}\n{m['content']}"
        docs.append(Document(page_content=text, metadata={
            "user_id": SOP_USER_ID,
            "doc_id": m["doc_id"],
            "chunk_index": 0,
            "chunk_id": _chunk_id(SOP_USER_ID, m["doc_id"], 0, text),
            "title": m["title"],
            "category": m["category"],
        }))
    upsert_chunks(docs, embed_documents([d.page_content for d in docs]))
    return len(docs)


class RagManualRetriever:
    """Drop-in for the old Qdrant indexer: same `search_manuals` shape, backed by the RAG pipeline."""

    def search_manuals(self, query: str, limit: int = 2) -> List[Dict[str, Any]]:
        try:
            rows = retrieve(query, Principal(user_id=SOP_USER_ID), limit)
        except Exception:
            # DB or embedding service down: the investigation should still finish, just without citations.
            logger.exception("SOP retrieval failed; continuing without manual citations")
            return []
        return [
            {
                "doc_id": r["doc_id"],
                "title": (r.get("metadata") or {}).get("title", r["doc_id"]),
                "content": r["content"],
                "score": round(1 - float(r["distance"]), 3),
            }
            for r in rows
        ]


_shared: RagManualRetriever | None = None


def get_manual_retriever() -> RagManualRetriever:
    global _shared
    if _shared is None:
        _shared = RagManualRetriever()
    return _shared
