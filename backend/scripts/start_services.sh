#!/usr/bin/env bash
set -euo pipefail

# Start Postgres and Redis using the repository docker-compose.yml
# Run from repo root: ./backend/scripts/start_services.sh

docker-compose up -d postgres redis

echo "Started Postgres and Redis (docker-compose services: postgres, redis)."
