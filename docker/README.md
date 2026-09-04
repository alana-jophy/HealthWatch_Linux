# HealthWatch Docker & Infrastructure Architecture

This directory houses container definitions and orchestration assets for the HealthWatch platform.

## Services
1. **`db`**: `postgis/postgis:16-3.4` (PostgreSQL with PostGIS extension).
2. **`backend`**: FastAPI backend service on Python 3.11 with libgeos/libpq.
3. **`frontend`**: React + TypeScript + Vite developer server on Node 20.

## Running in WSL / Ubuntu 24.04
From the project root:
```bash
docker compose up --build
```
