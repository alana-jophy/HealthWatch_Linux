#!/usr/bin/env bash
set -e

echo "=== 1. Current Working Directory in WSL ==="
pwd

echo "=== 2. Validating docker-compose.yml ==="
docker compose config

echo "=== 3. Starting Services with docker compose up -d ==="
docker compose up -d

echo "=== 4. Checking Service Status ==="
docker compose ps

echo "=== 5. Verifying PostgreSQL and PostGIS ==="
# Wait a few seconds for DB container to initialize if needed
sleep 5
docker compose exec -T db psql -U healthwatch_user -d healthwatch_db -c "SELECT postgis_full_version();"
