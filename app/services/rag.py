from langchain_core.runnables import Runnable

from app.chains.rag import build_rag_chain
from app.config import get_settings
from app.llm.openrouter import get_chat_llm
from app.retrieval.rbac import Principal
from app.retrieval.retriever import RBACRetriever


def build_user_rag_chain(principal: Principal) -> Runnable:
    settings = get_settings()
    retriever = RBACRetriever(principal=principal, top_k=settings.rag_top_k)
    return build_rag_chain(get_chat_llm(), retriever)
