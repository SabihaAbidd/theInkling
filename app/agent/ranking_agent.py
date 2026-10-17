"""LLM-based ranking agent for personalized digest feeds."""

from __future__ import annotations

import json
from dataclasses import dataclass

from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field

from app.agent.model_provider import create_chat_model, default_model, default_provider
from app.profiles.user_profile import UserProfile

DEFAULT_RANKING_MODEL = default_model(default_provider())

RANKING_INSTRUCTIONS = """
You are a personalized AI news ranking agent.
Rank digest items for a user's stated interests.
Prefer items that directly match the user's preferred sources, content types,
and keywords. Also consider semantic relevance: "agentic workflows" should
match an interest in "agents".
Return every candidate exactly once.
Use deterministic, consistent scoring from 0 to 100.
Do not invent facts. Base reasons only on the provided candidate text and profile.
"""

RANKING_PROMPT = ChatPromptTemplate.from_messages(
    [
        ("system", RANKING_INSTRUCTIONS),
        ("human", "Rank this profile against these candidates:\n{ranking_input}"),
    ]
)


class RankedItemsOutput(BaseModel):
    """Validated ordering and relevance notes for article candidates."""

    ranked_items: list["RankedItemOutput"] = Field(min_length=0)


class RankedItemOutput(BaseModel):
    """One article's position and reader relevance."""

    digest_id: int
    rank: int = Field(ge=1)
    relevance_score: int = Field(ge=0, le=100)
    reason: str = Field(max_length=300)


@dataclass(frozen=True)
class LLMRankedItem:
    """One item ranked by the LLM."""

    digest_id: int
    rank: int
    relevance_score: int
    reason: str


class RankingAgent:
    """Ranks digest candidates with the configured LLM and structured JSON output."""

    def __init__(
        self,
        model: str = DEFAULT_RANKING_MODEL,
        api_key: str | None = None,
    ) -> None:
        self.model = model
        self.api_key = api_key

    def rank_digest_items(
        self,
        profile: UserProfile,
        candidates: list[dict],
    ) -> list[LLMRankedItem]:
        """Rank digest candidates for the given user profile."""

        if not candidates:
            return []

        model = create_chat_model(self.model, self.api_key)
        chain = (
            RANKING_PROMPT | model.with_structured_output(RankedItemsOutput)
        ).with_config(
            {"run_name": "reader_relevance_ranker", "tags": ["the-inkling", "ranking"]}
        )
        data = chain.invoke(
            {
                "ranking_input": json.dumps(
                    {
                        "profile": profile_to_payload(profile),
                        "candidates": candidates,
                    },
                    ensure_ascii=False,
                )
            }
        )
        return [
            LLMRankedItem(
                digest_id=int(item["digest_id"]),
                rank=int(item["rank"]),
                relevance_score=int(item["relevance_score"]),
                reason=str(item["reason"]),
            )
            for item in data.ranked_items
        ]


def profile_to_payload(profile: UserProfile) -> dict:
    """Serialize a profile for LLM ranking."""

    return {
        "name": profile.name,
        "preferred_sources": list(profile.preferred_sources),
        "preferred_kinds": list(profile.preferred_kinds),
        "keywords": list(profile.keywords),
        "excluded_keywords": list(profile.excluded_keywords),
        "metadata": profile.metadata,
    }
