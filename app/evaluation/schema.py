from pydantic import BaseModel, Field


class EvalCase(BaseModel):
    """One golden example. Ingest the referenced docs for `user_id` before running eval."""

    question: str = Field(..., min_length=1)
    expected_answer: str = Field(..., min_length=1)
    user_id: str = Field(..., min_length=1)
    expected_chunk_ids: list[str] = Field(default_factory=list)
    expected_doc_ids: list[str] = Field(default_factory=list)
    case_id: str | None = None


class RetrievalScores(BaseModel):
    hit_at_k: float
    recall_at_k: float
    mrr: float
    retrieved_chunk_ids: list[str]
    retrieved_doc_ids: list[str]


class GenerationScores(BaseModel):
    answer: str
    correctness: float | None = None
    groundedness: float | None = None
    judge_reasoning: str | None = None


class CaseResult(BaseModel):
    case_id: str
    question: str
    retrieval: RetrievalScores
    generation: GenerationScores | None = None


class EvalReport(BaseModel):
    cases: list[CaseResult]
    mean_hit_at_k: float
    mean_recall_at_k: float
    mean_mrr: float
    mean_correctness: float | None = None
    mean_groundedness: float | None = None
