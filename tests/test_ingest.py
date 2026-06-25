"""Unit tests for the chunker and record builder. These are pure-Python and do
not need Chroma or the embedding model, so they run fast in CI."""
from src.ingest import build_records, chunk_text


def test_chunk_text_short_text_is_single_chunk():
    text = "Snowflake clustering depth is a metric."
    chunks = chunk_text(text, chunk_size=200, overlap=20)
    assert chunks == [text]


def test_chunk_text_respects_max_size():
    text = "para one.\n\n" + ("word " * 800) + "\n\npara three."
    chunks = chunk_text(text, chunk_size=400, overlap=50)
    assert len(chunks) > 1
    assert all(len(c) <= 500 for c in chunks), [len(c) for c in chunks]


def test_chunk_text_overlap_preserves_context():
    text = ("alpha bravo charlie delta " * 80).strip()
    chunks = chunk_text(text, chunk_size=200, overlap=50)
    assert len(chunks) >= 2
    # Some content from the end of one chunk should appear in the next.
    tail = chunks[0][-30:]
    assert any(tail[-10:] in c for c in chunks[1:])


def test_build_records_assigns_unique_ids_and_metadata():
    docs = [
        ("snowflake_warehouses.md", "Warehouses are compute clusters. " * 200),
        ("airflow_xcom.md", "XComs pass data between tasks. " * 200),
    ]
    records = build_records(docs)
    ids = [r["id"] for r in records]
    assert len(ids) == len(set(ids)), "chunk ids must be unique"
    sources = {r["metadata"]["source_doc"] for r in records}
    assert sources == {"snowflake_warehouses.md", "airflow_xcom.md"}
    for r in records:
        assert r["metadata"]["chunk_id"].startswith(r["metadata"]["source_doc"])
        assert "chunk_index" in r["metadata"]
