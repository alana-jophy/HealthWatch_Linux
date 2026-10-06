# HealthWatch Frontend (`healthwatch-frontend`)

[![Docker Image](https://img.shields.io/badge/docker-healthwatch--frontend-blue.svg)](https://hub.docker.com)
[![React](https://img.shields.io/badge/React-18.3-cyan.svg)](https://react.dev)
[![TypeScript](https://img.shields.io/badge/TypeScript-5.2-blue.svg)](https://www.typescriptlang.org)
[![Nginx](https://img.shields.io/badge/Nginx-Alpine-green.svg)](https://nginx.org)
[![Tailwind CSS](https://img.shields.io/badge/TailwindCSS-3.4-teal.svg)](https://tailwindcss.com)

The official production frontend microservice for the **HealthWatch** Disease Surveillance platform. Serves the React 18 Single Page Application (SPA), geospatial Leaflet dashboards, and pre-packaged Android APK downloads via an optimized, lightweight **Nginx Alpine** web server.

---

## Architecture Overview

`healthwatch-frontend` provides:
- **Interactive Surveillance Dashboards**: Disease outbreak heatmaps, Kerala geographic hierarchy filters (District → Local Body → Ward), and cluster density visualizations.
- **Movement Roadmap & Telemetry Visualizer**: Spatial timeline mapping discrete 15-minute GPS observations, stationary drift classification, and sequential movement paths.
- **Patient & Clinician Portals**: Patient registration, consent agreements, monitoring cadence, and disease case progress.
- **Android APK Distribution Server**: Serves compiled `HealthWatch.apk` artifacts directly at `/HealthWatch.apk` with proper MIME headers for instant mobile downloads.
- **Production Nginx Routing**: Hardened SPA routing (`try_files $uri $uri/ /index.html`), gzip compression, security headers (`X-Frame-Options`, `X-Content-Type-Options`), and caching policies.

---

## Environment Variables (`.env`)

| Variable | Type | Default | Required | Description |
| :--- | :--- | :--- | :--- | :--- |
| `VITE_API_BASE_URL` | String | *Empty (Relative)* | No | Custom backend API origin URL. If empty, relative reverse proxy routing via Gateway is used (recommended) |
| `VITE_APP_TITLE` | String | `HealthWatch Surveillance System` | No | HTML document title and portal branding name |
| `PORT` | Integer | `80` | No | Internal Nginx container listen port |

---

## Sample `.env` File (`.env.frontend`)

```ini
# Application Title Branding
VITE_APP_TITLE=HealthWatch Surveillance System

# Production API Routing (Leave blank when using Gateway reverse proxy)
VITE_API_BASE_URL=

# Port
PORT=80
```

---

## Quick Start: Standalone `docker run`

```bash
docker run -d \
  --name healthwatch-frontend \
  --restart always \
  -p 80:80 \
  YOUR_DOCKERHUB_USERNAME/healthwatch-frontend:1.0.0
```

---

## Docker Compose Configuration

### Standalone Frontend with Backend Linking

```yaml
version: '3.8'

services:
  frontend:
    image: YOUR_DOCKERHUB_USERNAME/healthwatch-frontend:1.0.0
    container_name: healthwatch-frontend
    restart: always
    ports:
      - "80:80"
    healthcheck:
      test: ["CMD-SHELL", "wget -qO- http://127.0.0.1:80/healthz || exit 1"]
      interval: 15s
      timeout: 5s
      retries: 3
      start_period: 10s
    networks:
      - healthwatch-net

networks:
  healthwatch-net:
```

---

## Health Check & Verification

```bash
# Nginx Health Check Endpoint
wget -qO- http://127.0.0.1:80/healthz
# Response: OK

# Verify Root HTML
curl -I http://localhost:80/

# Verify Android APK Download Availability
curl -I http://localhost:80/HealthWatch.apk
```

---

## Container Specifications

- **Base Image**: `nginx:alpine` (multi-stage build from `node:20-alpine`)
- **Image Footprint**: ~35MB uncompressed Nginx runtime
- **Static Assets Directory**: `/usr/share/nginx/html`
- **Security Headers Included**:
  - `X-Frame-Options: SAMEORIGIN`
  - `X-Content-Type-Options: nosniff`
  - `X-XSS-Protection: 1; mode=block`
- **Resource Recommendations**:
  - Memory: `64MB` minimum, `128MB` recommended
  - CPU: `0.1` cores minimum, `0.25` cores recommended
