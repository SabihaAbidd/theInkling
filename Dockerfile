FROM python:3.12-slim

ENV PIPENV_NOSPIN=1 \
    PIPENV_VENV_IN_PROJECT=0 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /workspace

RUN pip install --no-cache-dir pipenv==2026.10.0

COPY Pipfile Pipfile.lock ./
RUN pipenv sync

COPY app ./app
COPY alembic.ini ./alembic.ini
COPY migrations ./migrations

EXPOSE 8000
