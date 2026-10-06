#!/bin/bash
# ==============================================================================
# HealthWatch Production Microservices Deployment Script
# Supports:
#   1. HTTP Mode (Standard port 80, ideal for IP testing or Cloudflare/AWS ALB)
#   2. HTTPS Mode (Automated Let's Encrypt SSL/TLS with certbot)
# ==============================================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

ENV_FILE=".env.production"
COMPOSE_FILE="docker-compose.prod.yml"

# Colors for terminal output
RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

print_banner() {
    echo -e "${CYAN}====================================================================${NC}"
    echo -e "${CYAN}       HealthWatch Public Health Surveillance System                ${NC}"
    echo -e "${CYAN}       Production Microservices Deployment Orchestrator             ${NC}"
    echo -e "${CYAN}====================================================================${NC}"
}

check_prerequisites() {
    echo -e "\n${BLUE}[1/4] Checking host environment prerequisites...${NC}"
    if ! command -v docker &> /dev/null; then
        echo -e "${RED}Error: Docker is not installed. Please install Docker Engine first.${NC}"
        exit 1
    fi

    if ! docker compose version &> /dev/null; then
        echo -e "${RED}Error: Docker Compose (v2) is not installed.${NC}"
        exit 1
    fi

    if [ ! -f "$ENV_FILE" ]; then
        if [ -f ".env.example" ]; then
            echo -e "${YELLOW}Notice: '$ENV_FILE' not found. Creating from '.env.example'...${NC}"
            cp .env.example "$ENV_FILE"
            echo -e "${YELLOW}Please review and edit '$ENV_FILE' with your domain and secrets.${NC}"
        else
            echo -e "${RED}Error: Neither '$ENV_FILE' nor '.env.example' exists.${NC}"
            exit 1
        fi
    fi
    echo -e "${GREEN}✓ Docker and Compose verified.${NC}"
    echo -e "${GREEN}✓ Environment configuration loaded from '$ENV_FILE'.${NC}"
}

load_env() {
    export $(grep -v '^#' "$ENV_FILE" | xargs)
    DOMAIN_NAME="${DOMAIN_NAME:-localhost}"
    ENABLE_HTTPS="${ENABLE_HTTPS:-false}"
    SSL_EMAIL="${SSL_EMAIL:-admin@example.com}"
    APP_VERSION="${CUSTOM_VERSION:-${APP_VERSION:-1.0.0}}"
    export APP_VERSION
}

build_apk() {
    if [ -f "mobile/build_apk_linux.sh" ] && command -v java &>/dev/null; then
        echo -e "\n${BLUE}[APK] Compiling HealthWatch Android APK for domain '${DOMAIN_NAME}'...${NC}"
        SERVER_DOMAIN="${DOMAIN_NAME}" ENABLE_HTTPS="${ENABLE_HTTPS}" bash mobile/build_apk_linux.sh || echo -e "${YELLOW}Notice: APK compilation skipped or failed; existing APK will be used.${NC}"
    fi
}

build_images() {
    build_apk
    echo -e "\n${BLUE}[2/4] Building production microservices Docker images (Tag: ${APP_VERSION})...${NC}"
    APP_VERSION="${APP_VERSION}" docker compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" build
    
    # Tag each built image with both the specific version and 'latest'
    docker tag "healthwatch-gateway:${APP_VERSION}" "healthwatch-gateway:latest" 2>/dev/null || true
    docker tag "healthwatch-frontend:${APP_VERSION}" "healthwatch-frontend:latest" 2>/dev/null || true
    docker tag "healthwatch-backend:${APP_VERSION}" "healthwatch-backend:latest" 2>/dev/null || true

    echo -e "${GREEN}✓ Production Docker images built and tagged successfully:${NC}"
    echo -e "   - healthwatch-gateway:${APP_VERSION} (and latest)"
    echo -e "   - healthwatch-frontend:${APP_VERSION} (and latest)"
    echo -e "   - healthwatch-backend:${APP_VERSION} (and latest)"
}

