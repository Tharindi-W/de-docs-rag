"""Streamlit UI for de-docs-rag.

Run: `streamlit run app.py`
Assumes ingestion has already been performed: `python -m src.ingest`.
"""
from __future__ import annotations

import os
from pathlib import Path

import streamlit as st
from dotenv import load_dotenv

load_dotenv()

from src import config
from src.generate import MissingApiKeyError
from src.pipeline import RAGPipeline
from src.retrieve import Retriever


st.set_page_config(page_title="de-docs-rag", layout="wide")
st.title("de-docs-rag")
st.caption(
    "Hybrid (dense + BM25) retrieval with cross-encoder re-ranking over "
    "Snowflake / Airflow / Glue docs. Generation by Groq."
)


@st.cache_resource(show_spinner="Loading retriever and re-ranker...")
def _load_pipeline() -> RAGPipeline:
    return RAGPipeline(retriever=Retriever())


if not Path(config.CHROMA_DIR).exists():
    st.error(
        "No index found. Run `python -m src.ingest` first to build the "
        f"Chroma store at `{config.CHROMA_DIR}`."
    )
    st.stop()

pipeline = _load_pipeline()

with st.sidebar:
    st.header("Config")
    st.write(f"Embedding: `{config.EMBED_MODEL_NAME}`")
    st.write(f"Re-ranker: `{config.RERANKER_MODEL_NAME}`")
    st.write(f"LLM: `{config.GROQ_MODEL}`")
    st.write(
        f"Dense k={config.DENSE_TOP_K} | Sparse k={config.SPARSE_TOP_K} "
        f"| Final k={config.FINAL_TOP_K}"
    )
    if not os.environ.get("GROQ_API_KEY"):
        st.warning(
            "GROQ_API_KEY not set. Retrieval works but generation will fail."
        )

question = st.text_input(
    "Ask a question about Snowflake, Airflow, or AWS Glue:",
    value="What is Snowflake automatic clustering?",
)

if st.button("Ask", type="primary") and question.strip():
    with st.spinner("Retrieving and generating..."):
        try:
            answer = pipeline.ask(question.strip(), verbose=False)
        except MissingApiKeyError as e:
            st.error(str(e))
            st.stop()

    st.subheader("Answer")
    st.write(answer.answer)

    st.subheader("Citations")
    for c in answer.citations:
        st.write(f"- `{c.chunk_id}` (score={c.similarity_score})")

    st.subheader("Retrieved chunks")
    for cand in answer.candidates:
        tag = "+".join(sorted(cand.sources))
        with st.expander(
            f"{cand.chunk_id} | from={tag} | rerank={cand.rerank_score}"
        ):
            st.code(cand.text, language="markdown")

    with st.expander("Final prompt sent to the LLM"):
        st.code(answer.prompt, language="text")
