#!/usr/bin/env bash
# ==============================================================================
# HealthWatch - Docker Hub Publishing & Documentation Sync Script
# ==============================================================================
# Tags and pushes HealthWatch container images to Docker Hub registry,
# and automatically pushes markdown README pages to each repository overview
# via the official Docker Hub REST API.
# ==============================================================================

set -euo pipefail

# Text formatting
RED=$'\033[0;31m'
GREEN=$'\033[0;32m'
BLUE=$'\033[0;34m'
YELLOW=$'\033[1;33m'
CYAN=$'\033[0;36m'
BOLD=$'\033[1m'
NC=$'\033[0m'

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

# Detect default version from .env.production or .env
DETECTED_VERSION=""
if [[ -f "${PROJECT_ROOT}/.env.production" ]]; then
    DETECTED_VERSION="$(grep -E '^APP_VERSION=' "${PROJECT_ROOT}/.env.production" | cut -d '=' -f2- | tr -d ' "\r' || true)"
elif [[ -f "${PROJECT_ROOT}/.env" ]]; then
    DETECTED_VERSION="$(grep -E '^APP_VERSION=' "${PROJECT_ROOT}/.env" | cut -d '=' -f2- | tr -d ' "\r' || true)"
fi

# Default configurations
DOCKERHUB_USER="${DOCKERHUB_USER:-}"
DOCKERHUB_TOKEN="${DOCKERHUB_TOKEN:-${DOCKERHUB_PASSWORD:-}}"
VERSION_TAG="${VERSION_TAG:-${DETECTED_VERSION:-1.0.0}}"
DRY_RUN=false
SKIP_README=false

usage() {
    cat << EOF
${BOLD}Usage:${NC} $0 [options]

${BOLD}Options:${NC}
  -u, --username <name>    Docker Hub username or organization namespace (default: auto-detected from ~/.docker/config.json or DOCKERHUB_USER)
  -t, --tag <tag>          Image version tag to publish (default: 1.0.0)
  --token <token>          Docker Hub Personal Access Token or password (default: auto-detected from ~/.docker/config.json or DOCKERHUB_TOKEN)
  --docker-config <path>   Custom Docker config JSON path (default: ~/.docker/config.json)
  --skip-readme            Push Docker images only; skip updating Docker Hub README overviews
  --dry-run                Print actions without tagging, pushing, or making API calls
  -h, --help               Display this help message

${BOLD}Examples:${NC}
  # Interactive / Auto mode (reads credentials directly from ~/.docker/config.json):
  $0

  # Automated execution with custom tag:
  $0 -t 1.0.0

  # Override credentials or namespace:
  $0 -u mydockerhubuser --token dckr_pat_xxxx --tag 1.0.0

  # Preview actions without pushing:
  $0 --dry-run
EOF
    exit 0
}

# Parse CLI arguments
while [[ $# -gt 0 ]]; do
    case "$1" in
        -u|--username)
            DOCKERHUB_USER="$2"
            shift 2
            ;;
        -t|--tag)
            VERSION_TAG="$2"
            shift 2
            ;;
        --token)
            DOCKERHUB_TOKEN="$2"
            shift 2
            ;;
        --docker-config)
            DOCKER_CONFIG_FILE="$2"
            shift 2
            ;;
        --skip-readme)
            SKIP_README=true
            shift
            ;;
        --dry-run)
            DRY_RUN=true
            shift
            ;;
        -h|--help)
            usage
            ;;
        *)
            echo -e "${RED}Unknown option: $1${NC}"
            usage
            ;;
    esac
done

# Auto-detect credentials from Docker configuration if not explicitly provided
DOCKER_CONFIG_DIR="${DOCKER_CONFIG:-${HOME}/.docker}"
DOCKER_CONFIG_FILE="${DOCKER_CONFIG_FILE:-${DOCKER_CONFIG_DIR}/config.json}"
LOADED_USER_FROM_CONFIG=false
LOADED_TOKEN_FROM_CONFIG=false

