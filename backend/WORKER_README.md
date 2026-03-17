Quick guide: run services, migrations, worker, and app

Prerequisites
- Docker & docker-compose installed
- (Optional) Python 3.11+ and a virtualenv if you want to run locally without containers

1) Start Postgres + Redis (docker-compose services)

From repo root:

```bash
./backend/scripts/start_services.sh
```

This starts `postgres` and `redis` services defined in the repository `docker-compose.yml`.

2) Configure env

Create a backend `.env` (or export environment variables) with at least:

- `DATABASE_URL` — e.g. `postgresql+asyncpg://postgres:postgres@localhost:5432/esim`
- `REDIS_URL` — e.g. `redis://localhost:6379/0`

You can copy the repo root `.env` to `backend/.env` and add `DATABASE_URL`/`REDIS_URL`.

3) Run DB migrations

From `backend/`:

```bash
./scripts/run_migrations.sh
```

This runs `alembic upgrade head` against `DATABASE_URL`.

4) Start Celery worker

From `backend/` (or use the script):

```bash
./scripts/start_worker.sh
```

This runs:

```bash
celery -A app.celery_app.celery worker --loglevel=info -Q default
```

5) Start the API server

From `backend/`:

```bash
./scripts/start_app.sh
```

6) Smoke test the export flow

- Authenticate and obtain a `session_token` using the frontend flow (or call the OAuth flow endpoints).
- Create a document via `POST /api/documents`.
- Trigger export:

```bash
curl -X POST "http://localhost:8000/api/documents/<DOCUMENT_ID>/drive" -H "X-Session-Token: <SESSION_TOKEN>"
```

This will create a `Task` and enqueue a Celery task. Check tasks:

```bash
curl -H "X-Session-Token: <SESSION_TOKEN>" "http://localhost:8000/api/tasks"
curl -H "X-Session-Token: <SESSION_TOKEN>" "http://localhost:8000/api/tasks/<TASK_ID>"
```

Notes & troubleshooting
- If you can't run Celery, the documents endpoint falls back to an in-process background task (no broker needed).
- Ensure `GOOGLE_CLIENT_ID`/`GOOGLE_CLIENT_SECRET` are set in env for Drive operations.
- For production, run workers with process supervisors and secure secrets in a vault.
