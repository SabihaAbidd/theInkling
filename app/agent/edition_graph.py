"""LangGraph workflow that ranks and edits a reader's daily paper."""

from __future__ import annotations

import re
from collections.abc import Mapping
from typing import Any
from urllib.parse import urlparse

from langchain_core.prompts import ChatPromptTemplate
from langgraph.graph import END, START, StateGraph
from langgraph.runtime import Runtime
from pydantic import BaseModel, Field

from app.agent.context import ArticleRecord, PaperRunContext, PaperState, ReaderProfile
from app.agent.model_provider import create_chat_model


class ArticleEdit(BaseModel):
    """Short, source-grounded editorial copy for one article."""

    headline: str = Field(min_length=1, max_length=180)
    summary: str = Field(min_length=1, max_length=800)


EDIT_PROMPT = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            "You are a careful newspaper editor. Use only supplied article details. "
            "Do not add unsupported claims.",
        ),
        (
            "human",
            "Reader interests: {interests}\nSource: {source}\nTitle: {title}\n"
            "Article text: {content}\nExisting summary: {summary}",
        ),
    ]
)


def rank_articles(
    state: PaperState, runtime: Runtime[PaperRunContext]
) -> dict[str, Any]:
    """Rank articles with transparent lexical preference signals."""

    del runtime
    profile = state.get("reader_profile", {})
    topics = _normalized_terms(profile)
    preferred_sources = {
        value.casefold() for value in profile.get("preferred_sources", [])
    }
    excluded = {value.casefold() for value in profile.get("excluded_keywords", [])}
    candidates: list[ArticleRecord] = []

    for article in state.get("articles", []):
        title = str(article.get("title", ""))
        summary = str(article.get("summary", ""))
        content = f"{title} {summary} {article.get('content', '')}".casefold()
        source = str(article.get("source", ""))
        if any(term in content for term in excluded):
            continue

        reasons = [term for term in topics if term in content]
        score = (len(reasons) * 10) + (
            5 if source.casefold() in preferred_sources else 0
        )
        if article.get("published_at"):
            score += 1
        candidate = dict(article)
        candidate["score"] = float(score)
        candidate["reasons"] = reasons
        candidates.append(candidate)

    candidates.sort(
        key=lambda item: (
            float(item.get("score", 0)),
            item.get("published_at") or "",
            str(item.get("title", "")).casefold(),
        ),
        reverse=True,
    )
    return {"ranked_articles": candidates}


def edit_articles(
    state: PaperState,
    runtime: Runtime[PaperRunContext],
) -> dict[str, Any]:
    """Use LangChain structured output for source-grounded article edits."""

    context = runtime.context
    limit = max(1, min(context.get("max_articles", 10), 20))
    selected = state.get("ranked_articles", [])[:limit]
    if not context.get("llm_enabled", True):
        return {"paper_articles": selected}

    try:
        model = create_chat_model(context.get("model_name"))
        editor = (EDIT_PROMPT | model.with_structured_output(ArticleEdit)).with_config(
            {"run_name": "newspaper_article_editor", "tags": ["the-inkling", "editor"]}
        )
        profile = state.get("reader_profile", {})
        interests = ", ".join(_normalized_terms(profile)) or "general news"
        edited: list[ArticleRecord] = []
        for source_article in selected:
            result = editor.invoke(
                {
                    "interests": interests,
                    "source": source_article.get("source", "Unknown source"),
                    "title": source_article.get("title", "Untitled article"),
                    "content": str(source_article.get("content", ""))[:6000],
                    "summary": source_article.get("summary", ""),
                }
            )
            article = dict(source_article)
            article["title"] = result.headline
            article["summary"] = result.summary
            edited.append(article)
        return {"paper_articles": edited}
    except Exception as exc:
        return {
            "paper_articles": selected,
            "issues": [f"editor_fallback:{type(exc).__name__}"],
        }


def quality_check(
    state: PaperState, runtime: Runtime[PaperRunContext]
) -> dict[str, Any]:
    """Remove duplicate or unsafe article URLs and report output health."""

    del runtime
    cleaned: list[ArticleRecord] = []
    seen: set[str] = set()
    for article in state.get("paper_articles", []):
        url = str(article.get("url", "")).strip()
        parsed = urlparse(url)
        canonical = url.split("#", 1)[0].rstrip("/").casefold()
        if (
            parsed.scheme not in {"http", "https"}
            or not parsed.netloc
            or canonical in seen
        ):
            continue
        article["url"] = url
        seen.add(canonical)
        cleaned.append(article)

    return {
        "paper_articles": cleaned,
        "quality_report": {
            "article_count": len(cleaned),
            "unique_urls": len(seen),
            "valid": bool(cleaned) and len(cleaned) == len(seen),
        },
    }


def build_edition_graph():
    """Compile the agent workflow with a typed shared state and run context."""

    graph = StateGraph(PaperState, context_schema=PaperRunContext)
    graph.add_node("personalization_ranker", rank_articles)
    graph.add_node("editor", edit_articles)
    graph.add_node("quality_check", quality_check)
    graph.add_edge(START, "personalization_ranker")
    graph.add_edge("personalization_ranker", "editor")
    graph.add_edge("editor", "quality_check")
    graph.add_edge("quality_check", END)
    return graph.compile()


def create_edition(
    *,
    reader_profile: ReaderProfile,
    articles: list[ArticleRecord],
    model_name: str,
    llm_enabled: bool = True,
    max_articles: int = 10,
    run_id: str | None = None,
) -> PaperState:
    """Run the typed-state agent graph for one edition."""

    input_state: PaperState = {"reader_profile": reader_profile, "articles": articles}
    context: PaperRunContext = {
        "model_name": model_name,
        "llm_enabled": llm_enabled,
        "max_articles": max_articles,
    }
    if run_id:
        context["run_id"] = run_id

    graph = build_edition_graph().with_config(
        {
            "run_name": "the_inkling_daily_edition",
            "tags": ["the-inkling", "daily-paper"],
            "metadata": {"graph_version": "v1", "run_id": run_id or "local"},
        }
    )
    return graph.invoke(input_state, context=context)


def _normalized_terms(profile: Mapping[str, list[str]]) -> list[str]:
    values = [*profile.get("topics", []), *profile.get("keywords", [])]
    return list(
        dict.fromkeys(
            re.sub(r"\s+", " ", value.strip()).casefold()
            for value in values
            if value.strip()
        )
    )
