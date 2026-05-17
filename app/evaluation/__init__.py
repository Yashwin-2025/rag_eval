"""RAG evaluation: retrieval metrics, end-to-end answers, optional LLM judge."""

from app.evaluation.pipeline import run_evaluation
from app.evaluation.schema import EvalCase, EvalReport

__all__ = ["EvalCase", "EvalReport", "run_evaluation"]
