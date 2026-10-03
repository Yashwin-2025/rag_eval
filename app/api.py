import shutil
import uuid
from pathlib import Path
from typing import Any

from fastapi import Depends, FastAPI, File, Form, Header, HTTPException, UploadFile
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from langchain_core.prompts import ChatPromptTemplate

from app.responsible_ai_router import router as responsible_ai_router


from app.config import get_settings
from app.ingest.run import ingest_file
from app.retrieval.rbac import Principal, retrieve
from app.llm.openrouter import get_chat_llm
from app.services.guardrails import scrub_pii, check_injection, check_verbatim_overlap, check_medical_safety
from app.services.audit import log_transaction
from app.db.pool import get_connection

app = FastAPI(title="Chatbot RAG", version="0.1.0")

DATA_DIR = Path(__file__).resolve().parent.parent / "data"

# user_ids whose documents are first-party (AETHER-OT SOPs, see aether_ot/agent/sop_manuals.py).
INTERNAL_DOC_USERS = {"aether-ot"}


def require_user_id(x_user_id: str | None = Header(default=None, alias="X-User-Id")) -> str:
    """Dev-only identity header. Replace with verified JWT/session in production."""
    if not x_user_id or not x_user_id.strip():
        raise HTTPException(status_code=401, detail="Missing X-User-Id header")
    return x_user_id.strip()


def get_principal(user_id: str = Depends(require_user_id)) -> Principal:
    return Principal(user_id=user_id)


class ChatRequest(BaseModel):
    question: str = Field(..., min_length=1)


class ChatResponse(BaseModel):
    answer: str


class IngestResponse(BaseModel):
    doc_id: str
    chunks: int


@app.get("/health")
def health() -> dict[str, str]:
    get_settings()
    return {"status": "ok"}


@app.post("/ingest", response_model=IngestResponse)
async def ingest(
    file: UploadFile = File(...),
    doc_id: str | None = Form(default=None),
    principal: Principal = Depends(get_principal),
) -> IngestResponse:
    if not file.filename:
        raise HTTPException(status_code=400, detail="Upload must include a filename")

    resolved_doc_id = doc_id or Path(file.filename).stem
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    suffix = Path(file.filename).suffix
    dest = DATA_DIR / f"{principal.user_id}_{uuid.uuid4().hex}{suffix}"

    try:
        with dest.open("wb") as out:
            shutil.copyfileobj(file.file, out)
        chunks = ingest_file(str(dest), doc_id=resolved_doc_id, user_id=principal.user_id)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    finally:
        dest.unlink(missing_ok=True)

    return IngestResponse(doc_id=resolved_doc_id, chunks=chunks)


@app.post("/chat", response_model=ChatResponse)
def chat(body: ChatRequest, principal: Principal = Depends(get_principal)) -> ChatResponse:
    # 1. Input Guardrails
    scrubbed_question, pii_mapping = scrub_pii(body.question)
    
    if check_injection(scrubbed_question):
        log_transaction(
            user_id=principal.user_id,
            question=body.question,
            retrieved_chunks=None,
            answer="Blocked by input safety filter: prompt injection detected.",
            guardrail_results={
                "pii_detected": len(pii_mapping) > 0,
                "injection_detected": True,
                "copyright_triggered": False,
                "medical_safety_triggered": False,
            },
        )
        return ChatResponse(answer="Blocked by input safety filter: prompt injection detected.")

    # 2. Vector Retrieval (Manual for audit logs and output guardrails check)
    settings = get_settings()
    retrieved_rows = retrieve(scrubbed_question, principal, settings.rag_top_k)
    context = "\n\n".join(row["content"] for row in retrieved_rows)

    # 3. LLM Generation
    llm = get_chat_llm()
    prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                "Use only the following context to answer. If the answer is not in the context, say you do not know.\n\n{context}",
            ),
            ("human", "{question}"),
        ]
    )
    formatted = prompt.format_messages(context=context, question=scrubbed_question)
    msg = llm.invoke(formatted)
    answer = msg.content if isinstance(msg.content, str) else str(msg.content)

    # 4. Output Guardrails
    medical_triggered = check_medical_safety(answer)
    # Our own SOP manuals are short and meant to be quoted, so the copyright check only applies
    # to everyone else's documents.
    copyright_triggered = (
        principal.user_id not in INTERNAL_DOC_USERS
        and check_verbatim_overlap(answer, [r["content"] for r in retrieved_rows])
    )

    guardrail_results = {
        "pii_detected": len(pii_mapping) > 0,
        "injection_detected": False,
        "copyright_triggered": copyright_triggered,
        "medical_safety_triggered": medical_triggered,
    }

    if medical_triggered:
        answer = "I am an AI assistant, not a doctor. I cannot provide medical diagnoses or treatment recommendations. Please consult a qualified healthcare professional."
    elif copyright_triggered:
        answer = "Response blocked by copyright filter: verbatim duplication of source document detected."
    else:
        # Restore PII in non-blocked answers
        for placeholder, original in pii_mapping.items():
            answer = answer.replace(placeholder, original)

    # 5. Audit Logging
    chunks_summary = [
        {"chunk_id": r["chunk_id"], "doc_id": r["doc_id"], "distance": float(r["distance"])}
        for r in retrieved_rows
    ]
    log_transaction(
        user_id=principal.user_id,
        question=body.question,
        retrieved_chunks=chunks_summary,
        answer=answer,
        guardrail_results=guardrail_results,
    )

    return ChatResponse(answer=answer)


@app.delete("/user/purge")
def purge_user_data(principal: Principal = Depends(get_principal)) -> dict[str, Any]:
    """Cascades deletion of all documents, chunks, and audit logs belonging to the user."""
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM rag_chunks WHERE user_id = %s", (principal.user_id,))
            deleted_chunks = cur.rowcount
            cur.execute("DELETE FROM audit_logs WHERE user_id = %s", (principal.user_id,))
            deleted_logs = cur.rowcount
        conn.commit()

    return {
        "status": "success",
        "message": f"Purged all user data: {deleted_chunks} chunks and {deleted_logs} logs deleted.",
        "deleted_chunks": deleted_chunks,
        "deleted_logs": deleted_logs,
    }


# Include Responsible AI Router
app.include_router(responsible_ai_router)

# Serve SPA Frontend Dashboard
app.mount("/static", StaticFiles(directory="app/static"), name="static")


@app.get("/")
def get_dashboard() -> FileResponse:
    return FileResponse("app/static/index.html")

