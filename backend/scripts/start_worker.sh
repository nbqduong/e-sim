#!/usr/bin/env bash
set -euo pipefail

# Start Celery worker for the backend
# Usage: ./backend/scripts/start_worker.sh

cd "$(dirname "$0")/.."

if [ -f .venv/bin/activate ]; then
  # shellcheck disable=SC1091
  source .venv/bin/activate
fi

# Make sure celery is installed
if ! python -c "import celery" >/dev/null 2>&1; then
  pip install -r requirements.txt
fi

# Start a worker listening on default queue
celery -A app.celery_app.celery worker --loglevel=info -Q default -n worker.%h
