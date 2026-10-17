"""Gemini-powered agent for creating digest summaries."""

from __future__ import annotations

import json
from dataclasses import dataclass

from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field

from app.agent.llm_client import default_model, default_provider
from app.agent.model_provider import create_chat_model
from app.database.models import NewsItem

DEFAULT_DIGEST_MODEL = default_model(default_provider())

DIGEST_INSTRUCTIONS = """
You are an AI news digest editor.
Your job is to turn one scraped news item into a useful digest entry.
Write a concise, factual title and a two to three sentence summary.
Prefer concrete details from the source item. Do not invent facts.
If the source item is weak or navigation-like, summarize only what is clearly present.
"""


class DigestOutput(BaseModel):
    """Validated summary generated from one source item."""

    title: str = Field(min_length=1, max_length=180)
    summary: str = Field(min_length=1, max_length=900)


DIGEST_PROMPT = ChatPromptTemplate.from_messages(
    [("system", DIGEST_INSTRUCTIONS), ("human", "Source item:\n{article}")]
)


@dataclass(frozen=True)
class DigestAgentResult:
    """Structured output returned by the digest agent."""

    title: str
    summary: str
    model: str
    response_id: str | None
    raw_response: dict


class DigestAgent:
    """Creates short structured digest entries through LangChain."""

    def __init__(
        self,
        model: str = DEFAULT_DIGEST_MODEL,
        api_key: str | None = None,
    ) -> None:
        self.model = model
        self.api_key = api_key

    def summarize_news_item(self, news_item: NewsItem) -> DigestAgentResult:
        """Generate one digest entry for a database news item."""

        model = create_chat_model(self.model, self.api_key)
        chain = (
            DIGEST_PROMPT | model.with_structured_output(DigestOutput)
        ).with_config(
            {"run_name": "article_digest_editor", "tags": ["the-inkling", "digest"]}
        )
        payload = chain.invoke({"article": build_digest_input(news_item)})
        return DigestAgentResult(
            title=payload.title.strip(),
            summary=payload.summary.strip(),
            model=self.model,
            response_id=None,
            raw_response=payload.model_dump(mode="json"),
        )


def build_digest_input(news_item: NewsItem) -> str:
    """Build the model input from a stored news item."""

    metadata = json.dumps(news_item.item_metadata or {}, ensure_ascii=False)
    parts = [
        f"Source: {news_item.source}",
        f"Type: {news_item.kind}",
        f"Original title: {news_item.title}",
        f"URL: {news_item.url}",
        f"Published at: {news_item.published_at}",
        f"Scraped summary: {news_item.summary or ''}",
        f"Content: {news_item.content or ''}",
        f"Transcript: {news_item.transcript or ''}",
        f"Metadata: {metadata}",
    ]
    return "\n".join(parts)
