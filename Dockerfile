# ---- build stage: install dependencies into a virtualenv ----
FROM python:3.12-slim AS builder

ENV PIP_NO_CACHE_DIR=1 PIP_DISABLE_PIP_VERSION_CHECK=1
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

WORKDIR /build
COPY pyproject.toml ./
COPY app ./app
RUN pip install .

# ---- runtime stage: slim image, non-root user ----
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PATH="/opt/venv/bin:$PATH" PORT=8000
RUN useradd --create-home --uid 1000 appuser

WORKDIR /srv
COPY --from=builder /opt/venv /opt/venv
COPY app ./app
COPY alembic ./alembic
COPY alembic.ini ./
COPY scripts ./scripts

USER appuser
EXPOSE 8000

# Apply pending migrations, then serve. Render injects $PORT.
CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port ${PORT}"]
