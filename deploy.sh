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
    # If a custom version was passed via CLI flags or arguments, synchronize into env file
    if [ -n "$CUSTOM_VERSION" ]; then
        APP_VERSION="$CUSTOM_VERSION"
        if [ -f "$ENV_FILE" ]; then
            if grep -q '^APP_VERSION=' "$ENV_FILE"; then
                sed -i "s/^APP_VERSION=.*/APP_VERSION=${APP_VERSION}/" "$ENV_FILE"
            else
                echo "APP_VERSION=${APP_VERSION}" >> "$ENV_FILE"
            fi
        fi
    fi

    export $(grep -v '^#' "$ENV_FILE" | xargs)
    DOMAIN_NAME="${DOMAIN_NAME:-localhost}"
    ENABLE_HTTPS="${ENABLE_HTTPS:-false}"
    SSL_EMAIL="${SSL_EMAIL:-admin@example.com}"
    APP_VERSION="${CUSTOM_VERSION:-${APP_VERSION:-1.0.0}}"
    export APP_VERSION
}

check_apk_needs_rebuild() {
    local FORCE="${1:-false}"
    if [ "$FORCE" = "true" ]; then
        echo "true"
        return 0
    fi

    local TARGET_APK="HealthWatch-v${APP_VERSION}.apk"
    local LAST_VERSION=""
    if [ -f "mobile/.last_built_apk_version" ]; then
        LAST_VERSION=$(cat "mobile/.last_built_apk_version" 2>/dev/null | tr -d '\r\n ')
    fi

    # Condition 1: Last built version does not match active APP_VERSION in env file
    if [ "$LAST_VERSION" != "$APP_VERSION" ]; then
        echo "true"
        return 0
    fi

    # Condition 2: Target versioned APK file missing in backend or frontend distribution dirs
    if [ ! -f "backend/app/$TARGET_APK" ] || [ ! -f "frontend/public/$TARGET_APK" ]; then
        echo "true"
        return 0
    fi

    # Condition 3: Default HealthWatch.apk installer missing
    if [ ! -f "backend/app/HealthWatch.apk" ] || [ ! -f "frontend/public/HealthWatch.apk" ]; then
        echo "true"
        return 0
    fi

    echo "false"
    return 0
}

cleanup_old_apks() {
    echo -e "\n${BLUE}[APK CLEANUP] Scanning and purging obsolete APK versions from server...${NC}"
    local TARGET_APK="HealthWatch-v${APP_VERSION}.apk"
    local REMOVED_COUNT=0

    for DIR in "frontend/public" "backend/app"; do
        if [ -d "$DIR" ]; then
            while IFS= read -r old_apk; do
                if [ -n "$old_apk" ]; then
                    echo -e "${YELLOW}  -> Purged obsolete APK file: $old_apk${NC}"
                    rm -f "$old_apk"
                    REMOVED_COUNT=$((REMOVED_COUNT + 1))
                fi
            done < <(find "$DIR" -maxdepth 1 -name "HealthWatch-*.apk" ! -name "$TARGET_APK" -type f)
            find "$DIR" -maxdepth 1 -name "*.idsig" -type f -delete 2>/dev/null || true
        fi
    done

    # Ensure frontend and backend have identical copies of the active APK
    if [ -f "backend/app/$TARGET_APK" ]; then
        cp -f "backend/app/$TARGET_APK" "backend/app/HealthWatch.apk"
        mkdir -p "frontend/public"
        cp -f "backend/app/$TARGET_APK" "frontend/public/$TARGET_APK"
        cp -f "backend/app/$TARGET_APK" "frontend/public/HealthWatch.apk"
    elif [ -f "frontend/public/$TARGET_APK" ]; then
        cp -f "frontend/public/$TARGET_APK" "frontend/public/HealthWatch.apk"
        mkdir -p "backend/app"
        cp -f "frontend/public/$TARGET_APK" "backend/app/$TARGET_APK"
        cp -f "frontend/public/$TARGET_APK" "backend/app/HealthWatch.apk"
    fi

    # Hot-sync to running containers if active
    if docker ps --format '{{.Names}}' 2>/dev/null | grep -q "^healthwatch-backend$"; then
        if [ -f "backend/app/$TARGET_APK" ]; then
            docker cp "backend/app/$TARGET_APK" healthwatch-backend:/app/app/$TARGET_APK 2>/dev/null || true
            docker cp "backend/app/$TARGET_APK" healthwatch-backend:/app/app/HealthWatch.apk 2>/dev/null || true
        fi
    fi
    if docker ps --format '{{.Names}}' 2>/dev/null | grep -q "^healthwatch-frontend$"; then
        if [ -f "frontend/public/$TARGET_APK" ]; then
            docker cp "frontend/public/$TARGET_APK" healthwatch-frontend:/usr/share/nginx/html/$TARGET_APK 2>/dev/null || true
            docker cp "frontend/public/$TARGET_APK" healthwatch-frontend:/usr/share/nginx/html/HealthWatch.apk 2>/dev/null || true
        fi
    fi

    echo -e "${GREEN}✓ Obsolete APK versions pruned ($REMOVED_COUNT removed). Active release synchronized: v${APP_VERSION}.${NC}"
}

