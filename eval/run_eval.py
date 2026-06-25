"""Retrieval-only evaluation harness.

For each QA pair, run three retrieval strategies and check whether ANY of the
expected source docs appears in the top-k chunks returned. Print a markdown
table comparing dense-only, sparse-only, and hybrid+rerank.

Exits with code 1 if hybrid hit-rate falls below the CI threshold."""
from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from pathlib import Path

# Allow `python eval/run_eval.py` from the repo root.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src import config
from src.retrieve import Retriever

EVAL_DIR = Path(__file__).resolve().parent
DEFAULT_QA_PATH = EVAL_DIR / "qa_pairs.json"


@dataclass
class StrategyResult:
    name: str
    hits: int
    total: int

    @property
    def hit_rate(self) -> float:
        return self.hits / self.total if self.total else 0.0


def _hit(candidates_docs: list[str], expected_docs: list[str]) -> bool:
    return any(e in candidates_docs for e in expected_docs)


def run(qa_path: Path = DEFAULT_QA_PATH, k: int = config.FINAL_TOP_K) -> dict:
    qa_pairs = json.loads(qa_path.read_text(encoding="utf-8"))
    retriever = Retriever()

    dense_res = StrategyResult("dense_only", 0, len(qa_pairs))
    sparse_res = StrategyResult("sparse_only", 0, len(qa_pairs))
    hybrid_res = StrategyResult("hybrid+rerank", 0, len(qa_pairs))

    per_question: list[dict] = []

    for qa in qa_pairs:
        q = qa["question"]
        expected = qa["expected_docs"]

        dense_docs = [c.source_doc for c in retriever.dense(q, k=k)]
        sparse_docs = [c.source_doc for c in retriever.sparse(q, k=k)]
        hybrid_docs = [c.source_doc for c in retriever.hybrid(q, final_k=k)]

        d_hit = _hit(dense_docs, expected)
        s_hit = _hit(sparse_docs, expected)
        h_hit = _hit(hybrid_docs, expected)

        dense_res.hits += int(d_hit)
        sparse_res.hits += int(s_hit)
        hybrid_res.hits += int(h_hit)

        per_question.append(
            {
                "question": q,
                "expected": expected,
                "dense_hit": d_hit,
                "sparse_hit": s_hit,
                "hybrid_hit": h_hit,
                "hybrid_top_docs": hybrid_docs,
            }
        )

    return {
        "k": k,
        "results": [dense_res, sparse_res, hybrid_res],
        "per_question": per_question,
    }


def format_markdown(report: dict) -> str:
    lines = [
        f"### Retrieval hit-rate @ k={report['k']}",
        "",
        "| Strategy | Hits | Total | Hit-rate |",
        "|---|---|---|---|",
    ]
    for r in report["results"]:
        lines.append(
            f"| {r.name} | {r.hits} | {r.total} | {r.hit_rate:.2%} |"
        )
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--qa", default=str(DEFAULT_QA_PATH))
    parser.add_argument("--k", type=int, default=config.FINAL_TOP_K)
    parser.add_argument(
        "--threshold",
        type=float,
        default=0.70,
        help="Fail (exit 1) if hybrid+rerank hit-rate is below this.",
    )
    args = parser.parse_args()

    report = run(Path(args.qa), k=args.k)
    print(format_markdown(report))

    hybrid = next(r for r in report["results"] if r.name == "hybrid+rerank")
    if hybrid.hit_rate < args.threshold:
        print(
            f"\nFAIL: hybrid hit-rate {hybrid.hit_rate:.2%} below "
            f"threshold {args.threshold:.0%}",
            file=sys.stderr,
        )
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
