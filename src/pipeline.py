"""End-to-end query pipeline: retrieve -> generate -> structured answer + citations."""
from __future__ import annotations

from dataclasses import asdict, dataclass

from . import config
from .generate import GenerationResult, generate
from .retrieve import Candidate, Retriever


@dataclass
class Citation:
    source_doc: str
    chunk_id: str
    similarity_score: float

    @classmethod
    def from_candidate(cls, c: Candidate) -> "Citation":
        return cls(
            source_doc=c.source_doc,
            chunk_id=c.chunk_id,
            similarity_score=round(c.final_score, 4),
        )


@dataclass
class Answer:
    question: str
    answer: str
    citations: list[Citation]
    candidates: list[Candidate]  # full chunks, handy for the UI
    prompt: str

    def to_dict(self) -> dict:
        return {
            "question": self.question,
            "answer": self.answer,
            "citations": [asdict(c) for c in self.citations],
        }


class RAGPipeline:
    def __init__(self, retriever: Retriever | None = None) -> None:
        self.retriever = retriever or Retriever()

    def ask(self, question: str, verbose: bool = False) -> Answer:
        candidates = self.retriever.hybrid(
            question, final_k=config.FINAL_TOP_K, verbose=verbose
        )
        gen: GenerationResult = generate(question, candidates)
        return Answer(
            question=question,
            answer=gen.answer,
            citations=[Citation.from_candidate(c) for c in candidates],
            candidates=candidates,
            prompt=gen.prompt,
        )


if __name__ == "__main__":
    import sys

    q = " ".join(sys.argv[1:]) or "What is Snowflake automatic clustering?"
    pipeline = RAGPipeline()
    answer = pipeline.ask(q, verbose=True)
    print("\n=== Answer ===")
    print(answer.answer)
    print("\n=== Citations ===")
    for c in answer.citations:
        print(f"  - {c.chunk_id} (score={c.similarity_score})")
