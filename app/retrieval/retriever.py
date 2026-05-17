from langchain_core.callbacks import CallbackManagerForRetrieverRun
from langchain_core.documents import Document
from langchain_core.retrievers import BaseRetriever
from pydantic import Field

from app.retrieval.rbac import Principal, retrieve


class RBACRetriever(BaseRetriever):
    """LangChain retriever scoped to a single authenticated user."""

    principal: Principal
    top_k: int = Field(default=5, ge=1)

    def _get_relevant_documents(
        self,
        query: str,
        *,
        run_manager: CallbackManagerForRetrieverRun,
    ) -> list[Document]:
        rows = retrieve(query, self.principal, self.top_k)
        docs: list[Document] = []
        for row in rows:
            meta = dict(row.get("metadata") or {})
            meta["chunk_id"] = row["chunk_id"]
            meta["doc_id"] = row["doc_id"]
            if row.get("distance") is not None:
                meta["distance"] = row["distance"]
            docs.append(Document(page_content=row["content"], metadata=meta))
        return docs
