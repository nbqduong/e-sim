#!/usr/bin/env bash
set -euo pipefail

# Run Alembic migrations for the backend
# Usage: ./backend/scripts/run_migrations.sh

cd "$(dirname "$0")/.."

# Activate venv if exists
if [ -f .venv/bin/activate ]; then
  # shellcheck disable=SC1091
  source .venv/bin/activate
fi

# Install requirements if alembic not available
if ! command -v alembic >/dev/null 2>&1; then
  pip install -r requirements.txt
fi

# Ensure DATABASE_URL is set (example below)
: "${DATABASE_URL:=postgresql+asyncpg://postgres:postgres@localhost:5432/esim}"
export DATABASE_URL
export PYTHONPATH="$(pwd)${PYTHONPATH:+:$PYTHONPATH}"

# Run alembic from backend folder
alembic -c alembic.ini upgrade head

echo "Migrations applied."
