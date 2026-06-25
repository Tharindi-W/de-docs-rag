"""Ingestion pipeline: read raw .md docs, chunk recursively, embed with MiniLM,
persist to a local Chroma collection. Run as `python -m src.ingest`.

The chunker is implemented by hand (no LangChain) so every decision is visible:
1. Try to split on the largest separator that yields sub-chunks small enough.
2. If a piece is still too large, recurse with the next separator.
3. Glue small pieces back together up to CHUNK_SIZE_CHARS with CHUNK_OVERLAP_CHARS.
"""
from __future__ import annotations

import hashlib
import shutil
from pathlib import Path
from typing import Iterable

import chromadb
from chromadb.config import Settings
from sentence_transformers import SentenceTransformer

from . import config


def read_docs(raw_dir: Path) -> list[tuple[str, str]]:
    """Return list of (source_doc_filename, full_text)."""
    docs: list[tuple[str, str]] = []
    for path in sorted(raw_dir.glob("*.md")):
        text = path.read_text(encoding="utf-8").strip()
        if text:
            docs.append((path.name, text))
    return docs


def _split_recursive(text: str, separators: list[str], max_size: int) -> list[str]:
    """Split text using the first separator that yields any piece under max_size,
    recursing on still-too-large pieces with the next separator."""
    if len(text) <= max_size:
        return [text]
    if not separators:
        # Hard cut as last resort.
        return [text[i : i + max_size] for i in range(0, len(text), max_size)]

    sep, *rest = separators
    parts = text.split(sep) if sep else list(text)
    pieces: list[str] = []
    for p in parts:
        if not p:
            continue
        if len(p) <= max_size:
            pieces.append(p)
        else:
            pieces.extend(_split_recursive(p, rest, max_size))
    # Re-attach the separator so downstream text remains readable.
    return [p + (sep if sep else "") for p in pieces]


def chunk_text(
    text: str,
    chunk_size: int = config.CHUNK_SIZE_CHARS,
    overlap: int = config.CHUNK_OVERLAP_CHARS,
    separators: list[str] | None = None,
) -> list[str]:
    """Recursive splitter that then re-glues pieces up to chunk_size with overlap."""
    seps = separators if separators is not None else config.CHUNK_SEPARATORS
    raw_pieces = _split_recursive(text, seps, chunk_size)

    chunks: list[str] = []
    buf = ""
    for piece in raw_pieces:
        if len(buf) + len(piece) <= chunk_size:
            buf += piece
        else:
            if buf:
                chunks.append(buf.strip())
            # Carry the tail of the previous buffer as overlap.
            tail = buf[-overlap:] if overlap and buf else ""
            buf = tail + piece
    if buf.strip():
        chunks.append(buf.strip())
    return [c for c in chunks if c]


def build_records(docs: Iterable[tuple[str, str]]) -> list[dict]:
    """Turn (filename, text) pairs into chunk records with stable ids + metadata."""
    records: list[dict] = []
    for source_doc, text in docs:
        for i, chunk in enumerate(chunk_text(text)):
            chunk_id = f"{source_doc}::chunk_{i:03d}"
            uid = hashlib.sha1(chunk_id.encode("utf-8")).hexdigest()
            records.append(
                {
                    "id": uid,
                    "text": chunk,
                    "metadata": {
                        "source_doc": source_doc,
                        "chunk_id": chunk_id,
                        "chunk_index": i,
                    },
                }
            )
    return records


def get_chroma_client(persist_dir: Path = config.CHROMA_DIR) -> chromadb.PersistentClient:
    persist_dir.mkdir(parents=True, exist_ok=True)
    return chromadb.PersistentClient(
        path=str(persist_dir),
        settings=Settings(anonymized_telemetry=False, allow_reset=True),
    )


def ingest(
    raw_dir: Path = config.RAW_DOCS_DIR,
    persist_dir: Path = config.CHROMA_DIR,
    reset: bool = True,
) -> int:
    """Run the full ingestion pipeline. Returns the number of chunks indexed."""
    if reset and persist_dir.exists():
        shutil.rmtree(persist_dir)

    docs = read_docs(raw_dir)
    if not docs:
        raise RuntimeError(f"No .md docs found in {raw_dir}. Add docs and retry.")

    records = build_records(docs)
    print(f"[ingest] {len(docs)} docs -> {len(records)} chunks")

    embedder = SentenceTransformer(config.EMBED_MODEL_NAME)
    embeddings = embedder.encode(
        [r["text"] for r in records],
        show_progress_bar=True,
        normalize_embeddings=True,
    ).tolist()

    client = get_chroma_client(persist_dir)
    # Drop and recreate the collection so re-ingesting is deterministic.
    try:
        client.delete_collection(config.COLLECTION_NAME)
    except Exception:
        pass
    collection = client.create_collection(
        name=config.COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"},
    )
    collection.add(
        ids=[r["id"] for r in records],
        documents=[r["text"] for r in records],
        metadatas=[r["metadata"] for r in records],
        embeddings=embeddings,
    )
    print(f"[ingest] persisted {len(records)} chunks to {persist_dir}")
    return len(records)


if __name__ == "__main__":
    ingest()