if [[ -f "${DOCKER_CONFIG_FILE}" ]] && command -v python3 >/dev/null 2>&1; then
    mapfile -t CRED_DATA < <(python3 - "${DOCKER_CONFIG_FILE}" << 'PYEOF'
import sys
import json
import base64
import shutil
import subprocess

config_path = sys.argv[1]
try:
    with open(config_path, "r", encoding="utf-8") as f:
        cfg = json.load(f)

    auths = cfg.get("auths", {})
    registries = [
        "https://index.docker.io/v1/",
        "index.docker.io/v1/",
        "https://registry-1.docker.io/v2/",
        "registry-1.docker.io",
        "docker.io"
    ]

    # 1. Direct auth entries in config.json
    for reg in registries:
        if reg in auths and "auth" in auths[reg]:
            decoded = base64.b64decode(auths[reg]["auth"]).decode("utf-8", errors="ignore")
            if ":" in decoded:
                user, secret = decoded.split(":", 1)
                if user and secret:
                    print(user)
                    print(secret)
                    sys.exit(0)

    # 2. Check credential helpers / credStore if configured
    helper = None
    cred_helpers = cfg.get("credHelpers", {})
    for reg in registries:
        if reg in cred_helpers:
            helper = f"docker-credential-{cred_helpers[reg]}"
            target = reg
            break
    if not helper and "credsStore" in cfg:
        helper = f"docker-credential-{cfg['credsStore']}"
        target = "https://index.docker.io/v1/"

    if helper and shutil.which(helper):
        proc = subprocess.run([helper, "get"], input=target.encode(), stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if proc.returncode == 0:
            res = json.loads(proc.stdout.decode())
            user = res.get("Username") or res.get("ServerURL")
            secret = res.get("Secret")
            if user and secret:
                print(user)
                print(secret)
                sys.exit(0)
except Exception:
    pass
PYEOF
)
    CFG_USER="${CRED_DATA[0]:-}"
    CFG_TOKEN="${CRED_DATA[1]:-}"

    if [[ -z "${DOCKERHUB_USER}" ]] && [[ -n "${CFG_USER}" ]]; then
        DOCKERHUB_USER="${CFG_USER}"
        LOADED_USER_FROM_CONFIG=true
    fi

    if [[ -z "${DOCKERHUB_TOKEN}" ]] && [[ -n "${CFG_TOKEN}" ]]; then
        if [[ "${DOCKERHUB_USER}" == "${CFG_USER}" ]]; then
            DOCKERHUB_TOKEN="${CFG_TOKEN}"
            LOADED_TOKEN_FROM_CONFIG=true
        fi
    fi
fi

echo -e "${CYAN}${BOLD}================================================================${NC}"
echo -e "${CYAN}${BOLD}       HealthWatch Docker Hub Publisher & Documentation Sync     ${NC}"
echo -e "${CYAN}${BOLD}================================================================${NC}"

# Check Docker CLI
if ! command -v docker >/dev/null 2>&1; then
    echo -e "${RED}[ERROR] 'docker' CLI is not installed or not in PATH.${NC}"
    exit 1
fi

if [[ "${LOADED_USER_FROM_CONFIG}" = true ]] || [[ "${LOADED_TOKEN_FROM_CONFIG}" = true ]]; then
    echo -e "  ${GREEN}✓${NC} Loaded credentials from ${BOLD}${DOCKER_CONFIG_FILE}${NC} (User: ${BOLD}${DOCKERHUB_USER}${NC})"
fi

# Prompt for username if not provided
if [[ -z "${DOCKERHUB_USER}" ]]; then
    if [[ -t 0 ]]; then
        read -rp "Enter your Docker Hub username (e.g. johndoe): " DOCKERHUB_USER
    else
        echo -e "${RED}[ERROR] Docker Hub username not specified. Set DOCKERHUB_USER, use -u <username>, or configure ~/.docker/config.json.${NC}"
        exit 1
    fi
fi

if [[ -z "${DOCKERHUB_USER}" ]]; then
    echo -e "${RED}[ERROR] Docker Hub username cannot be empty.${NC}"
    exit 1
fi

echo -e "${BLUE}Target Registry Namespace:${NC} ${BOLD}${DOCKERHUB_USER}${NC}"
echo -e "${BLUE}Target Version Tag:       ${NC} ${BOLD}${VERSION_TAG}${NC} (and ${BOLD}latest${NC})"
echo -e "${BLUE}Docker Hub Credentials:   ${NC} $(if [[ -n "${DOCKERHUB_TOKEN}" ]]; then echo -e "${GREEN}Configured (Token loaded)${NC}"; else echo -e "${YELLOW}Not configured (will prompt for README sync)${NC}"; fi)"
echo -e "${BLUE}Dry Run Mode:             ${NC} ${BOLD}${DRY_RUN}${NC}"
echo ""

# Microservices list: <LocalImageName>:<SubdirectoryWithReadme>:<ShortDescription>
SERVICES=(
    "healthwatch-backend:backend:HealthWatch Disease Surveillance & Contact Tracing REST API (FastAPI + PostGIS)"
    "healthwatch-frontend:frontend:HealthWatch React 18 Surveillance Dashboard & Android APK Distribution"
    "healthwatch-gateway:gateway:HealthWatch High-Performance Reverse Proxy & Automated SSL Gateway (Nginx)"
)

# Verify local images exist
echo -e "${CYAN}==> Verifying local images...${NC}"
MISSING_IMAGES=0
for entry in "${SERVICES[@]}"; do
    IFS=":" read -r img_name img_dir short_desc <<< "${entry}"
    if ! docker image inspect "${img_name}:${VERSION_TAG}" >/dev/null 2>&1; then
        if docker image inspect "${img_name}:latest" >/dev/null 2>&1; then
            echo -e "${YELLOW}[WARN] Found ${img_name}:latest, tagging as ${img_name}:${VERSION_TAG}...${NC}"
            if [[ "${DRY_RUN}" = false ]]; then
                docker tag "${img_name}:latest" "${img_name}:${VERSION_TAG}"
            fi
        else
            echo -e "${RED}[ERROR] Local image ${img_name}:${VERSION_TAG} not found!${NC}"
            MISSING_IMAGES=$((MISSING_IMAGES + 1))
        fi
    else
        echo -e "  ${GREEN}✓${NC} Found ${img_name}:${VERSION_TAG}"
    fi
done

if [[ ${MISSING_IMAGES} -gt 0 ]]; then
    echo -e "${RED}[ERROR] ${MISSING_IMAGES} image(s) missing. Build them before running this script.${NC}"
    echo -e "Run: ./deploy.sh or docker compose -f docker/docker-compose.prod.yml build"
    exit 1
fi

# Ensure user is logged in
if [[ "${DRY_RUN}" = false ]]; then
    echo ""
    echo -e "${CYAN}==> Checking Docker Hub authentication...${NC}"
    if ! docker info 2>/dev/null | grep -q "Username: ${DOCKERHUB_USER}"; then
        echo -e "${YELLOW}Authenticating with Docker Hub for ${BOLD}${DOCKERHUB_USER}${NC}...${NC}"
        if [[ -n "${DOCKERHUB_TOKEN}" ]]; then
            echo "${DOCKERHUB_TOKEN}" | docker login -u "${DOCKERHUB_USER}" --password-stdin
        else
            docker login -u "${DOCKERHUB_USER}"
        fi
    else
        echo -e "  ${GREEN}✓${NC} Authenticated as ${BOLD}${DOCKERHUB_USER}${NC}"
    fi
fi

# Tag and push images
echo ""
echo -e "${CYAN}==> Tagging and pushing images to Docker Hub...${NC}"

for entry in "${SERVICES[@]}"; do
    IFS=":" read -r img_name img_dir short_desc <<< "${entry}"
    TARGET_REPO="${DOCKERHUB_USER}/${img_name}"

    echo -e "\n${BOLD}[${img_name}]${NC}"
    
    # Tag version and latest
    echo -e "  -> Tagging ${TARGET_REPO}:${VERSION_TAG}"
    echo -e "  -> Tagging ${TARGET_REPO}:latest"
    if [[ "${DRY_RUN}" = false ]]; then
        docker tag "${img_name}:${VERSION_TAG}" "${TARGET_REPO}:${VERSION_TAG}"
        docker tag "${img_name}:${VERSION_TAG}" "${TARGET_REPO}:latest"
    fi

    # Push
    echo -e "  -> Pushing ${TARGET_REPO}:${VERSION_TAG}..."
    if [[ "${DRY_RUN}" = false ]]; then
        docker push "${TARGET_REPO}:${VERSION_TAG}"
    fi

    echo -e "  -> Pushing ${TARGET_REPO}:latest..."
    if [[ "${DRY_RUN}" = false ]]; then
        docker push "${TARGET_REPO}:latest"
    fi

    echo -e "  ${GREEN}✓ Successfully pushed ${TARGET_REPO}${NC}"
done

# Push README documentation to Docker Hub Repository Overview
if [[ "${SKIP_README}" = true ]]; then
    echo -e "\n${YELLOW}[INFO] Skipped Docker Hub README update (--skip-readme was passed).${NC}"
else
    echo ""
    echo -e "${CYAN}${BOLD}==> Updating Docker Hub Repository Overview READMEs...${NC}"

    if [[ -z "${DOCKERHUB_TOKEN}" ]] && [[ -t 0 ]] && [[ "${DRY_RUN}" = false ]]; then
        echo -e "\nTo automatically push the markdown READMEs to each Docker Hub repository overview,"
        echo -e "a Docker Hub Personal Access Token (PAT) or password is required."
        echo -e "Generate one at: ${CYAN}https://hub.docker.com/settings/security${NC} (Read & Write permissions)."
        read -rsp "Enter Docker Hub Token / Password (press ENTER to skip): " DOCKERHUB_TOKEN
        echo ""
    fi

    if [[ -z "${DOCKERHUB_TOKEN}" ]]; then
        echo -e "\n${YELLOW}[NOTICE] No Docker Hub Personal Access Token provided.${NC}"
        echo -e "Images were successfully pushed, but repository README overviews were not updated automatically."
        echo -e "To upload READMEs automatically next time:"
        echo -e "  ${BOLD}export DOCKERHUB_TOKEN=\"dckr_pat_xxxx\"${NC}"
        echo -e "  ${BOLD}$0 -u ${DOCKERHUB_USER} --token \"dckr_pat_xxxx\"${NC}"
        echo -e "\nAlternatively, copy the markdown files manually to Docker Hub repository overview:"
        for entry in "${SERVICES[@]}"; do
            IFS=":" read -r img_name img_dir short_desc <<< "${entry}"
            echo -e "  - ${BOLD}${img_name}:${NC} ${SCRIPT_DIR}/${img_dir}/README.md"
        done
    else
        # Execute Python helper to push READMEs via Docker Hub API
        python3 - "${DOCKERHUB_USER}" "${DOCKERHUB_TOKEN}" "${SCRIPT_DIR}" "${DRY_RUN}" << 'PYEOF'
import sys
import json
import urllib.request
import urllib.error
from pathlib import Path

username = sys.argv[1]
token_or_pw = sys.argv[2]
script_dir = Path(sys.argv[3])
dry_run = sys.argv[4].lower() == 'true'

repos = [
    {
        "repo": "healthwatch-backend",
        "readme": script_dir / "backend" / "README.md",
        "description": "HealthWatch Disease Surveillance & Contact Tracing REST API (FastAPI + PostGIS)"
    },
    {
        "repo": "healthwatch-frontend",
        "readme": script_dir / "frontend" / "README.md",
        "description": "HealthWatch React 18 Surveillance Dashboard & Android APK Distribution"
    },
    {
        "repo": "healthwatch-gateway",
        "readme": script_dir / "gateway" / "README.md",
        "description": "HealthWatch High-Performance Reverse Proxy & Automated SSL Gateway (Nginx)"
    }
]

if dry_run:
    print("[DRY-RUN] Would authenticate with Docker Hub API and push READMEs.")
    sys.exit(0)

# Step 1: Login to Docker Hub v2 API to obtain JWT
print(f"Authenticating with Docker Hub API for user '{username}'...")
login_url = "https://hub.docker.com/v2/users/login/"
login_data = json.dumps({"username": username, "password": token_or_pw}).encode("utf-8")
req = urllib.request.Request(login_url, data=login_data, headers={"Content-Type": "application/json"})

try:
    with urllib.request.urlopen(req) as response:
        res_body = json.loads(response.read().decode("utf-8"))
        jwt_token = res_body.get("token")
        if not jwt_token:
            print("\033[0;31m[ERROR] Could not retrieve JWT token from Docker Hub API.\033[0m")
            sys.exit(1)
        print("\033[0;32m  ✓ Docker Hub API Authentication successful.\033[0m\n")
except urllib.error.HTTPError as e:
    print(f"\033[0;31m[ERROR] Docker Hub API Login failed ({e.code}): {e.read().decode('utf-8')}\033[0m")
    sys.exit(1)
except Exception as e:
    print(f"\033[0;31m[ERROR] Connection error during Docker Hub authentication: {e}\033[0m")
    sys.exit(1)

# Step 2: Push each README to PATCH /v2/repositories/<username>/<repo>/
for item in repos:
    repo_name = item["repo"]
    readme_path = item["readme"]
    short_desc = item["description"]

    if not readme_path.exists():
        print(f"\033[0;33m[WARN] README file not found: {readme_path}\033[0m")
        continue

    content = readme_path.read_text(encoding="utf-8")
    # Dynamically customize YOUR_DOCKERHUB_USERNAME placeholder to actual username
    content = content.replace("YOUR_DOCKERHUB_USERNAME", username)

    patch_url = f"https://hub.docker.com/v2/repositories/{username}/{repo_name}/"
    patch_data = json.dumps({
        "description": short_desc,
        "full_description": content
    }).encode("utf-8")

    patch_req = urllib.request.Request(
        patch_url,
        data=patch_data,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"JWT {jwt_token}"
        },
        method="PATCH"
    )

    try:
        with urllib.request.urlopen(patch_req) as response:
            if response.status in (200, 204):
                print(f"  \033[0;32m✓ [{username}/{repo_name}]\033[0m Successfully updated repository overview README!")
            else:
                print(f"  \033[0;33m? [{username}/{repo_name}]\033[0m Status: {response.status}")
    except urllib.error.HTTPError as e:
        print(f"  \033[0;31m✗ [{username}/{repo_name}]\033[0m API update error ({e.code}): {e.read().decode('utf-8')}")
    except Exception as e:
        print(f"  \033[0;31m✗ [{username}/{repo_name}]\033[0m Error updating README: {e}")

