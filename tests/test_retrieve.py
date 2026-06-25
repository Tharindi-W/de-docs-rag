"""Unit tests for retrieval helpers that do not require a built index.

End-to-end retrieval (Chroma + embeddings) is covered by the eval harness,
which CI runs separately."""
from src.retrieve import Candidate, Retriever, tokenize


def test_tokenize_lowercases_and_splits_punctuation():
    assert tokenize("Snowflake_clustering, depth.") == [
        "snowflake_clustering",
        "depth",
    ]


def test_tokenize_keeps_alphanumeric():
    assert tokenize("G.2X worker has 2 DPUs") == [
        "g",
        "2x",
        "worker",
        "has",
        "2",
        "dpus",
    ]


def test_candidate_final_score_prefers_rerank():
    c = Candidate(
        chunk_id="a::chunk_000",
        source_doc="a.md",
        text="x",
        dense_score=0.9,
        sparse_score=12.0,
        rerank_score=2.5,
    )
    assert c.final_score == 2.5


def test_candidate_final_score_falls_back_to_dense():
    c = Candidate(
        chunk_id="a::chunk_000",
        source_doc="a.md",
        text="x",
        dense_score=0.7,
    )
    assert c.final_score == 0.7


def test_merge_unions_sources():
    a = Candidate("id1", "doc.md", "x", dense_score=0.8, sources={"dense"})
    b = Candidate("id1", "doc.md", "x", sparse_score=5.0, sources={"sparse"})
    merged = Retriever._merge([a], [b])
    assert len(merged) == 1
    assert merged[0].sources == {"dense", "sparse"}
    assert merged[0].dense_score == 0.8
    assert merged[0].sparse_score == 5.0
