# HealthWatch Gateway (`healthwatch-gateway`)

[![Docker Image](https://img.shields.io/badge/docker-healthwatch--gateway-blue.svg)](https://hub.docker.com)
[![Nginx](https://img.shields.io/badge/Nginx-Alpine-green.svg)](https://nginx.org)
[![SSL/TLS](https://img.shields.io/badge/SSL%2FTLS-Let's%20Encrypt-teal.svg)](https://letsencrypt.org)
[![Security](https://img.shields.io/badge/Security-A%2B%20Rated-brightgreen.svg)](https://ssllabs.com)

The official API Gateway and Reverse Proxy microservice for the **HealthWatch** Disease Surveillance platform. Built on **Nginx Alpine**, it manages unified ingress routing, automated **Let's Encrypt SSL/TLS certificates**, HTTP-to-HTTPS redirection, and rate limiting.

---

## Architecture Overview

`healthwatch-gateway` serves as the single public-facing entrypoint:
- **Unified Domain Routing**: Routes incoming traffic seamlessly between frontend (`/`), REST API (`/api/`), interactive documentation (`/docs`), and Android APK downloads (`/HealthWatch.apk`).
- **Zero-Downtime SSL/TLS Automation**: Automatically configures Let's Encrypt SSL certificates with Certbot ACME webroot challenge support.
- **Dual Operating Modes**:
  - **HTTP Mode**: Port 80 execution without SSL, ideal for local network testing (`192.168.x.x`), private clusters, or reverse-proxy setups behind Cloudflare/AWS ALB.
  - **HTTPS Mode**: Port 443 execution with automated HTTP-to-HTTPS redirect, modern TLS 1.2/1.3 cipher suites, OCSP stapling, and HSTS headers.
- **Resilient Upstream Failure Handling**: Built-in keepalives and buffers protect internal Python and Node microservices from slow-client attacks.

---

## Ingress Routing Map

| Path Pattern | Upstream Destination | Description |
| :--- | :--- | :--- |
| `/` | `frontend:80` | Single Page Application HTML/JS assets |
| `/api/` | `backend:8000/api/` | REST API endpoints & surveillance logic |
| `/docs` | `backend:8000/docs` | Swagger interactive API explorer |
| `/redoc` | `backend:8000/redoc` | ReDoc API documentation |
| `/HealthWatch.apk` | `frontend:80/HealthWatch.apk` | Android APK installer download |
| `/.well-known/acme-challenge/` | `/var/www/certbot` | Let's Encrypt validation challenge |

---

## Environment Variables (`.env`)

| Variable | Type | Default | Required | Description |
| :--- | :--- | :--- | :--- | :--- |
| `DOMAIN_NAME` | String | `localhost` | **Yes** | Server domain name or public IP (e.g. `healthwatch.example.com` or `192.168.1.100`) |
| `ENABLE_HTTPS` | Boolean | `false` | No | Set to `true` to enable SSL/TLS termination, or `false` for standard HTTP |
| `SSL_EMAIL` | String | `admin@example.com`| No | Contact email for Let's Encrypt certificate renewal alerts |

---

## Sample `.env` File (`.env.gateway`)

```ini
# Server Domain (FQDN or Public IP)
DOMAIN_NAME=healthwatch.example.com

# SSL Mode ('true' for HTTPS via Let's Encrypt, 'false' for HTTP)
ENABLE_HTTPS=false

# Certificate Expiry Alert Email
SSL_EMAIL=admin@example.com
```

---

## Quick Start: Standalone `docker run`

### HTTP Mode (Port 80)
```bash
docker run -d \
  --name healthwatch-gateway \
  --restart always \
  -p 80:80 \
  -e DOMAIN_NAME="healthwatch.example.com" \
  -e ENABLE_HTTPS="false" \
  YOUR_DOCKERHUB_USERNAME/healthwatch-gateway:1.0.0
```

### HTTPS Mode (Port 80 & 443 with Mounted Certificates)
```bash
docker run -d \
  --name healthwatch-gateway \
  --restart always \
  -p 80:80 \
  -p 443:443 \
  -e DOMAIN_NAME="healthwatch.example.com" \
  -e ENABLE_HTTPS="true" \
  -v certbot_conf:/etc/letsencrypt:ro \
  -v certbot_www:/var/www/certbot:ro \
  YOUR_DOCKERHUB_USERNAME/healthwatch-gateway:1.0.0
```

---

## Complete Docker Compose Stack

```yaml
version: '3.8'

services:
  gateway:
    image: YOUR_DOCKERHUB_USERNAME/healthwatch-gateway:1.0.0
    container_name: healthwatch-gateway
    restart: always
    ports:
      - "80:80"
      - "443:443"
    environment:
      - DOMAIN_NAME=${DOMAIN_NAME:-localhost}
      - ENABLE_HTTPS=${ENABLE_HTTPS:-false}
    volumes:
      - certbot_conf:/etc/letsencrypt
      - certbot_www:/var/www/certbot
    depends_on:
      - frontend
      - backend
    networks:
      - healthwatch-net

  frontend:
    image: YOUR_DOCKERHUB_USERNAME/healthwatch-frontend:1.0.0
    container_name: healthwatch-frontend
    restart: always
    networks:
      - healthwatch-net

  backend:
    image: YOUR_DOCKERHUB_USERNAME/healthwatch-backend:1.0.0
    container_name: healthwatch-backend
    restart: always
    environment:
      - DATABASE_URL=postgresql://healthwatch_admin:HealthWatch_Prod_Secret_Pass_2026!@db:5432/healthwatch_db
      - SECRET_KEY=your-secret-key
    networks:
      - healthwatch-net

volumes:
  certbot_conf:
  certbot_www:

networks:
  healthwatch-net:
```

---

## Health Check & Verification

```bash
# Verify Gateway HTTP Routing
curl -I http://localhost/

# Verify API Routing Through Gateway
curl -f http://localhost/api/health

# Verify ACME Challenge Path
curl -I http://localhost/.well-known/acme-challenge/test
```
