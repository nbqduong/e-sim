# E-Sim

This project uses Docker and Docker Compose for development and deployment.

## Prerequisites

Ensure you have the following installed on your system:
- [Git](https://git-scm.com/downloads)
- [Docker](https://docs.docker.com/get-docker/)
- [Docker Compose](https://docs.docker.com/compose/install/) (usually included with Docker Desktop)

## Getting Started

To initialize the project and start the application, run the following commands in the project root:

```bash
git submodule update --init
docker compose up frontend --build && docker compose up backend --build
```

This will:
1. Initialize submodules (including `cpp-web`).
2. Build and run the `frontend` service (including any dependencies like `testapp` and `cpp-web`).
3. Build and run the `backend` service (including `postgres` and `redis`).

The backend will be available at `http://localhost:8000`.
