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

The automation script [`push_to_dockerhub.sh`](file:///home/alana/Desktop/healthwatch/docker/push_to_dockerhub.sh) handles:
1. **Image Validation**: Checks that local microservices are built and ready.
2. **Tagging**: Tags each local image with both your chosen version tag (`:${VERSION_TAG}`) and `:latest`.
3. **Registry Push**: Pushes all images to your Docker Hub repository via `docker push`.
4. **Automated Documentation Sync**: Authenticates with Docker Hub's v2 REST API to automatically update the **Repository Overview (README)** for all 3 images with their respective markdown documentation ([`docker/backend/README.md`](file:///home/alana/Desktop/healthwatch/docker/backend/README.md), [`docker/frontend/README.md`](file:///home/alana/Desktop/healthwatch/docker/frontend/README.md), and [`docker/gateway/README.md`](file:///home/alana/Desktop/healthwatch/docker/gateway/README.md)).

### Prerequisites

1. Build images locally first:
   ```bash
   ./deploy.sh build
   # Or with a specific version:
   ./deploy.sh build 1.0.0
   ```
2. Generate a **Docker Hub Personal Access Token (PAT)**:
   - Go to: [hub.docker.com/settings/security](https://hub.docker.com/settings/security)
   - Click **New Access Token**
   - Access Permissions: **Read & Write** (required to update repository descriptions)

---

### Command-Line Options Reference

| Option | Shorthand | Description | Default |
| :--- | :--- | :--- | :--- |
| `--username <name>` | `-u` | Docker Hub username or org namespace | Auto-detected from `~/.docker/config.json` or `$DOCKERHUB_USER` |
| `--tag <version>` | `-t` | Version tag to push (also tags `:latest`) | `APP_VERSION` from `.env.production` or `1.0.0` |
| `--token <token>` | | Personal Access Token or password | Auto-detected from `~/.docker/config.json` or `$DOCKERHUB_TOKEN` |
| `--docker-config <path>` | | Custom Docker config file path | `~/.docker/config.json` |
| `--skip-readme` | | Push images only; skip updating READMEs | `false` |
| `--dry-run` | | Print commands without executing | `false` |
| `--help` | `-h` | Display usage manual and examples | |

---

### Execution Examples

#### 1. Automatic Execution (Uses Saved Credentials from `~/.docker/config.json`)
If you have already logged in via `docker login`, the script will automatically detect your username and token:
```bash
./docker/push_to_dockerhub.sh
```
*Zero-prompt: automatically pushes images and syncs all three README overviews.*

#### 2. Fully Automated (CI/CD / Custom Credentials)
```bash
./docker/push_to_dockerhub.sh -u mydockerhubuser -t 1.0.0 --token "dckr_pat_xxxx"
```

#### 3. Using Environment Variables
```bash
export DOCKERHUB_USER="mydockerhubuser"
export DOCKERHUB_TOKEN="dckr_pat_xxxx"
./docker/push_to_dockerhub.sh
```

#### 4. Preview Execution (Dry-Run)
```bash
./docker/push_to_dockerhub.sh --dry-run
```

---

### How the Automated README Sync Works

Docker images themselves do not store repository overview pages. The script interacts with Docker Hub's API:
1. **Authentication**: Calls `POST https://hub.docker.com/v2/users/login/` with your credentials to obtain a secure session JWT.
2. **Dynamic Customization**: Reads the service's `README.md` and dynamically substitutes any `YOUR_DOCKERHUB_USERNAME` placeholders with your actual username so all copy-pasteable commands in Docker Hub refer directly to your repository!
3. **Overview Update**: Sends `PATCH https://hub.docker.com/v2/repositories/<username>/<repo>/` with the payload `{"full_description": "<markdown_content>"}`.

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
