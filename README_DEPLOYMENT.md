# HealthWatch - Production Microservices Deployment Guide

This guide describes how to deploy the **HealthWatch Epidemiological Surveillance System** into any production Linux server as containerized microservices with custom domain configuration and support for both **HTTP** (no SSL) and **HTTPS** (automated SSL/TLS).

---

## 1. Microservices Architecture Overview

```
                                      [ Internet / Client Traffic ]
                                                    │
                                                    ▼
                     ┌────────────────────────────────────────────────────────┐
                     │          healthwatch-gateway (Nginx Alpine)            │
                     │             Ports: 80 (HTTP) & 443 (HTTPS)             │
                     │  - Domain Routing & Host Header Verification           │
                     │  - Automated Let's Encrypt SSL/TLS Termination         │
                     │  - Rate Limiting & Strict Security Headers             │
                     └───────────────┬────────────────────────┬───────────────┘
                                     │                        │
                      /              │                        │  /api, /docs, /download
                      (SPA Requests) │                        │  (REST API & Telemetry)
                                     ▼                        ▼
      ┌──────────────────────────────────────────┐    ┌──────────────────────────────────────────┐
      │          healthwatch-frontend            │    │           healthwatch-backend            │
      │        (React 18 + Nginx Alpine)         │    │      (FastAPI + Gunicorn 4 Workers)      │
      │  - Static Asset Caching (Immutable)      │    │  - Real-time GPS Telemetry Ingestion     │
      │  - Client-side Routing Fallback          │    │  - Spatial-Temporal Contact Tracing      │
      │  - Native dark-mode responsive dashboard │    │  - AI Outbreak Prediction & PDF Reports  │
      └──────────────────────────────────────────┘    └────────────────────┬─────────────────────┘
                                                                           │
                                                                           │  PostgreSQL Protocol
                                                                           │  (Port 5432 Internal)
                                                                           ▼
                                                      ┌──────────────────────────────────────────┐
                                                      │              healthwatch-db              │
                                                      │        (PostgreSQL 16 + PostGIS 3.4)     │
                                                      │  - Persistent Volume: 'postgres_data'    │
                                                      │  - Full Kerala SEC Ward Delimitation     │
                                                      │  - Spatial Indexing (GiST / R-Tree)      │
                                                      └──────────────────────────────────────────┘
```

---

## 2. Server Prerequisites

On your target Linux production server (Ubuntu 22.04 / 24.04 LTS recommended):

1. **Docker & Docker Compose**:
   ```bash
   sudo apt-get update
   sudo apt-get install -y ca-certificates curl gnupg
   sudo install -m 0755 -d /etc/apt/keyrings
   curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
   sudo chmod a+r /etc/apt/keyrings/docker.gpg

   echo \
     "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
     $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | \
     sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

   sudo apt-get update
   sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
   ```

2. **Firewall (Open Ports 80 and 443)**:
   ```bash
   sudo ufw allow 80/tcp
   sudo ufw allow 443/tcp
   sudo ufw allow 22/tcp
   sudo ufw enable
   ```

3. **DNS Configuration (For Domain & HTTPS)**:
   - Create an **A Record** in your DNS registrar pointing your domain (e.g., `healthwatch.yourdomain.com`) to your server's public IP address.

---

## 3. Deployment Files Structure

The production deployment package consists of the following modular files:

| File | Purpose |
| :--- | :--- |
| **`docker-compose.prod.yml`** | Production Compose file defining all 4 microservices + Certbot with health checks and restart policies. |
| **`.env.production`** | Environment configuration defining your domain name, credentials, and secrets. |
| **`deploy.sh`** | Automated executable script to build, deploy, and manage the microservices. |
| **`gateway/`** | Reverse proxy microservice containing dynamic Nginx HTTP and HTTPS templates. |
| **`backend/Dockerfile.prod`** | Hardened multi-worker Gunicorn + Uvicorn container image. |
| **`frontend/Dockerfile.prod`** | Multi-stage builder creating a lightweight Nginx image serving optimized static assets. |

---

## 4. Configuration: Customizing `.env.production`

Before launching, edit `.env.production` with your server details:

```bash
nano .env.production
```

Key configuration parameters:

```env
# 1. Server Domain or Public IP
DOMAIN_NAME=healthwatch.yourdomain.com

# 2. HTTPS Toggle (set to 'true' for automated SSL, or 'false' for HTTP)
ENABLE_HTTPS=false

# 3. Notification email for Let's Encrypt SSL certificates
SSL_EMAIL=admin@yourdomain.com

# 4. PostgreSQL Credentials (Use strong passwords in production)
POSTGRES_USER=healthwatch_admin
POSTGRES_PASSWORD=YourStrongDatabasePassword123!
POSTGRES_DB=healthwatch_db
DATABASE_URL=postgresql://healthwatch_admin:YourStrongDatabasePassword123!@db:5432/healthwatch_db

# 6. Default Admin Account
ADMIN_EMAIL=admin@healthwatch.org
ADMIN_PASSWORD=YourSecureAdminPassword123!
ADMIN_NAME=System Administrator
```

---

## 5. Image Versioning & Build Tagging

You can specify the Docker image version/tag in three different ways:

1. **In `.env.production` (Persistent)**:
   ```env
   APP_VERSION=1.2.0
   ```
2. **Directly in the CLI (On the fly)**:
   ```bash
   # Build with specific tag:
   ./deploy.sh build 1.2.0
   # Or launch directly with specific tag:
   ./deploy.sh http 1.2.0
   ./deploy.sh https 1.2.0
   # Or using the -t / -v flag:
   ./deploy.sh build -t 1.2.0
   ```
