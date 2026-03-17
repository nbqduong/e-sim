#!/usr/bin/env bash
set -euo pipefail

# Start the FastAPI dev server
# Usage: ./backend/scripts/start_app.sh

cd "$(dirname "$0")/.."

if [ -f .venv/bin/activate ]; then
  # shellcheck disable=SC1091
  source .venv/bin/activate
fi

uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
