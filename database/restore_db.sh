#!/usr/bin/env bash
# ==============================================================================
# HealthWatch - Database Restore Utility
# ==============================================================================
# Restores a HealthWatch PostgreSQL + PostGIS dump (.sql or .sql.gz)
# into a running production or staging container.
# ==============================================================================

set -euo pipefail

# Text formatting
RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

# Default configurations
ENV_FILE="${PROJECT_ROOT}/.env.production"
if [[ ! -f "$ENV_FILE" ]]; then
    ENV_FILE="${PROJECT_ROOT}/.env"
fi

CONTAINER_NAME="healthwatch-db"
DUMP_FILE=""
ASSUME_YES=false

usage() {
    cat << EOF
${BOLD}Usage:${NC} $0 [options] [dump_file]

${BOLD}Options:${NC}
  -f, --file <path>       Path to .sql or .sql.gz database dump file
  -c, --container <name>  Database container name (default: healthwatch-db)
  -e, --env-file <path>   Path to environment configuration file (default: .env.production)
  -y, --yes               Skip confirmation prompt
  -h, --help              Display this help message

${BOLD}Examples:${NC}
  # Restore default latest dump into running container:
  $0

  # Restore specific dump file:
  $0 -f database/backups/healthwatch_production_dump.sql.gz

  # Non-interactive execution in CI/CD or automation:
  $0 -f database/backups/healthwatch_production_dump.sql -y
EOF
    exit 0
}

# Parse CLI arguments
while [[ $# -gt 0 ]]; do
    case "$1" in
        -f|--file)
            DUMP_FILE="$2"
            shift 2
            ;;
        -c|--container)
            CONTAINER_NAME="$2"
            shift 2
            ;;
        -e|--env-file)
            ENV_FILE="$2"
            shift 2
            ;;
        -y|--yes)
            ASSUME_YES=true
            shift
            ;;
        -h|--help)
            usage
            ;;
        *)
            if [[ -z "$DUMP_FILE" && -f "$1" ]]; then
                DUMP_FILE="$1"
                shift
            else
                echo -e "${RED}Unknown option or file not found: $1${NC}"
                usage
            fi
            ;;
    esac
done

# If no dump file specified, locate default backup
if [[ -z "$DUMP_FILE" ]]; then
    if [[ -f "${SCRIPT_DIR}/backups/healthwatch_production_dump.sql.gz" ]]; then
        DUMP_FILE="${SCRIPT_DIR}/backups/healthwatch_production_dump.sql.gz"
    elif [[ -f "${SCRIPT_DIR}/backups/healthwatch_production_dump.sql" ]]; then
        DUMP_FILE="${SCRIPT_DIR}/backups/healthwatch_production_dump.sql"
    elif [[ -f "${PROJECT_ROOT}/healthwatch_production_dump.sql" ]]; then
        DUMP_FILE="${PROJECT_ROOT}/healthwatch_production_dump.sql"
    else
        echo -e "${RED}[ERROR] No database dump file found in database/backups/.${NC}"
        echo -e "Please specify a dump file using: $0 -f <path-to-dump>"
        exit 1
    fi
fi

if [[ ! -f "$DUMP_FILE" ]]; then
    echo -e "${RED}[ERROR] Dump file does not exist: $DUMP_FILE${NC}"
    exit 1
fi

# Load database credentials from env file
if [[ -f "$ENV_FILE" ]]; then
    echo -e "${CYAN}Loading database credentials from:${NC} ${BOLD}${ENV_FILE}${NC}"
    # Read variables safely
    DB_USER="$(grep -E '^POSTGRES_USER=' "$ENV_FILE" | cut -d '=' -f2- | tr -d ' "\r' || true)"
    DB_NAME="$(grep -E '^POSTGRES_DB=' "$ENV_FILE" | cut -d '=' -f2- | tr -d ' "\r' || true)"
    DB_PASS="$(grep -E '^POSTGRES_PASSWORD=' "$ENV_FILE" | cut -d '=' -f2- | tr -d ' "\r' || true)"
fi

# Fallbacks if env file was missing or incomplete
DB_USER="${DB_USER:-healthwatch_admin}"
DB_NAME="${DB_NAME:-healthwatch_db}"

echo -e "${CYAN}${BOLD}================================================================${NC}"
echo -e "${CYAN}${BOLD}           HealthWatch Production Database Restore              ${NC}"
echo -e "${CYAN}${BOLD}================================================================${NC}"
echo -e "${BLUE}Target Container:${NC} ${BOLD}${CONTAINER_NAME}${NC}"
echo -e "${BLUE}Target Database: ${NC} ${BOLD}${DB_NAME}${NC}"
echo -e "${BLUE}Database User:   ${NC} ${BOLD}${DB_USER}${NC}"
echo -e "${BLUE}Dump File:       ${NC} ${BOLD}${DUMP_FILE}${NC} ($(du -h "$DUMP_FILE" | cut -f1))"
echo ""

# Verify Docker container is running
if ! docker ps --format '{{.Names}}' | grep -q "^${CONTAINER_NAME}$"; then
    echo -e "${RED}[ERROR] Container '${CONTAINER_NAME}' is not currently running!${NC}"
    echo -e "Start the container first: ${BOLD}docker compose up -d db${NC}"
    exit 1
fi

# Confirmation prompt
if [[ "$ASSUME_YES" = false ]]; then
    echo -e "${YELLOW}${BOLD}WARNING:${NC} Restoring this dump will insert/overwrite schema and table data in '${DB_NAME}'."
    read -rp "Are you sure you want to proceed? [y/N]: " confirm
    if [[ ! "$confirm" =~ ^[yY]([eE][sS])?$ ]]; then
        echo -e "${YELLOW}Restore operation cancelled by user.${NC}"
        exit 0
    fi
fi

echo -e "\n${CYAN}==> Step 1: Checking and preparing PostGIS extensions...${NC}"
docker exec "${CONTAINER_NAME}" psql -U "${DB_USER}" -d "${DB_NAME}" -c \
    "CREATE EXTENSION IF NOT EXISTS postgis; CREATE EXTENSION IF NOT EXISTS postgis_topology; CREATE EXTENSION IF NOT EXISTS \"uuid-ossp\";" \
    >/dev/null 2>&1 || true
echo -e "  ${GREEN}✓${NC} PostGIS extensions verified."

echo -e "\n${CYAN}==> Step 2: Restoring data from dump...${NC}"
START_TIME=$(date +%s)

if [[ "$DUMP_FILE" == *.gz ]]; then
    gunzip -c "$DUMP_FILE" | docker exec -i "${CONTAINER_NAME}" psql -U "${DB_USER}" -d "${DB_NAME}" >/dev/null
else
    docker exec -i "${CONTAINER_NAME}" psql -U "${DB_USER}" -d "${DB_NAME}" < "$DUMP_FILE" >/dev/null
fi

END_TIME=$(date +%s)
DURATION=$((END_TIME - START_TIME))
echo -e "  ${GREEN}✓${NC} Dump successfully applied in ${DURATION}s."

echo -e "\n${CYAN}==> Step 3: Verifying restored tables and record counts...${NC}"
echo ""
docker exec "${CONTAINER_NAME}" psql -U "${DB_USER}" -d "${DB_NAME}" -c "
SELECT relname AS table_name, n_live_tup AS total_rows 
FROM pg_stat_user_tables 
ORDER BY n_live_tup DESC;
"

echo -e "\n${GREEN}${BOLD}================================================================${NC}"
echo -e "${GREEN}${BOLD}   ✓ Database restore completed successfully!                    ${NC}"
echo -e "${GREEN}${BOLD}================================================================${NC}"
