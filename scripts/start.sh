#!/bin/sh
# Container entrypoint: migrate, optionally load demo data, then serve.
set -e

alembic upgrade head

# Hosts without shell access (e.g. Render free tier) can't run the seed by hand.
# The seed is idempotent: it does nothing if the demo user already exists.
if [ "$SEED_DEMO" = "true" ]; then
    python -m scripts.seed
fi

exec uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8000}"
