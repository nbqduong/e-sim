#!/usr/bin/env bash
set -euo pipefail

# Start Postgres using the repository docker-compose.yml
# Run from repo root: ./backend/scripts/start_services.sh

docker compose up -d postgres

echo "Started Postgres (docker compose service: postgres)."
