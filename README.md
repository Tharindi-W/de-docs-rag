# de-docs-rag

A production-style Retrieval-Augmented Generation system over data engineering
documentation (Snowflake, Apache Airflow, AWS Glue). It is built directly on
top of `chromadb`, `sentence-transformers`, and `rank_bm25` rather than a
framework wrapper, so every step of the pipeline is inspectable and
explainable.

```
question -> hybrid retrieval (dense + BM25, union, cross-encoder rerank)
         -> top-k chunks
         -> Groq LLM with context-only system prompt
         -> answer + structured citations
```

## Architecture

### Ingestion flow

```
data/raw/*.md
   |
   v
recursive char chunker (~400 tok, ~50 tok overlap)
   |
   v
sentence-transformers/all-MiniLM-L6-v2  (384-dim, local)
   |
   v
Chroma persistent collection (cosine)  +  in-memory BM25 (built at query time)
```

### Query flow

```
user question
   |
   +--> dense retrieval (Chroma top-10)
   +--> sparse retrieval (BM25 top-10)
        |
        v
   union + dedupe by chunk_id
        |
        v
   cross-encoder/ms-marco-MiniLM-L-6-v2 rerank
        |
        v
   final top-4 chunks
        |
        v
   prompt with strict "answer from context only" system message
        |
        v
   Groq llama-3.1-8b-instant
        |
        v
   { answer, citations: [{source_doc, chunk_id, similarity_score}, ...] }
```

## Design decisions

| Decision | Alternative considered | Why this choice |
|---|---|---|
| Vector store: Chroma (persistent, local) | Pinecone, Weaviate, Qdrant Cloud | Zero infra cost and zero external dependency for a portfolio project; persists to disk so the index survives across runs. Pinecone/Weaviate are the right answer at scale; over-engineering this would obscure the pipeline. |
| Embeddings: `all-MiniLM-L6-v2` (384-dim, local) | OpenAI `text-embedding-3-small`, Cohere `embed-english-v3` | Free, runs offline, no rate limits, no key management. Tradeoff documented: MiniLM is measurably weaker than hosted models on hard semantic tasks. The BM25 layer plus cross-encoder rerank compensates for most of that gap on this corpus. |
| Retrieval: hybrid dense + BM25 with cross-encoder rerank | Dense-only | Dense embeddings miss exact-term matches (e.g. `G.2X`, `AUTO_SUSPEND`, function names) that BM25 catches trivially. Rerank reorders the union so the highest-quality chunks land in the prompt. The eval harness reports hit-rate separately to prove this. |
| Generation: Groq (`llama-3.1-8b-instant`) | OpenAI GPT-4o, Anthropic Claude | Groq's free tier is fast and free for portfolio work. The OpenAI-compatible endpoint means switching to OpenAI is a one-line `base_url` change if needed. |
| No LangChain or LlamaIndex | Use a framework | Every step is plain Python so the interview conversation can go down to "why this exact line"; framework abstractions hide the parts I want to discuss (chunking strategy, hybrid scoring, rerank). |
| Chunking: recursive character splitter, ~400 tokens, ~50 overlap | Sentence-level, fixed-size token windows | 400 tokens fits comfortably in the context budget alongside k=4 chunks and a system prompt, and the recursive splitter respects paragraph and sentence boundaries first. Overlap reduces the risk of an answer falling exactly on a chunk boundary. |
| Citations as structured objects | Inline-only or none | `{source_doc, chunk_id, similarity_score}` lets the UI and downstream consumers render or filter citations programmatically, not just parse them out of prose. |

## Setup

Requirements: Python 3.11 or newer, ~2 GB RAM for the embedding and re-ranker
models.

```bash
git clone <this repo>
cd de-docs-rag

python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS / Linux
source .venv/bin/activate

pip install -r requirements.txt

cp .env.example .env
# Edit .env and set GROQ_API_KEY
```

### Getting a free Groq API key

