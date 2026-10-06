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

# 5. Security & Concurrency
SECRET_KEY=e2425e1a9c2592bc67cd4ca08dd470d84462af8ba9bcda3ce77c5b73855cd4e3
WORKERS=4
BACKEND_CORS_ORIGINS=["http://healthwatch.yourdomain.com","https://healthwatch.yourdomain.com"]
```

---

## 5. Launching the Microservices

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

## 7. Packaging & Pushing Docker Images to a Container Registry (Optional)

If you prefer to push your images to **Docker Hub** or **GitHub Container Registry (GHCR)** rather than building on the server:

```bash
# 1. Build the production images locally
./deploy.sh build

# 2. Tag with your Docker Hub username or registry
docker tag healthwatch-gateway:1.0.0 yourusername/healthwatch-gateway:1.0.0
docker tag healthwatch-frontend:1.0.0 yourusername/healthwatch-frontend:1.0.0
docker tag healthwatch-backend:1.0.0 yourusername/healthwatch-backend:1.0.0

# 3. Log in and push
docker login
docker push yourusername/healthwatch-gateway:1.0.0
docker push yourusername/healthwatch-frontend:1.0.0
docker push yourusername/healthwatch-backend:1.0.0
```

On your production server, simply reference `image: yourusername/healthwatch-...:1.0.0` in `docker-compose.prod.yml` and run:
```bash
docker compose -f docker-compose.prod.yml --env-file .env.production up -d
```