PYEOF
    fi
fi

echo ""
echo -e "${GREEN}${BOLD}================================================================${NC}"
echo -e "${GREEN}${BOLD}   ✓ Docker Hub Release & Documentation Push Completed!          ${NC}"
echo -e "${GREEN}${BOLD}================================================================${NC}"
echo -e "Your images and documentation are now live at:"
echo -e "  - ${CYAN}https://hub.docker.com/r/${DOCKERHUB_USER}/healthwatch-backend${NC}"
echo -e "  - ${CYAN}https://hub.docker.com/r/${DOCKERHUB_USER}/healthwatch-frontend${NC}"
echo -e "  - ${CYAN}https://hub.docker.com/r/${DOCKERHUB_USER}/healthwatch-gateway${NC}"
echo ""
echo -e "To deploy on any server using these images:"
echo -e "  1. Download ${BOLD}docker-compose.hub.yml${NC}"
echo -e "  2. Download ${BOLD}env.fullstack.sample${NC} and rename to ${BOLD}.env${NC}"
echo -e "  3. Set ${BOLD}DOCKERHUB_USER=${DOCKERHUB_USER}${NC} in ${BOLD}.env${NC}"
echo -e "  4. Run: ${BOLD}docker compose -f docker-compose.hub.yml up -d${NC}"
echo ""