1. Sign in at https://console.groq.com/keys
2. Create a new API key.
3. Paste it into `.env` as `GROQ_API_KEY=...`.

Groq's free tier is sufficient for development and demos; rate limits are
visible in the console.

## Run

```bash
# 1. Build the index (one-time, also reruns when docs change)
python -m src.ingest

# 2. Run the retrieval eval (no LLM call, no key needed)
python eval/run_eval.py

# 3. Launch the Streamlit UI
streamlit run app.py
```

The UI shows the answer, structured citations, the retrieved chunks with their
source tags (dense / sparse / both), and the exact prompt sent to the LLM.

## Example query

> **Q:** What is Snowflake automatic clustering and when should I define a clustering key?

> **A:** According to [snowflake_clustering.md], automatic clustering is a
> background service that maintains the clustering of large tables defined with
> a CLUSTER BY expression. Snowflake monitors clustering depth and reclusters
> micro-partitions when they become heavily overlapping. A clustering key is
> worthwhile when the table is large (multi-terabyte), queries filter on a
> small number of columns, and the natural ingestion order does not align with
> how the table is queried.

Citations:

- snowflake_clustering.md :: chunk_000 (score=8.7421)
- snowflake_clustering.md :: chunk_001 (score=7.2103)

_(Replace this section with a screenshot of the Streamlit UI once you have
one.)_

## Eval results

Hit-rate @ k=4 on the 13 hand-written QA pairs in `eval/qa_pairs.json`:

| Strategy | Hit-rate |
|---|---|
| dense_only | _filled in by `python eval/run_eval.py`_ |
| sparse_only | _filled in by `python eval/run_eval.py`_ |
| hybrid+rerank | _filled in by `python eval/run_eval.py`_ |

CI fails if hybrid hit-rate falls below 70%, so the table above acts as a
guardrail, not decoration.

## What I would improve with more time or at production scale

- **Larger corpus and ingestion pipeline.** Crawl the actual Snowflake,
  Airflow, and Glue documentation sites on a schedule, diff against the
  previous snapshot, and only re-embed changed chunks (incremental ingest).
- **Query rewriting.** A small LLM call to expand the user's question into
  hypothetical answer text (HyDE) before dense retrieval, particularly for
  short or ambiguous queries.
- **Semantic caching.** Cache `(normalised_question -> answer + citations)`
  with a similarity check on the question embedding to avoid repeat LLM
  calls.
- **Observability.** Emit per-query traces (retrieval candidates, rerank
  scores, prompt, model latency, token counts) to a tracing backend. Track
  user thumbs up/down to build a feedback dataset.
- **Better embeddings.** Swap MiniLM for a hosted embedding model
  (text-embedding-3-large or Cohere v3) and re-run the eval; expect a few
  points of hit-rate on the harder semantic questions.
- **Vector store at scale.** Move from local Chroma to a managed store
  (Pinecone, Qdrant Cloud, or pgvector on the existing OLTP DB) once the
  corpus exceeds what fits in memory or needs multi-region access.
- **Answer evaluation, not just retrieval.** Add an LLM-as-judge step that
  scores factuality of the generated answer against the cited chunks, with a
  smaller golden set graded by hand.
- **Streaming ingestion for changing docs.** Subscribe to upstream RSS or
  webhook events so new docs are indexed within minutes of publication.
- **Access control.** For multi-tenant use, scope the Chroma collection by
  tenant and filter retrieval by metadata at query time.

## Repo layout

```
de-docs-rag/
  data/raw/              # source .md docs
  src/
    config.py            # all tunables
    ingest.py            # chunk + embed + persist
    retrieve.py          # dense + BM25 + rerank
    generate.py          # prompt + Groq call
    pipeline.py          # ties it together, returns Answer + Citations
  eval/
    qa_pairs.json
    run_eval.py
  tests/
    test_ingest.py
    test_retrieve.py
  app.py                 # Streamlit UI
  .github/workflows/ci.yml
  requirements.txt
  .env.example
  README.md
```
