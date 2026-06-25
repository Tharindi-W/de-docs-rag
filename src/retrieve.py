"""Hybrid retrieval: dense (Chroma cosine) + sparse (BM25) candidate union,
cross-encoder re-rank, returning a final top_k.

Each Candidate is tagged with which source it came from (dense / sparse / both)
so a demo can show the hybrid pipeline actually doing work."""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

import chromadb
from chromadb.config import Settings
from rank_bm25 import BM25Okapi
from sentence_transformers import CrossEncoder, SentenceTransformer

from . import config


@dataclass
class Candidate:
    chunk_id: str
    source_doc: str
    text: str
    dense_score: float | None = None
    sparse_score: float | None = None
    rerank_score: float | None = None
    sources: set[str] = field(default_factory=set)  # {"dense", "sparse"}

    @property
    def final_score(self) -> float:
        # Prefer the rerank score; fall back to dense for cases (tests) without a reranker.
        if self.rerank_score is not None:
            return self.rerank_score
        if self.dense_score is not None:
            return self.dense_score
        return self.sparse_score or 0.0


_TOKEN_RE = re.compile(r"[A-Za-z0-9_]+")


def tokenize(text: str) -> list[str]:
    return [t.lower() for t in _TOKEN_RE.findall(text)]


class Retriever:
    """Holds the Chroma collection, BM25 index, embedder and re-ranker.

    Built once at app/eval start; reused across queries."""

    def __init__(
        self,
        persist_dir: Path = config.CHROMA_DIR,
        load_reranker: bool = True,
    ) -> None:
        client = chromadb.PersistentClient(
            path=str(persist_dir),
            settings=Settings(anonymized_telemetry=False),
        )
        self.collection = client.get_collection(config.COLLECTION_NAME)

        all_data = self.collection.get(include=["documents", "metadatas"])
        self._ids: list[str] = all_data["ids"]
        self._docs: list[str] = all_data["documents"]
        self._metas: list[dict] = all_data["metadatas"]

        # BM25 lives in memory. Cheap for thousands of chunks; for millions
        # we'd swap in an inverted-index store (Elastic/OpenSearch).
        self._bm25 = BM25Okapi([tokenize(d) for d in self._docs])

        self.embedder = SentenceTransformer(config.EMBED_MODEL_NAME)
        self.reranker = (
            CrossEncoder(config.RERANKER_MODEL_NAME) if load_reranker else None
        )

    # ---------- individual strategies ----------

    def dense(self, query: str, k: int = config.DENSE_TOP_K) -> list[Candidate]:
        q_emb = self.embedder.encode(
            [query], normalize_embeddings=True
        ).tolist()
        res = self.collection.query(
            query_embeddings=q_emb,
            n_results=k,
            include=["documents", "metadatas", "distances"],
        )
        out: list[Candidate] = []
        for doc, meta, dist in zip(
            res["documents"][0], res["metadatas"][0], res["distances"][0]
        ):
            # Chroma returns cosine *distance*; flip to similarity in [0, 1] (approx).
            sim = 1.0 - float(dist)
            out.append(
                Candidate(
                    chunk_id=meta["chunk_id"],
                    source_doc=meta["source_doc"],
                    text=doc,
                    dense_score=sim,
                    sources={"dense"},
                )
            )
        return out

    def sparse(self, query: str, k: int = config.SPARSE_TOP_K) -> list[Candidate]:
        scores = self._bm25.get_scores(tokenize(query))
        top_idx = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)[:k]
        out: list[Candidate] = []
        for i in top_idx:
            if scores[i] <= 0:
                continue
            meta = self._metas[i]
            out.append(
                Candidate(
                    chunk_id=meta["chunk_id"],
                    source_doc=meta["source_doc"],
                    text=self._docs[i],
                    sparse_score=float(scores[i]),
                    sources={"sparse"},
                )
            )
        return out

    # ---------- hybrid + rerank ----------

    @staticmethod
    def _merge(*candidate_lists: list[Candidate]) -> list[Candidate]:
        merged: dict[str, Candidate] = {}
        for cands in candidate_lists:
            for c in cands:
                if c.chunk_id in merged:
                    existing = merged[c.chunk_id]
                    existing.sources.update(c.sources)
                    if c.dense_score is not None:
                        existing.dense_score = c.dense_score
                    if c.sparse_score is not None:
                        existing.sparse_score = c.sparse_score
                else:
                    merged[c.chunk_id] = c
        return list(merged.values())

    def hybrid(
        self,
        query: str,
        final_k: int = config.FINAL_TOP_K,
        verbose: bool = False,
    ) -> list[Candidate]:
        dense_cands = self.dense(query)
        sparse_cands = self.sparse(query)
        merged = self._merge(dense_cands, sparse_cands)

        if self.reranker is not None and merged:
            pairs = [(query, c.text) for c in merged]
            scores = self.reranker.predict(pairs).tolist()
            for c, s in zip(merged, scores):
                c.rerank_score = float(s)

        merged.sort(key=lambda c: c.final_score, reverse=True)
        top = merged[:final_k]

        if verbose:
            print(f"[retrieve] query={query!r}")
            for c in top:
                tag = "+".join(sorted(c.sources))
                print(
                    f"  {c.chunk_id} | from={tag} | "
                    f"dense={c.dense_score} sparse={c.sparse_score} "
                    f"rerank={c.rerank_score}"
                )
        return top
