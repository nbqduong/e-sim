# e-sim Backend (FastAPI)

FastAPI backend for authenticated local project/document management. The current runtime focuses on:

- serving frontend assets and API responses
- logging users in with Google OAuth
- CRUD for projects and documents
- staying simple enough to support future crypto-focused services without a worker tier

## Features

- **Google login** - issues short-lived OAuth state, exchanges auth codes, and sets a signed session cookie.
- **Project and document CRUD** - stores per-user content in Postgres through SQLAlchemy + Alembic.
- **Redis-backed auth state** - Google OAuth state tokens are shared across instances for multi-node deployments.
- **Container-ready** - env-file driven configuration plus a Docker image for local and production deployment.

## Project structure

- Application source lives in [app/](app).
  - [app/main.py](app/main.py) wires routers, middleware, and frontend serving.
  - [app/api/routes/auth.py](app/api/routes/auth.py), [app/api/routes/projects.py](app/api/routes/projects.py), and [app/api/routes/documents.py](app/api/routes/documents.py) expose the REST API.
  - [app/services/](app/services) handles OAuth and session logic.
  - [app/models/](app/models), [app/repositories/](app/repositories/), and [alembic/](alembic/) provide persistence.
- [requirements.txt](requirements.txt) pins Python dependencies.
- [Dockerfile](Dockerfile) builds a deployable image.
- [.env.example](.env.example) lists required configuration.

## Getting started

1. **Install dependencies**

   ```bash
   python -m venv .venv
   source .venv/bin/activate
   pip install --upgrade pip
   pip install -r requirements.txt
   ```

2. **Configure environment**

   ```bash
   cp .env.example .env
   # fill in GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET, SESSION_SECRET, DATABASE_URL, REDIS_URL, etc.
   ```

3. **Run the API**

   ```bash
   uvicorn app.main:app --reload
   ```

   The service listens on `http://localhost:8000`.

4. **Build & run with Docker**

   ```bash
   docker build -t e-sim-backend .
   docker run --rm -p 8000:8000 --env-file .env e-sim-backend
   ```

## Nginx reverse proxy

For production, the repo includes an Nginx config at `deploy/nginx/backend.conf` that forwards incoming traffic to the backend container on port `8000`.

- `docker-compose.prod.yml` exposes Nginx on port `80`.
- Set `GOOGLE_REDIRECT_URI` in `.env` to your public HTTPS origin before deploying.
- Set `SESSION_COOKIE_SECURE=true` when the public site is served over HTTPS.

## Google Cloud setup

1. Create OAuth 2.0 Client Credentials with type **Web Application**.
2. Add your callback URL to the authorized redirect URIs.
   - Local example: `http://localhost:8000/auth/google/callback`
   - Nginx example: `https://your-domain.example/auth/google/callback`
3. Store the client ID and client secret in your env file.

### Storage CORS Configuration

Because the frontend project uploads and downloads files directly from the browser using Signed URLs via the Google Cloud Storage API, your associated GCS bucket must be configured with a proper CORS (Cross-Origin Resource Sharing) policy to prevent blocked requests.

1. Create a file named `cors.json` with the following content. Make sure to adjust the `origin` array to perfectly match your frontend development and production URLs:
   ```json
   [
       {
           "origin": [
               "http://localhost:8000",
               "http://localhost:5173",
               "https://your-domain.example"
           ],
           "method": ["GET", "PUT", "POST", "OPTIONS", "HEAD", "DELETE"],
           "responseHeader": ["*"],
           "maxAgeSeconds": 3600
       }
   ]
   ```
2. Apply this CORS policy to your bucket using the Google Cloud CLI (`gcloud`):
   ```bash
   gcloud storage buckets update gs://<YOUR_BUCKET_NAME> --cors-file=cors.json
   ```

## API workflow

1. Frontend calls `GET /auth/google/login`.
2. After consent, Google redirects to `GET /auth/google/callback?code=...&state=...`.
3. The callback sets a `session_token` cookie and redirects the browser back into the app.
4. Authenticated requests use `/api/projects` and `/api/documents` for local CRUD.

## Notes

- Persisted data lives in the database configured by `DATABASE_URL`; run Alembic migrations before first launch.
- Redis is required for shared OAuth state and rate limiting; set `REDIS_URL` for local and production environments.
- The API is CORS-enabled for localhost frontends by default. Adjust `CORS_ALLOW_ORIGINS` as needed.
- Historical Drive/task migrations remain in the repo for compatibility, but the runtime no longer depends on that stack.
