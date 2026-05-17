import json
from pathlib import Path

from app.chains.rag import _format_docs
from app.config import get_settings
from app.evaluation.judge import judge_answer
from app.evaluation.metrics import hit_at_k, recall_at_k, reciprocal_rank
from app.evaluation.schema import (
    CaseResult,
    EvalCase,
    EvalReport,
    GenerationScores,
    RetrievalScores,
)
from app.retrieval.rbac import Principal, retrieve
from app.retrieval.retriever import RBACRetriever
from app.services.rag import build_user_rag_chain


def load_dataset(path: str | Path) -> list[EvalCase]:
    cases: list[EvalCase] = []
    with Path(path).open(encoding="utf-8") as f:
        for line_no, line in enumerate(f, start=1):
            line = line.strip()
            if not line:
                continue
            data = json.loads(line)
            if not data.get("case_id"):
                data["case_id"] = f"line_{line_no}"
            cases.append(EvalCase.model_validate(data))
    if not cases:
        raise ValueError(f"No eval cases found in {path}")
    return cases


def _evaluate_retrieval(case: EvalCase, top_k: int) -> RetrievalScores:
    principal = Principal(user_id=case.user_id)
    rows = retrieve(case.question, principal, top_k)
    chunk_ids = [r["chunk_id"] for r in rows]
    doc_ids = [r["doc_id"] for r in rows]
    exp_chunks = set(case.expected_chunk_ids)
    exp_docs = set(case.expected_doc_ids)
    return RetrievalScores(
        hit_at_k=hit_at_k(chunk_ids, doc_ids, exp_chunks, exp_docs, top_k),
        recall_at_k=recall_at_k(chunk_ids, doc_ids, exp_chunks, exp_docs, top_k),
        mrr=reciprocal_rank(chunk_ids, doc_ids, exp_chunks, exp_docs),
        retrieved_chunk_ids=chunk_ids,
        retrieved_doc_ids=doc_ids,
    )


def _evaluate_generation(case: EvalCase, top_k: int, use_judge: bool) -> GenerationScores:
    principal = Principal(user_id=case.user_id)
    retriever = RBACRetriever(principal=principal, top_k=top_k)
    docs = retriever.invoke(case.question)
    context = _format_docs(docs)
    chain = build_user_rag_chain(principal)
    answer = chain.invoke({"question": case.question})

    scores = GenerationScores(answer=answer)
    if not use_judge:
        return scores

    correctness, groundedness, reasoning = judge_answer(
        question=case.question,
        reference_answer=case.expected_answer,
        context=context,
        model_answer=answer,
    )
    scores.correctness = correctness
    scores.groundedness = groundedness
    scores.judge_reasoning = reasoning
    return scores


def run_evaluation(
    dataset_path: str | Path,
    *,
    run_generation: bool = True,
    use_judge: bool = True,
    top_k: int | None = None,
) -> EvalReport:
    settings = get_settings()
    k = top_k if top_k is not None else settings.rag_top_k
    cases = load_dataset(dataset_path)

    results: list[CaseResult] = []
    for case in cases:
        retrieval = _evaluate_retrieval(case, k)
        generation = None
        if run_generation:
            generation = _evaluate_generation(case, k, use_judge=use_judge)
        results.append(
            CaseResult(
                case_id=case.case_id or case.question[:40],
                question=case.question,
                retrieval=retrieval,
                generation=generation,
            )
        )

    n = len(results)
    mean_hit = sum(r.retrieval.hit_at_k for r in results) / n
    mean_recall = sum(r.retrieval.recall_at_k for r in results) / n
    mean_mrr = sum(r.retrieval.mrr for r in results) / n

    gen_results = [r for r in results if r.generation and r.generation.correctness is not None]
    mean_corr = None
    mean_ground = None
    if gen_results:
        mean_corr = sum(r.generation.correctness for r in gen_results) / len(gen_results)
        mean_ground = sum(r.generation.groundedness for r in gen_results) / len(gen_results)

    return EvalReport(
        cases=results,
        mean_hit_at_k=mean_hit,
        mean_recall_at_k=mean_recall,
        mean_mrr=mean_mrr,
        mean_correctness=mean_corr,
        mean_groundedness=mean_ground,
    )