start_http() {
    echo -e "\n${BLUE}[3/4] Launching HealthWatch in HTTP Mode (Port 80)...${NC}"
    sed -i 's/^ENABLE_HTTPS=.*/ENABLE_HTTPS=false/' "$ENV_FILE"
    APP_VERSION="${APP_VERSION}" docker compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" up -d --remove-orphans

    echo -e "\n${BLUE}[4/4] Verifying microservice health status...${NC}"
    sleep 5
    docker compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" ps

    echo -e "\n${GREEN}====================================================================${NC}"
    echo -e "${GREEN}✓ HealthWatch Microservices successfully running in HTTP mode!${NC}"
    echo -e "  - Web Application:       http://${DOMAIN_NAME}"
    echo -e "  - REST API & Health:     http://${DOMAIN_NAME}/api/health"
    echo -e "  - Interactive API Docs:  http://${DOMAIN_NAME}/docs"
    echo -e "  - Android APK Download:  http://${DOMAIN_NAME}/download/healthwatch.apk"
    echo -e "${GREEN}====================================================================${NC}"
}

start_https() {
    echo -e "\n${BLUE}[3/4] Initializing HTTPS deployment with automated SSL/TLS...${NC}"

    if [ "$DOMAIN_NAME" = "localhost" ] || [ "$DOMAIN_NAME" = "127.0.0.1" ] || [[ "$DOMAIN_NAME" =~ ^[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
        echo -e "${RED}Error: Cannot obtain Let's Encrypt certificate for localhost or raw IP address ($DOMAIN_NAME).${NC}"
        echo -e "${YELLOW}Let's Encrypt requires a valid publicly resolvable Fully Qualified Domain Name (FQDN).${NC}"
        echo -e "${YELLOW}Please set DOMAIN_NAME=yourdomain.com in '$ENV_FILE' and ensure DNS points to this server.${NC}"
        exit 1
    fi

    # Ensure ENABLE_HTTPS is set to true in environment configuration
    sed -i 's/^ENABLE_HTTPS=.*/ENABLE_HTTPS=true/' "$ENV_FILE"

    # Check if a valid certificate already exists in the docker volume or gateway
    HAS_EXISTING_CERT=false
    if docker run --rm -v healthwatch_linux_certbot_conf:/etc/letsencrypt alpine test -f "/etc/letsencrypt/live/${DOMAIN_NAME}/fullchain.pem" 2>/dev/null; then
        HAS_EXISTING_CERT=true
    fi

    if [ "$HAS_EXISTING_CERT" = "true" ]; then
        echo -e "${GREEN}✓ Existing SSL/TLS certificate detected for '${DOMAIN_NAME}'. Reusing existing certificate.${NC}"
    else
        # Step A: Start Gateway in HTTP mode so Nginx can respond to the ACME challenge
        echo -e "${CYAN}Step A: Starting Gateway in HTTP mode for ACME challenge...${NC}"
        docker compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" up -d gateway

        # Step B: Request Let's Encrypt Certificate
        echo -e "${CYAN}Step B: Requesting Let's Encrypt SSL certificate for '${DOMAIN_NAME}'...${NC}"
        docker compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" run --rm --entrypoint "\
            certbot certonly --webroot -w /var/www/certbot \
            --email ${SSL_EMAIL} \
            -d ${DOMAIN_NAME} \
            --rsa-key-size 4096 \
            --agree-tos \
            --keep-until-expiring \
            --non-interactive" certbot
    fi

    # Step C: Enable HTTPS and start/reload microservices
    echo -e "${CYAN}Step C: Launching microservices in HTTPS mode...${NC}"
    APP_VERSION="${APP_VERSION}" docker compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" up -d --remove-orphans

    echo -e "\n${BLUE}[4/4] Verifying microservice health status...${NC}"
    sleep 5
    docker compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" ps

    echo -e "\n${GREEN}====================================================================${NC}"
    echo -e "${GREEN}✓ HealthWatch Microservices successfully running with HTTPS/SSL!${NC}"
    echo -e "  - Secure Web Portal:     https://${DOMAIN_NAME}"
    echo -e "  - Secure REST API:       https://${DOMAIN_NAME}/api/health"
    echo -e "  - Secure API Docs:       https://${DOMAIN_NAME}/docs"
    echo -e "  - Android APK Download:  https://${DOMAIN_NAME}/download/healthwatch.apk"
    echo -e "  - Automated Renewal:     Certbot daemon checks every 12 hours"
    echo -e "${GREEN}====================================================================${NC}"
}

stop_services() {
    echo -e "\n${YELLOW}Stopping HealthWatch production microservices...${NC}"
    docker compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" down
    echo -e "${GREEN}✓ All microservices stopped cleanly.${NC}"
}

show_status() {
    echo -e "\n${BLUE}HealthWatch Production Microservices Status:${NC}"
    docker compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" ps
}

show_logs() {
    docker compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" logs -f --tail=100
}

# ------------------------------------------------------------------------------
# Entrypoint Dispatcher
# ------------------------------------------------------------------------------
CUSTOM_VERSION=""

# Support flags: -v <tag>, -t <tag>, --version <tag>, or passing tag as second argument
while [[ $# -gt 0 ]]; do
    case "$1" in
        -v|--version|-t|--tag)
            CUSTOM_VERSION="$2"
            shift 2
            ;;
        *)
            if [[ -z "${ACTION:-}" ]]; then
                ACTION="$1"
            elif [[ -z "$CUSTOM_VERSION" ]]; then
                CUSTOM_VERSION="$1"
            fi
            shift
            ;;
    esac
done

print_banner
check_prerequisites
load_env

ACTION="${ACTION:-}"

case "$ACTION" in
    http)
        build_images
        start_http
        ;;
    https|ssl)
        build_images
        start_https
        ;;
    apk)
        build_apk
        ;;
    build)
        build_images
        ;;
    stop|down)
        stop_services
        ;;
    status)
        show_status
        ;;
    logs)
        show_logs
        ;;
    import-wards|seed-wards)
        echo -e "\n${BLUE}Importing official Kerala wards from CSV into database...${NC}"
        docker compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" exec backend python -m app.scripts.import_official_kerala_wards
        ;;
    verify-wards)
        echo -e "\n${BLUE}Verifying Kerala administrative spatial hierarchy in database...${NC}"
        docker compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" exec backend python -m app.scripts.verify_kerala_wards
        ;;
    *)
        echo -e "\nUsage: $0 {http|https|build|apk|stop|status|logs|import-wards|verify-wards} [version_tag]"
        echo -e "  ${CYAN}./deploy.sh build [tag]${NC}        - Build production Docker images with specific tag"
        echo -e "  ${CYAN}./deploy.sh http [tag]${NC}         - Build and launch in HTTP mode on port 80"
        echo -e "  ${CYAN}./deploy.sh https [tag]${NC}        - Build and launch in HTTPS mode with Let's Encrypt SSL on port 443"
        echo -e "  ${CYAN}./deploy.sh apk${NC}                - Compile Android APK with domain injected from .env configuration"
        echo -e "  ${CYAN}./deploy.sh import-wards${NC}       - Import official_kerala_wards.csv into PostgreSQL/PostGIS database"
        echo -e "  ${CYAN}./deploy.sh verify-wards${NC}       - Run complete integrity check on all districts, local bodies, and wards"
        echo -e "  ${CYAN}./deploy.sh stop${NC}               - Stop all production containers"
        echo -e "  ${CYAN}./deploy.sh status${NC}             - Show running containers and health checks"
        echo -e "  ${CYAN}./deploy.sh logs${NC}               - Tail live logs from all microservices"
        echo -e ""
        echo -e "Current Configuration ($ENV_FILE):"
        echo -e "  Domain:         ${YELLOW}${DOMAIN_NAME}${NC}"
        echo -e "  Version Tag:    ${YELLOW}${APP_VERSION}${NC}"
        echo -e "  HTTPS Enabled:  ${YELLOW}${ENABLE_HTTPS}${NC}"
        echo -e "  SSL Email:      ${YELLOW}${SSL_EMAIL}${NC}"
        echo -e ""
        read -p "Select deployment mode (1 for HTTP, 2 for HTTPS, 3 to Exit): " choice
        case "$choice" in
            1)
                build_images
                start_http
                ;;
            2)
                build_images
                start_https
                ;;
            *)
                echo "Exiting."
                exit 0
                ;;
        esac
        ;;
esac
