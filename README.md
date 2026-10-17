# The Inkling

The Inkling turns a reader's interests into a daily, newspaper-style edition. This repository is being migrated from an AI-news aggregator to a general-interest personal newspaper.

## Architecture

- **Web client:** React 19, Vite, Tailwind CSS, ESLint, and Prettier.
- **API:** FastAPI with account authentication, preferences, edition, archive, and feedback endpoints.
- **Background work:** Celery workers use Redis for edition jobs and shared rate limits.
- **Persistence:** PostgreSQL stores reader accounts, articles, feedback, and date-keyed edition snapshots.
- **Agent workflow:** LangChain composes structured editorial calls. LangGraph passes typed shared paper state between ranking, editing, and quality nodes; per-run configuration stays in typed runtime context.
- **Observability:** LangSmith receives graph traces when configured.
- **Ingestion:** Topic-tagged RSS/Atom feeds and curated source pages; source fetching has request timeouts.

Architecture flow:

    Reader -> React reader -> FastAPI -> PostgreSQL
                             -> Redis queue -> Celery worker
    Celery worker -> curated RSS sources -> LangGraph paper state
    LangGraph -> topic/feedback ranker -> LangChain semantic reranker
             -> LangChain grounded editor -> quality checks
    LangGraph traces -> LangSmith (when enabled; reader identity is excluded)

The ranker learns from saved, skipped, and longer-read stories. It combines
topic and source preferences with a per-reader TF-IDF feedback model, then applies
a bounded LangChain model rerank to up to 30 candidate stories. The editor
rewrites the selected set in one structured model call and keeps publisher links
intact. If model calls fail, deterministic ranking and publisher summaries
remain available.

Curated source requests run with a bounded pool of eight concurrent fetches. Each
source has a timeout and can fail independently; successful sources still feed
the edition, and results retain curated source order.

## Start locally

### Docker Compose

1. Copy .env.example to .env and set the keys listed below.
2. From the repository root, start the stack:

       docker compose -f docker/docker-compose.yml up --build

3. Open the reader at http://localhost:5173. The API and interactive API docs are at http://localhost:8000 and http://localhost:8000/docs.

The Compose stack includes PostgreSQL, Redis, the API, the Celery worker, and the Vite development server. The API runs Alembic migrations before serving requests, and the worker waits for the API health check.

`render.yaml` defines the API and Celery worker. Both use the Pipenv lockfile and Python 3.12; configure reachable PostgreSQL and Redis URLs, exact frontend origins in `CORS_ORIGINS`, and deploy the Vite client separately. The Blueprint generates `AUTH_SECRET_KEY` and prompts for provider credentials without storing secret values in Git. Render does not offer a free background worker plan, so its worker service uses the smallest paid plan.

### Run API and frontend outside Docker

Run PostgreSQL and Redis, then install dependencies from the repository root:

    python -m pipenv sync
    npm install

Run database migrations, then start the API and worker in separate terminals:

    pipenv run alembic upgrade head
    pipenv run uvicorn app.web:app --reload --port 8000
    pipenv run celery -A app.worker.celery_app worker --loglevel=INFO
    npm run dev

Set DATABASE_URL and REDIS_URL to services reachable from the host. Local development defaults are PostgreSQL on port 5432 and Redis on port 6379.

## Environment and API keys

Keep real values in .env or the deployment provider's secret store. Never commit .env.

| Variable          | Required       | Purpose                                                                                                    |
| ----------------- | -------------- | ---------------------------------------------------------------------------------------------------------- |
| AUTH_SECRET_KEY   | Yes            | Signs login tokens. Use a unique random secret.                                                            |
| GROQ_API_KEY      | For AI editing | LangChain calls the configured Groq model. Without it, the graph keeps source titles and summaries.        |
| LANGSMITH_API_KEY | Optional       | Sends traces to LangSmith. Set LANGSMITH_TRACING=true and LANGSMITH_PROJECT=the-inkling to enable tracing. |
| DATABASE_URL      | Yes            | PostgreSQL connection string. Compose supplies a container-internal default.                               |
| REDIS_URL         | Yes            | Celery broker and shared rate-limit storage. Compose supplies a container-internal default.                |

No Gmail or Stripe keys are needed for the newspaper reader. RSS ingestion does not need a provider API key. .env.example contains placeholders only.

## Edition API

Authenticated routes include:

- GET /api/preferences/paper and PUT /api/preferences/paper
- POST /api/papers to queue today's edition
- GET /api/papers/today to poll its status and read it when ready
- GET /api/papers and GET /api/papers/{edition_id} for archive and reading
- GET /api/papers/{edition_id}/pdf for an authenticated PDF download with publisher links
- POST /api/papers/{edition_id}/feedback for opened, saved, skipped, and dismissed signals

Edition generation is keyed by reader and UTC date, returns immediately after queuing, and records a durable snapshot for the archive.

## Quality commands

    pipenv run lint
    pipenv run format
    pipenv run migrate
    pipenv run ruff check app tests
    pipenv run ruff format --check app tests
    python -m unittest discover -s tests -v
    npm run lint
    npm run format:check
    npm run build

GitHub Actions runs backend lint/format and the personalization checks alongside
frontend lint/format/build on pushes to `main` and pull requests.
