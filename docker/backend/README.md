# HealthWatch Backend (`healthwatch-backend`)

[![Docker Image](https://img.shields.io/badge/docker-healthwatch--backend-blue.svg)](https://hub.docker.com)
[![Python](https://img.shields.io/badge/python-3.11-brightgreen.svg)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110+-teal.svg)](https://fastapi.tiangolo.com)
[![PostGIS](https://img.shields.io/badge/PostGIS-3.4-blue.svg)](https://postgis.net)

The official production backend microservice for the **HealthWatch** Disease Surveillance and Contact Tracing platform. Built on **FastAPI**, **SQLAlchemy**, and **GeoAlchemy2**, served by high-concurrency **Gunicorn + Uvicorn** asynchronous workers.

---

## Architecture Overview

`healthwatch-backend` provides:
- **Spatial GIS & Geolocation Engine**: PostGIS spatial indexing (`ST_DWithin`, `ST_MakePoint`, `ST_AsGeoJSON`) for disease clusters, containment zones, and movement roadmaps.
- **Role-Based Access Control (RBAC)**: Secure JWT authentication supporting Public Health Officers, Health Workers, and Patients.
- **Privacy-Preserving Movement Surveillance**: Discrete 15-minute sampling telemetry isolation complying with DISHA/HIPAA healthcare privacy standards.
- **Clinical Surveillance & Outbreak Analytics**: Disease case tracking, contact exposure graphs, and diagnostic metadata.
- **Hardened Execution**: Runs as an unprivileged, non-root system user (`healthwatch:healthwatch`) with read-only application layers.

---

## Environment Variables (`.env`)

All parameters are configurable via an `.env` file or container environment variables:

| Variable | Type | Default | Required | Description |
| :--- | :--- | :--- | :--- | :--- |
| `DATABASE_URL` | String | *None* | **Yes** | PostgreSQL connection URL with PostGIS: `postgresql://user:pass@host:5432/dbname` |
| `SECRET_KEY` | String | *None* | **Yes** | 64-character hex cryptographic secret for signing JWT tokens (`openssl rand -hex 32`) |
| `PORT` | Integer | `8000` | No | Internal HTTP port the Gunicorn process binds to |
| `WORKERS` | Integer | `4` | No | Number of concurrent Gunicorn worker processes (`(2 x CPU Cores) + 1`) |
| `ENVIRONMENT` | String | `production` | No | Application environment mode (`production` or `development`) |
| `DEBUG` | Boolean | `False` | No | Enable verbose debug tracebacks (`True` or `False`) |
| `APP_NAME` | String | `HealthWatch` | No | Application name returned in health check metadata |
| `APP_VERSION` | String | `1.0.0` | No | Application version identifier |
| `API_V1_STR` | String | `/api/v1` | No | URL prefix for REST API version 1 endpoints |
| `BACKEND_CORS_ORIGINS` | JSON Array | `["*"]` | No | Allowed CORS origin URLs (e.g. `["https://healthwatch.example.com"]`) |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Integer | `1440` | No | Validity duration of session JWT access tokens in minutes (1440 = 24 hours) |
| `PASSWORD_RESET_TOKEN_EXPIRE_HOURS` | Integer | `24` | No | Validity duration of password change tokens in hours |
| `ADMIN_EMAIL` | String | `admin@healthwatch.org` | No | Primary administrator account login email |
| `ADMIN_PASSWORD` | String | `Admin@HealthWatch2026` | No | Primary administrator account login password |
| `ADMIN_NAME` | String | `System Administrator` | No | Administrator display name |
| `LOCATION_SAMPLING_INTERVAL_MINUTES`| Integer | `15` | No | Default surveillance discrete sampling interval in minutes |
| `PROXIMITY_ALERT_THRESHOLD_METERS` | Float | `50.0` | No | Contact proximity detection radius in meters |
| `STATIONARY_DRIFT_THRESHOLD_METERS` | Float | `50.0` | No | Maximum GPS displacement considered stationary device drift |

---

## Sample `.env` File (`.env.backend`)

```ini
# Core Configuration
PORT=8000
WORKERS=4
ENVIRONMENT=production
DEBUG=False
APP_NAME=HealthWatch
APP_VERSION=1.0.0
API_V1_STR=/api/v1

# Security Secrets (Generate: openssl rand -hex 32)
SECRET_KEY=9a4f2c1b8e7d3a5f6e8c0b2d4f6a8b1c3e5d7f9a1b3c5e7d9f1a3b5c7e9d1b3f
ACCESS_TOKEN_EXPIRE_MINUTES=1440
PASSWORD_RESET_TOKEN_EXPIRE_HOURS=24

# Initial Administrator Credentials
ADMIN_EMAIL=admin@healthwatch.org
ADMIN_PASSWORD=Admin@HealthWatch2026
ADMIN_NAME=System Administrator

# Database Connection
DATABASE_URL=postgresql://healthwatch_admin:HealthWatch_Prod_Secret_Pass_2026!@db:5432/healthwatch_db

# CORS Allowed Origins
BACKEND_CORS_ORIGINS=["http://healthwatch.example.com","https://healthwatch.example.com","http://localhost"]
```

---

## Quick Start: Standalone `docker run`

To run the backend with an external PostgreSQL/PostGIS database:

```bash
docker run -d \
  --name healthwatch-backend \
  --restart always \
  -p 8000:8000 \
  -e DATABASE_URL="postgresql://user:pass@db-host:5432/healthwatch_db" \
  -e SECRET_KEY="your-64-character-hex-secret-key" \
  -e WORKERS=4 \
  YOUR_DOCKERHUB_USERNAME/healthwatch-backend:1.0.0
```

---

## Docker Compose Configuration

### Standalone Backend + PostGIS Stack

```yaml
version: '3.8'

services:
  db:
    image: postgis/postgis:16-3.4
    container_name: healthwatch-db
    restart: always
    environment:
      POSTGRES_USER: healthwatch_admin
      POSTGRES_PASSWORD: HealthWatch_Prod_Secret_Pass_2026!
      POSTGRES_DB: healthwatch_db
    volumes:
      - postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U healthwatch_admin -d healthwatch_db"]
      interval: 10s
      timeout: 5s
      retries: 5
    networks:
      - healthwatch-net

  backend:
    image: YOUR_DOCKERHUB_USERNAME/healthwatch-backend:1.0.0
    container_name: healthwatch-backend
    restart: always
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql://healthwatch_admin:HealthWatch_Prod_Secret_Pass_2026!@db:5432/healthwatch_db
      - SECRET_KEY=your-64-character-hex-secret-key
      - WORKERS=4
      - ENVIRONMENT=production
    depends_on:
      db:
        condition: service_healthy
    healthcheck:
      test: ["CMD-SHELL", "curl -f http://localhost:8000/api/health || exit 1"]
      interval: 15s
      timeout: 5s
      retries: 3
      start_period: 20s
    networks:
      - healthwatch-net

volumes:
  postgres_data:

networks:
  healthwatch-net:
```

---

## Health Check & Verification

Once running, verify backend operation:

```bash
# Basic Health Status
curl -f http://localhost:8000/api/health
# Response: {"status":"healthy","database":"connected","version":"1.0.0","uptime":"..."}

# OpenAPI Specification
curl -f http://localhost:8000/api/v1/openapi.json

# Interactive Documentation (Swagger UI)
http://localhost:8000/docs
```

---

## Security & Container Hardening

- **Non-Root Execution**: Runs under system user `healthwatch` (`UID 999`), preventing container breakout vulnerabilities.
- **Health Monitoring**: Built-in `HEALTHCHECK` probes `/api/health` every 15 seconds.
- **Resource Recommendations**:
  - Memory: `512MB` minimum, `1GB` recommended
  - CPU: `0.5` cores minimum, `1.0+` cores recommended
