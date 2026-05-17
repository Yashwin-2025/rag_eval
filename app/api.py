import shutil
import uuid
from pathlib import Path

from fastapi import Depends, FastAPI, File, Form, Header, HTTPException, UploadFile
from pydantic import BaseModel, Field

from app.config import get_settings
from app.ingest.run import ingest_file
from app.retrieval.rbac import Principal
from app.services.rag import build_user_rag_chain

app = FastAPI(title="Chatbot RAG", version="0.1.0")

DATA_DIR = Path(__file__).resolve().parent.parent / "data"


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
    chain = build_user_rag_chain(principal)
    answer = chain.invoke({"question": body.question})
    return ChatResponse(answer=answer)