build_apk() {
    local FORCE_REBUILD="${1:-false}"
    local TARGET_APK="HealthWatch-v${APP_VERSION}.apk"
    local LAST_VERSION=""
    if [ -f "mobile/.last_built_apk_version" ]; then
        LAST_VERSION=$(cat "mobile/.last_built_apk_version" 2>/dev/null | tr -d '\r\n ')
    fi

    local NEEDS_REBUILD
    NEEDS_REBUILD=$(check_apk_needs_rebuild "$FORCE_REBUILD")

    if [ "$NEEDS_REBUILD" = "true" ]; then
        echo -e "\n${CYAN}====================================================================${NC}"
        if [ "$FORCE_REBUILD" = "true" ]; then
            echo -e "${CYAN}  [APK] Force rebuild requested for Android APK                     ${NC}"
        elif [ -n "$LAST_VERSION" ] && [ "$LAST_VERSION" != "$APP_VERSION" ]; then
            echo -e "${CYAN}  [APK] New version tag detected in env file: v${APP_VERSION} (previous: v${LAST_VERSION})${NC}"
        elif [ ! -f "backend/app/$TARGET_APK" ]; then
            echo -e "${CYAN}  [APK] Target APK missing for v${APP_VERSION}. Initiating build...            ${NC}"
        else
            echo -e "${CYAN}  [APK] Triggering clean build of HealthWatch APK v${APP_VERSION}...          ${NC}"
        fi
        echo -e "${CYAN}  Target: v${APP_VERSION} | Domain: ${DOMAIN_NAME} | HTTPS: ${ENABLE_HTTPS}   ${NC}"
        echo -e "${CYAN}====================================================================${NC}"

        if [ ! -f "mobile/build_apk_linux.sh" ]; then
            echo -e "${RED}Error: 'mobile/build_apk_linux.sh' not found.${NC}"
            exit 1
        fi

        if ! command -v java &>/dev/null && [ ! -d "/usr/lib/jvm/java-17-openjdk-amd64" ] && [ ! -d "$HOME/jdk-17" ]; then
            echo -e "${RED}Error: OpenJDK 17 ('java') is required to build the APK but not found.${NC}"
            echo -e "${YELLOW}Please install OpenJDK 17: sudo apt install -y openjdk-17-jdk-headless${NC}"
            exit 1
        fi

        echo -e "\n${BLUE}Compiling Android APK with Gradle for release v${APP_VERSION}...${NC}"
        SERVER_DOMAIN="${DOMAIN_NAME}" ENABLE_HTTPS="${ENABLE_HTTPS}" APP_VERSION="${APP_VERSION}" bash mobile/build_apk_linux.sh

        if [ ! -f "backend/app/$TARGET_APK" ] || [ ! -f "frontend/public/$TARGET_APK" ]; then
            echo -e "${RED}Error: APK build finished but 'HealthWatch-v${APP_VERSION}.apk' was not found!${NC}"
            exit 1
        fi

        echo "$APP_VERSION" > "mobile/.last_built_apk_version"
        echo -e "${GREEN}✓ Successfully built and deployed HealthWatch APK v${APP_VERSION}.${NC}"
        cleanup_old_apks
    else
        echo -e "\n${GREEN}✓ Android APK is already up-to-date for v${APP_VERSION} (backend/app/$TARGET_APK). Rebuild skipped.${NC}"
        echo -e "  ${YELLOW}(Run './deploy.sh apk' to force an immediate clean rebuild if needed)${NC}"
        cleanup_old_apks
    fi
}

build_images() {
    build_apk false
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
        build_apk true
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
    clean-apks|prune-apks)
        cleanup_old_apks
        ;;
    *)
        echo -e "\nUsage: $0 {http|https|build|apk|clean-apks|stop|status|logs|import-wards|verify-wards} [version_tag]"
        echo -e "  ${CYAN}./deploy.sh build [tag]${NC}        - Build production Docker images with specific tag"
        echo -e "  ${CYAN}./deploy.sh http [tag]${NC}         - Build and launch in HTTP mode on port 80"
        echo -e "  ${CYAN}./deploy.sh https [tag]${NC}        - Build and launch in HTTPS mode with Let's Encrypt SSL on port 443"
        echo -e "  ${CYAN}./deploy.sh apk${NC}                - Compile Android APK with domain injected from .env configuration"
        echo -e "  ${CYAN}./deploy.sh clean-apks${NC}         - Purge obsolete APK versions and synchronize active release"
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
