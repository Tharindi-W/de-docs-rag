"""Prompt construction + Groq LLM call. Groq exposes an OpenAI-compatible API,
so we reuse the openai Python client and just point base_url at Groq."""
from __future__ import annotations

import os
from dataclasses import dataclass

from openai import OpenAI

from . import config
from .retrieve import Candidate


SYSTEM_PROMPT = (
    "You are a data engineering documentation assistant. "
    "Answer the user's question USING ONLY the context passages provided. "
    "If the context does not contain enough information to answer, reply "
    "exactly: \"I don't have enough information in the provided docs.\" "
    "When you use a fact, cite the source document inline like "
    "[snowflake_clustering.md]. Be concise and technical."
)


class MissingApiKeyError(RuntimeError):
    pass


@dataclass
class GenerationResult:
    answer: str
    prompt: str


def _format_context(candidates: list[Candidate]) -> str:
    blocks = []
    for c in candidates:
        blocks.append(f"[{c.source_doc}] (chunk={c.chunk_id})\n{c.text}")
    return "\n\n---\n\n".join(blocks)


def build_prompt(question: str, candidates: list[Candidate]) -> str:
    context = _format_context(candidates) if candidates else "(no context retrieved)"
    return (
        f"Context passages:\n{context}\n\n"
        f"Question: {question}\n\n"
        f"Answer (cite sources inline like [filename.md]):"
    )


def _client() -> OpenAI:
    key = os.environ.get("GROQ_API_KEY")
    if not key:
        raise MissingApiKeyError(
            "GROQ_API_KEY is not set. Copy .env.example to .env and add your free "
            "key from https://console.groq.com/keys, or `export GROQ_API_KEY=...`."
        )
    return OpenAI(api_key=key, base_url=config.GROQ_BASE_URL)


def generate(question: str, candidates: list[Candidate]) -> GenerationResult:
    prompt = build_prompt(question, candidates)
    client = _client()
    resp = client.chat.completions.create(
        model=config.GROQ_MODEL,
        temperature=config.GROQ_TEMPERATURE,
        max_tokens=config.GROQ_MAX_TOKENS,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
    )
    answer = resp.choices[0].message.content or ""
    return GenerationResult(answer=answer.strip(), prompt=prompt)
