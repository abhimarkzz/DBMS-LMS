#!/usr/bin/env bash
# ==============================================================================
# LMS Deployment & Readiness Verification Script
# ==============================================================================
set -euo pipefail

GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}======================================================${NC}"
echo -e "${BLUE}  LMS Production Deployment Readiness Check           ${NC}"
echo -e "${BLUE}======================================================${NC}"

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

ERRORS=0

# 1. Check Python & Virtualenv
echo -e "\n${YELLOW}[1/5] Checking Python Environment...${NC}"
if [ -d "venv" ]; then
    echo -e "  ${GREEN}✓${NC} Python virtual environment detected at ./venv"
    source venv/bin/activate
elif command -v python3 &>/dev/null; then
    echo -e "  ${GREEN}✓${NC} System python3 available: $(python3 --version)"
else
    echo -e "  ${RED}✗${NC} Python 3 is not installed!"
    ERRORS=$((ERRORS + 1))
fi

# 2. Check Backend Dependencies & Syntax
echo -e "\n${YELLOW}[2/5] Validating Backend Core & Import Syntax...${NC}"
if PYTHONPATH=backend python3 -c "from app.main import app; print('  Backend imports verified successfully.')" 2>/dev/null; then
    echo -e "  ${GREEN}✓${NC} FastAPI application loaded and configured cleanly."
else
    echo -e "  ${RED}✗${NC} Failed to import app.main! Check backend dependencies."
    ERRORS=$((ERRORS + 1))
fi

# 3. Check Database Health via App Engine
echo -e "\n${YELLOW}[3/5] Checking Database Connections (Postgres, Mongo, Redis)...${NC}"
PYTHONPATH=backend python3 -c "
import sys
from app.main import app
from fastapi.testclient import TestClient

client = TestClient(app)
res = client.get('/api/admin/health')
if res.status_code == 200:
    data = res.json()
    print('  PostgreSQL Status:', data.get('components', {}).get('postgresql', {}).get('status'))
    print('  pgvector Status:  ', data.get('components', {}).get('pgvector', {}).get('status'))
    print('  MongoDB Status:   ', data.get('components', {}).get('mongodb', {}).get('status'))
    print('  Redis Status:     ', data.get('components', {}).get('redis', {}).get('status'))
else:
    print('  Health check returned status:', res.status_code)
    sys.exit(1)
" || {
    echo -e "  ${RED}✗${NC} Health check failed!"
    ERRORS=$((ERRORS + 1))
}

# 4. Check Frontend Build & Typechecking
echo -e "\n${YELLOW}[4/5] Building & Typechecking Frontend Assets...${NC}"
if (cd frontend && npm run build >/dev/null 2>&1); then
    echo -e "  ${GREEN}✓${NC} Frontend production bundle built successfully (dist/ ready)."
else
    echo -e "  ${RED}✗${NC} Frontend build failed! Run 'cd frontend && npm run build' for details."
    ERRORS=$((ERRORS + 1))
fi

# 5. Check Docker & Deployment Configuration Files
echo -e "\n${YELLOW}[5/5] Verifying Deployment Artifacts...${NC}"
FILES=("backend/Dockerfile" "frontend/Dockerfile" "frontend/nginx.conf" "docker-compose.yml" "Procfile" "render.yaml" "frontend/vercel.json")
for file in "${FILES[@]}"; do
    if [ -f "$file" ]; then
        echo -e "  ${GREEN}✓${NC} $file present"
    else
        echo -e "  ${RED}✗${NC} Missing $file!"
        ERRORS=$((ERRORS + 1))
    fi
done

echo -e "\n${BLUE}======================================================${NC}"
if [ "$ERRORS" -eq 0 ]; then
    echo -e "${GREEN}  ✓ ALL SYSTEMS GO: READY FOR DEPLOYMENT!           ${NC}"
    echo -e "${BLUE}======================================================${NC}"
    echo -e "Deployment Options:"
    echo -e "  • Docker Compose: docker compose up --build -d"
    echo -e "  • Render:         Push to GitHub and connect repository"
    echo -e "  • PaaS / Railway: Uses Procfile & Dockerfile automatically"
    echo -e "  • Frontend Host:  Deploy ./frontend to Vercel/Netlify"
    exit 0
else
    echo -e "${RED}  ✗ DEPLOYMENT CHECK FOUND $ERRORS ISSUE(S)       ${NC}"
    echo -e "${BLUE}======================================================${NC}"
    exit 1
fi
