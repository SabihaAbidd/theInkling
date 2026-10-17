# The Inkling Product Brief

## Problem

Readers need a useful morning overview without manually checking many news sites. The product brief is the NaSCon '26 problem statement in the repository root.

## Product promise

The Inkling creates a personal, general-interest newspaper from a reader's selected subjects and learns from article feedback. Each edition reads like a compact paper and links to each publisher's original reporting.

## Primary reader jobs

1. Choose topics and a few editorial preferences during onboarding.
2. Read today's edition in a newspaper-style web reader.
3. Open a publisher's original story, save it, or signal that it is not relevant.
4. Return to previous editions through an archive.
5. Improve future recommendations as the system receives feedback.

## Product boundaries

- General news is the default; AI news is one optional interest area.
- Sources are curated and attributed. The product links to original articles.
- Accounts are retained for private preferences and edition history.
- Payment checkout and Gmail sending are outside the core reader experience.
- LLM editing must stay grounded in fetched source text and fall back to publisher copy.
- Article feedback is append-only. Preferences and feedback remain scoped to the authenticated reader.

## Current delivery state

- Shipped foundation: authenticated accounts, topic-tagged feeds, a typed LangGraph edition workflow, persistent editions and feedback, Celery/Redis edition jobs, rate limits, and LangSmith configuration.
- Shipped: reader onboarding, topic/source preferences, TF-IDF feedback ranking, a LangChain model reranker, grounded batch editing, the daily/archived web reader, and authenticated PDF downloads.
- Shipped: retired billing, review, digest, transcript, and source-run models were removed from the live schema. Alembic archives existing legacy tables under `legacy_*` names so their rows remain recoverable.

## Acceptance criteria

- A reader can create an account and choose general-interest topics.
- A daily paper can be queued without holding an API worker during ingestion and editing.
- Editions are persisted by reader and date and can be reopened from the archive.
- Every story links to its original publisher and exposes reader feedback controls.
- Feedback signals are available to later ranking runs.
- Agent runs are observable through LangSmith when configured, with no secrets or direct identifying profile fields in trace metadata.
