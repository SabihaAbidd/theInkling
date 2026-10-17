"""LangChain chat model construction for configured providers."""

from __future__ import annotations

import os

from langchain_groq import ChatGroq

DEFAULT_MODEL = "openai/gpt-oss-120b"


def create_chat_model(
    model_name: str | None = None,
    api_key: str | None = None,
) -> ChatGroq:
    """Build the Groq LangChain chat model using environment configuration."""

    provider = os.getenv("LLM_PROVIDER", "groq").strip().lower()
    if provider != "groq":
        raise ValueError(f"Unsupported LLM_PROVIDER {provider!r}; use 'groq'.")

    selected_api_key = api_key or os.getenv("GROQ_API_KEY")
    if not selected_api_key:
        raise RuntimeError("Missing GROQ_API_KEY in environment.")

    return ChatGroq(
        model=model_name or os.getenv("LLM_MODEL", DEFAULT_MODEL),
        api_key=selected_api_key,
        temperature=0,
        max_retries=2,
        timeout=45,
    )
