"""Lightweight per-reader content model built from explicit feedback."""

from __future__ import annotations

import math
import re
from collections import Counter
from typing import Any

TOKEN_RE = re.compile(r"[a-z0-9]{2,}")


def feedback_relevance_scores(
    articles: list[dict[str, Any]], feedback: list[dict[str, Any]]
) -> list[float]:
    """Score candidates by TF-IDF similarity to positive and negative signals.

    Saved stories and opens lasting at least 30 seconds are positive examples.
    Skipped and dismissed stories are negative examples. Unlabeled opens are
    ignored. The score is positive similarity minus negative similarity and is
    bounded to [-1, 1], so it can be combined with other ranker signals.
    """

    labeled_feedback = [
        (item, _feedback_label(item)) for item in feedback if _feedback_label(item) != 0
    ]
    article_documents = [_article_tokens(article) for article in articles]
    feedback_documents = [_feedback_tokens(item) for item, _ in labeled_feedback]
    documents = [*article_documents, *feedback_documents]
    if not feedback_documents or not any(article_documents):
        return [0.0] * len(articles)

    inverse_frequency = _inverse_document_frequency(documents)
    article_vectors = [
        _weighted_vector(tokens, inverse_frequency) for tokens in article_documents
    ]
    feedback_vectors = [
        _weighted_vector(tokens, inverse_frequency) for tokens in feedback_documents
    ]

    scores: list[float] = []
    for article_vector in article_vectors:
        positive_scores = [
            _cosine_similarity(article_vector, vector)
            for vector, (_, label) in zip(
                feedback_vectors, labeled_feedback, strict=True
            )
            if label > 0
        ]
        negative_scores = [
            _cosine_similarity(article_vector, vector)
            for vector, (_, label) in zip(
                feedback_vectors, labeled_feedback, strict=True
            )
            if label < 0
        ]
        positive_mean = (
            sum(positive_scores) / len(positive_scores) if positive_scores else 0.0
        )
        negative_mean = (
            sum(negative_scores) / len(negative_scores) if negative_scores else 0.0
        )
        scores.append(max(-1.0, min(1.0, positive_mean - negative_mean)))
    return scores


def _feedback_label(item: dict[str, Any]) -> int:
    action = item.get("action")
    if action == "saved" or (
        action == "opened" and int(item.get("dwell_seconds") or 0) >= 30
    ):
        return 1
    if action in {"skipped", "dismissed"}:
        return -1
    return 0


def _article_tokens(article: dict[str, Any]) -> Counter[str]:
    title = str(article.get("title", ""))
    summary = str(article.get("summary", ""))
    content = str(article.get("content", ""))
    return Counter(
        [
            *_tokens(title),
            *_tokens(title),
            *_tokens(title),
            *_tokens(summary),
            *_tokens(content),
        ]
    )


def _feedback_tokens(item: dict[str, Any]) -> Counter[str]:
    return Counter([*_tokens(item.get("title", "")), *_tokens(item.get("summary", ""))])


def _tokens(value: Any) -> list[str]:
    return TOKEN_RE.findall(str(value).casefold())


def _inverse_document_frequency(
    documents: list[Counter[str]],
) -> dict[str, float]:
    document_frequency: Counter[str] = Counter()
    for document in documents:
        document_frequency.update(document.keys())
    document_count = len(documents)
    return {
        token: math.log((1 + document_count) / (1 + frequency)) + 1
        for token, frequency in document_frequency.items()
    }


def _weighted_vector(
    tokens: Counter[str], inverse_frequency: dict[str, float]
) -> dict[str, float]:
    weights = {
        token: (1 + math.log(count)) * inverse_frequency[token]
        for token, count in tokens.items()
        if count and token in inverse_frequency
    }
    magnitude = math.sqrt(sum(weight * weight for weight in weights.values()))
    if not magnitude:
        return {}
    return {token: weight / magnitude for token, weight in weights.items()}


def _cosine_similarity(left: dict[str, float], right: dict[str, float]) -> float:
    if not left or not right:
        return 0.0
    return sum(weight * right.get(token, 0.0) for token, weight in left.items())
