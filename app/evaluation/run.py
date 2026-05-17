"""CLI: python -m app.evaluation.run --dataset eval/sample_dataset.jsonl"""

import argparse
import json
from pathlib import Path

from app.evaluation.pipeline import run_evaluation


def _print_report(report) -> None:
    print("\n=== RAG evaluation summary ===")
    print(f"  cases:             {len(report.cases)}")
    print(f"  mean hit@k:        {report.mean_hit_at_k:.3f}")
    print(f"  mean recall@k:     {report.mean_recall_at_k:.3f}")
    print(f"  mean MRR:          {report.mean_mrr:.3f}")
    if report.mean_correctness is not None:
        print(f"  mean correctness: {report.mean_correctness:.3f}")
        print(f"  mean groundedness: {report.mean_groundedness:.3f}")
    print()


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate RAG retrieval and generation.")
    parser.add_argument(
        "--dataset",
        type=Path,
        default=Path("eval/sample_dataset.jsonl"),
        help="JSONL file with EvalCase rows",
    )
    parser.add_argument("--top-k", type=int, default=None, help="Override RAG_TOP_K from settings")
    parser.add_argument(
        "--retrieval-only",
        action="store_true",
        help="Skip generation; only compute hit/recall/MRR",
    )
    parser.add_argument(
        "--no-judge",
        action="store_true",
        help="Run generation but skip OpenRouter LLM judge (saves cost)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Write full JSON report to this path",
    )
    args = parser.parse_args()

    report = run_evaluation(
        args.dataset,
        run_generation=not args.retrieval_only,
        use_judge=not args.no_judge,
        top_k=args.top_k,
    )
    _print_report(report)

    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(report.model_dump_json(indent=2), encoding="utf-8")
        print(f"Wrote report to {args.output}")


if __name__ == "__main__":
    main()
