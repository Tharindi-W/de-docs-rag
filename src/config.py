"""Centralised tunables. Keep everything that someone might want to A/B here."""
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# Data + persistence
RAW_DOCS_DIR = ROOT / "data" / "raw"
CHROMA_DIR = ROOT / "chroma_store"
COLLECTION_NAME = "de_docs"

# Chunking. ~400 tokens with ~50 token overlap. We approximate tokens with
# characters at a 4:1 ratio (standard rule of thumb for English prose) so we
# do not need to load a tokenizer just to chunk.
CHUNK_SIZE_CHARS = 1600          # ~400 tokens
CHUNK_OVERLAP_CHARS = 200        # ~50 tokens
CHUNK_SEPARATORS = ["\n\n", "\n", ". ", " "]  # recursive split, biggest first

# Embeddings. MiniLM is 384-dim, fast, fully local. Tradeoff documented in README.
EMBED_MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"

# Retrieval
DENSE_TOP_K = 10
SPARSE_TOP_K = 10
FINAL_TOP_K = 4

# Re-ranker
RERANKER_MODEL_NAME = "cross-encoder/ms-marco-MiniLM-L-6-v2"

# Generation (Groq, OpenAI-compatible endpoint)
GROQ_BASE_URL = "https://api.groq.com/openai/v1"
GROQ_MODEL = "llama-3.1-8b-instant"
GROQ_TEMPERATURE = 0.1
GROQ_MAX_TOKENS = 512
