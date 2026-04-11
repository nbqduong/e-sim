#!/bin/sh
set -eu

export PYTHONPATH="${APP_DIR:-/home/worker/source}${PYTHONPATH:+:$PYTHONPATH}"

echo "Applying database migrations..."
alembic -c alembic.ini upgrade head

echo "Starting backend server..."
exec uvicorn app.main:app --host 0.0.0.0 --port 8000 --proxy-headers --forwarded-allow-ips='*'
