# HealthWatch Docker & Container Architecture Guide

This directory houses the container definitions, production compose profiles, environment templates, and publishing automation for the **HealthWatch** Disease Surveillance and Contact Tracing Platform.

---

## Container Topology & Microservices

```
                           Internet / Mobile App / Browser
                                        │
                                        ▼ (Port 80 / 443)
                    ┌───────────────────────────────────────┐
                    │          healthwatch-gateway          │
                    │   Nginx Alpine + Let's Encrypt SSL    │
                    └───────────────────┬───────────────────┘
                                        │
                 ┌──────────────────────┴──────────────────────┐
                 │                                             │
      Path: /api/*, /docs, /redoc                   Path: /*, /HealthWatch.apk
                 │                                             │
                 ▼                                             ▼
  ┌─────────────────────────────┐               ┌─────────────────────────────┐
  │     healthwatch-backend     │               │    healthwatch-frontend     │
  │  FastAPI + Python 3.11 GIS  │               │ React 18 SPA + APK Download │
  └──────────────┬──────────────┘               └─────────────────────────────┘
                 │
                 ▼ (Internal Port 5432)
  ┌─────────────────────────────┐
  │         Database            │
  │   PostgreSQL 16 + PostGIS   │
  └─────────────────────────────┘
```

---

## Image Catalog & Documentation Pages

Each microservice has its own dedicated Docker Hub README and sample environment configuration:

| Microservice Image | Purpose | Base OS | Dedicated Docs | Sample `.env` |
| :--- | :--- | :--- | :--- | :--- |
| **`healthwatch-backend`** | FastAPI REST API, PostGIS spatial queries, JWT auth, outbreak analytics | Python 3.11 Slim | [backend/README.md](file:///home/alana/Desktop/healthwatch/docker/backend/README.md) | [env.backend.sample](file:///home/alana/Desktop/healthwatch/docker/env.backend.sample) |
| **`healthwatch-frontend`** | React 18 SPA, Leaflet maps, Kerala geo-hierarchy, pre-built APK downloads | Nginx 1.25 Alpine | [frontend/README.md](file:///home/alana/Desktop/healthwatch/docker/frontend/README.md) | [env.frontend.sample](file:///home/alana/Desktop/healthwatch/docker/env.frontend.sample) |
| **`healthwatch-gateway`** | Unified reverse proxy, Let's Encrypt TLS termination, rate limiting | Nginx Alpine | [gateway/README.md](file:///home/alana/Desktop/healthwatch/docker/gateway/README.md) | [env.gateway.sample](file:///home/alana/Desktop/healthwatch/docker/env.gateway.sample) |
| **`postgis/postgis:16-3.4`** | PostgreSQL database with spatial GIS extension | Debian Bullseye | Official Docker Hub | (Included in fullstack env) |
| **`certbot/certbot:latest`** | Automated SSL certificate renewal daemon | Alpine Linux | Official Docker Hub | (Managed by Gateway) |

---

## Directory Layout

```
docker/
├── backend/
│   └── README.md              # Docker Hub overview documentation for healthwatch-backend
├── frontend/
│   └── README.md              # Docker Hub overview documentation for healthwatch-frontend
├── gateway/
│   └── README.md              # Docker Hub overview documentation for healthwatch-gateway
├── env.backend.sample         # Standalone backend environment variable template
├── env.frontend.sample        # Standalone frontend environment variable template
├── env.gateway.sample         # Standalone gateway environment variable template
├── env.fullstack.sample       # Unified master environment file for production stack
├── docker-compose.hub.yml     # Complete stack compose file configured for Docker Hub images
├── Dockerfile.backend         # Multi-stage production build for FastAPI + PostGIS
├── Dockerfile.frontend        # Production build for React 18 SPA + APK packaging
├── push_to_dockerhub.sh       # Automated CLI script to tag, push, and sync READMEs
└── README.md                  # This file
```

---

## Pushing Images & READMEs to Docker Hub

The automation script `push_to_dockerhub.sh` handles:
1. Tagging local images (`1.0.0` and `latest`).
2. Pushing all images to your Docker Hub repository.
3. Authenticating with Docker Hub's REST API to update the **Repository Overview (README)** for all 3 images automatically.

### Option 1: Interactive Execution
```bash
./docker/push_to_dockerhub.sh
```
The script will prompt for:
- Docker Hub Username / Organization
- Docker Hub Personal Access Token (PAT) with `Read & Write` permissions (or press ENTER to skip README API update)

### Option 2: Automated CI/CD Execution
```bash
# Export credentials
export DOCKERHUB_USER="your-dockerhub-username"
export DOCKERHUB_TOKEN="dckr_pat_xxxxxxxxxxxxxxxxxxxxxxxxxx"

# Run publisher
./docker/push_to_dockerhub.sh -u "$DOCKERHUB_USER" --token "$DOCKERHUB_TOKEN" --tag 1.0.0
```

### Option 3: Dry-Run (Preview Actions)
```bash
./docker/push_to_dockerhub.sh -u your-dockerhub-username --dry-run
```

> **Note on Docker Hub Personal Access Tokens (PAT)**:
> Generate a token at [Docker Hub Security Settings](https://hub.docker.com/settings/security) with **Read & Write** access.

---

## Deploying Anywhere from Docker Hub

To deploy HealthWatch on any cloud server or VPS using the published images:

### Step 1: Copy Compose and Env Files
```bash
# Download production compose file
curl -O https://raw.githubusercontent.com/alana-jophy/HealthWatch_Linux/main/docker/docker-compose.hub.yml

# Download sample env file and configure
curl -O https://raw.githubusercontent.com/alana-jophy/HealthWatch_Linux/main/docker/env.fullstack.sample
cp env.fullstack.sample .env
```

### Step 2: Configure `.env`
Edit `.env` and set:
```ini
DOCKERHUB_USER=your-dockerhub-username
DOMAIN_NAME=healthwatch.yourdomain.com
SECRET_KEY=generate-with-openssl-rand-hex-32
POSTGRES_PASSWORD=your-secure-db-password
ENABLE_HTTPS=false  # Set to true once DNS points to your server
SSL_EMAIL=admin@yourdomain.com
```

### Step 3: Launch Stack
```bash
docker compose -f docker-compose.hub.yml up -d
```

### Step 4: Verify Deployment
```bash
docker compose -f docker-compose.hub.yml ps
curl -f http://localhost/api/health
```