3. **Via CLI Environment Variable**:
   ```bash
   APP_VERSION=1.2.0 ./deploy.sh build
   ```

*Every build automatically tags the image with both your custom version tag (e.g. `healthwatch-backend:1.2.0`) and `latest` (`healthwatch-backend:latest`).*

---

## 6. Launching the Microservices

The included [`deploy.sh`](file:///home/alana/Desktop/healthwatch/deploy.sh) script handles compilation, configuration, and startup.

### Option A: Deploy in HTTP Mode (No SSL / Raw IP / Behind Cloudflare)
Ideal if you are testing via server IP address, running on an internal network, or terminating SSL at an external cloud load balancer (AWS ALB / Cloudflare):

```bash
./deploy.sh http
```
*Accessible at:* `http://your-server-domain-or-ip`

### Option B: Deploy in HTTPS Mode (Automated Let's Encrypt SSL/TLS)
Ideal for production domains with DNS pointed to the server:

```bash
./deploy.sh https
```
The script will:
1. Start the HTTP gateway to verify domain ownership via Let's Encrypt ACME challenge.
2. Automatically generate a 4096-bit RSA SSL/TLS certificate.
3. Switch the Gateway to HTTPS mode with TLS 1.2/1.3 and HSTS security headers.
4. Launch the automated Certbot daemon that continuously checks and renews certificates every 12 hours.

*Accessible at:* `https://healthwatch.yourdomain.com`

---

## 6. Management & Operational Commands

```bash
# View real-time status of all microservices
./deploy.sh status

# Tail live application logs across all containers
./deploy.sh logs

# Stop all microservices
./deploy.sh stop

# Re-build production images after code updates
./deploy.sh build
```

---

---

## 7. Automated Publishing & Docker Hub Synchronization

HealthWatch provides a turnkey automation script [`docker/push_to_dockerhub.sh`](file:///home/alana/Desktop/healthwatch/docker/push_to_dockerhub.sh) that:
1. Tags all 3 microservices with your target version (and `:latest`).
2. Pushes the Docker images to your Docker Hub repository.
3. Automatically uploads the markdown documentation ([`docker/backend/README.md`](file:///home/alana/Desktop/healthwatch/docker/backend/README.md), [`docker/frontend/README.md`](file:///home/alana/Desktop/healthwatch/docker/frontend/README.md), and [`docker/gateway/README.md`](file:///home/alana/Desktop/healthwatch/docker/gateway/README.md)) to each Docker Hub repository overview page via Docker Hub's REST API.

### Prerequisites

* Build your production images first:
  ```bash
  ./deploy.sh build
  # Or with a specific tag:
  ./deploy.sh build 1.0.0
  ```
* A **Docker Hub Personal Access Token (PAT)** with **Read & Write** permissions (generated at [hub.docker.com/settings/security](https://hub.docker.com/settings/security)).

---

### Execution Modes

#### Option A: Automatic Execution (Uses Saved Credentials from `~/.docker/config.json`)
If you have already logged in via `docker login`, the script automatically detects your credentials without any prompts:
```bash
./docker/push_to_dockerhub.sh
```

#### Option B: Automated / CI/CD One-Liner (Explicit Credentials)
```bash
./docker/push_to_dockerhub.sh -u your-dockerhub-username -t 1.0.0 --token "dckr_pat_xxxx"
```

#### Option C: Using Environment Variables
```bash
export DOCKERHUB_USER="your-dockerhub-username"
export DOCKERHUB_TOKEN="dckr_pat_xxxx"
./docker/push_to_dockerhub.sh
```

#### Option D: Dry-Run Mode (Preview Actions Without Pushing)
```bash
./docker/push_to_dockerhub.sh --dry-run
```

---

### Script CLI Options Reference

| Option | Flag | Description | Default |
| :--- | :--- | :--- | :--- |
| **Username** | `-u`, `--username` | Docker Hub username or organization namespace | Auto-detected from `~/.docker/config.json` or `$DOCKERHUB_USER` |
| **Version Tag** | `-t`, `--tag` | Image version tag to publish | `APP_VERSION` from `.env.production` or `1.0.0` |
| **Access Token**| `--token` | Docker Hub PAT (required for API README sync) | Auto-detected from `~/.docker/config.json` or `$DOCKERHUB_TOKEN` |
| **Docker Config**| `--docker-config` | Custom Docker config file path | `~/.docker/config.json` |
| **Skip README** | `--skip-readme` | Push Docker images only, skip API docs upload | `false` |
| **Dry Run** | `--dry-run` | Print commands without executing | `false` |
| **Help** | `-h`, `--help` | Display script usage and examples | |

---

### Deploying Anywhere Using Published Docker Hub Images

Once published, you can deploy the complete stack onto any remote server using [`docker/docker-compose.hub.yml`](file:///home/alana/Desktop/healthwatch/docker/docker-compose.hub.yml) without needing the source code:

```bash
# 1. Download production hub compose and environment template
curl -O https://raw.githubusercontent.com/alana-jophy/HealthWatch_Linux/main/docker/docker-compose.hub.yml
curl -O https://raw.githubusercontent.com/alana-jophy/HealthWatch_Linux/main/docker/env.fullstack.sample
cp env.fullstack.sample .env

# 2. Configure .env with your Docker Hub user and domain
# In .env:
# DOCKERHUB_USER=your-dockerhub-username
# DOMAIN_NAME=healthwatch.example.com

# 3. Launch stack
docker compose -f docker-compose.hub.yml up -d
```

