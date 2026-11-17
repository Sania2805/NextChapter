#!/usr/bin/env bash
set -eu

python -m alembic -c backend/alembic.ini upgrade head
exec python -m uvicorn main:app --app-dir backend --host 0.0.0.0 --port "${PORT:?Render provides PORT}"
