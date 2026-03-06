# e-sim Backend (FastAPI)

FastAPI reference implementation that powers the "edit text and sync to Google Drive" workflow. It demonstrates how to:

- authenticate users with Google OAuth
- let authenticated users author text documents
- export document content to Google Drive on demand

## Features

- **Google login** - issues short-lived OAuth states, exchanges auth codes, and creates signed session tokens your frontend can store.
- **Document management** - JSON-backed store keeps per-user drafts with title, body, timestamps, and Drive metadata.
- **Drive export** - uploads or updates plain-text files inside the Drive folder you configure, refreshing OAuth credentials when needed.
- **Portable config** - env-file driven settings (see [.env.example](.env.example)) plus container-ready [Dockerfile](Dockerfile).

## Project structure

- Application source lives in [app/](app).
  - [app/main.py](app/main.py) wires routers and middleware.
  - [app/api/routes/auth.py](app/api/routes/auth.py) and [app/api/routes/documents.py](app/api/routes/documents.py) expose the REST surface.
  - [app/services/](app/services) covers Google OAuth, Drive exports, and session management.
  - [app/storage/](app/storage) implements lightweight JSON persistence for user tokens and documents.
- [requirements.txt](requirements.txt) pins Python dependencies.
- [Dockerfile](Dockerfile) builds a deployable image.
- [.env.example](.env.example) lists mandatory secrets.

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
	# fill in GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET, SESSION_SECRET, etc.
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

## Google Cloud setup

1. Create OAuth 2.0 Client Credentials (type **Web Application**).
2. Add `http://localhost:8000/auth/google/callback` to the authorized redirect URIs.
3. Enable the **Google Drive API** for the project.
4. Store the Client ID/Secret inside your env file (the copy of [.env.example](.env.example)).
5. (Optional) Create or choose a Drive folder and place its ID in `GOOGLE_DRIVE_PARENT_ID` so exports land in a fixed location.

## API workflow

1. Frontend calls `GET /auth/google/login` to retrieve the Google authorization URL.
2. After the user consents, Google redirects to `GET /auth/google/callback?code=...&state=...`.
3. The callback returns a `session_token`. Send it in the `X-Session-Token` header for every document request.
4. Use the `/documents` endpoints to create or update text.
5. Trigger `/documents/{id}/drive` to push the latest content to Google Drive. The response echoes the Drive file ID and URL.

## Notes

- This starter stores data under `DATA_DIR` (defaults to `./data`). Mount a persistent volume in production.
- Tokens and documents sit in plain JSON for clarity; swap in a database by rewriting the store classes.
- The API is CORS-enabled for localhost frontends (ports 3000 and 5173 by default). Adjust `CORS_ALLOW_ORIGINS` as needed.
