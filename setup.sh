#!/usr/bin/env bash
set -euo pipefail

echo "🏊🚴🏃 Fitness Dashboard — Project Setup"
echo "========================================="
echo ""

# --- Colors ---
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

ok()   { echo -e "  ${GREEN}[OK]${NC} $1"; }
warn() { echo -e "  ${YELLOW}[!!]${NC} $1"; }
fail() { echo -e "  ${RED}[FAIL]${NC} $1"; }

# --- Check pyenv ---
echo "Checking prerequisites..."
if command -v pyenv &> /dev/null; then
    ok "pyenv found"
else
    fail "pyenv not found — install from https://github.com/pyenv/pyenv"
    exit 1
fi

# --- Check/create pyenv virtualenv ---
if pyenv versions --bare | grep -q "^T3Daily$"; then
    ok "pyenv virtualenv 'T3Daily' exists"
else
    warn "pyenv virtualenv 'T3Daily' not found — creating..."
    PYTHON_VERSION=$(pyenv versions --bare | grep -E '^\d+\.\d+\.\d+$' | tail -1)
    if [ -z "$PYTHON_VERSION" ]; then
        fail "No Python version installed in pyenv. Run: pyenv install 3.12"
        exit 1
    fi
    pyenv virtualenv "$PYTHON_VERSION" T3Daily
    ok "Created virtualenv 'T3Daily' using Python $PYTHON_VERSION"
fi

# --- Activate and install dependencies ---
echo ""
echo "Activating virtualenv and installing dependencies..."
eval "$(pyenv init -)"
eval "$(pyenv virtualenv-init -)"
pyenv activate T3Daily

if [ -f requirements.txt ]; then
    pip install -q -r requirements.txt
    ok "Python dependencies installed from requirements.txt"
else
    # Minimal deps for Phase 0
    pip install -q openpyxl
    ok "Minimal dependencies installed (openpyxl)"
    warn "No requirements.txt found yet — will be created in Phase 1"
fi

# --- Check Podman ---
echo ""
echo "Checking container tools..."
if command -v podman &> /dev/null; then
    ok "Podman $(podman --version | awk '{print $3}')"
else
    warn "Podman not found — install with: sudo pacman -S podman"
fi

if command -v podman-compose &> /dev/null; then
    ok "podman-compose found"
else
    warn "podman-compose not found — install with: pip install podman-compose"
fi

# --- Check Tailscale ---
echo ""
echo "Checking networking..."
if command -v tailscale &> /dev/null; then
    ok "Tailscale $(tailscale version 2>/dev/null | head -1)"
else
    warn "Tailscale not found — install from https://tailscale.com/download/linux"
fi

# --- Check .env ---
echo ""
echo "Checking configuration..."
if [ -f .env ]; then
    ok ".env file exists"
else
    if [ -f .env.example ]; then
        warn ".env not found — copy from .env.example and fill in your credentials:"
        echo "       cp .env.example .env"
    else
        warn ".env and .env.example not yet created (will be set up in Phase 1)"
    fi
fi

# --- Check data files ---
echo ""
echo "Checking data files..."
if [ -f data/plan/8020_ironman_level1.json ]; then
    ok "80/20 Ironman Level 1 plan (JSON)"
else
    warn "80/20 plan not found at data/plan/8020_ironman_level1.json"
fi

if [ -f data/plan/8020_workout_library.json ]; then
    # Count filled vs empty workouts
    FILLED=$(python3 -c "
import json
with open('data/plan/8020_workout_library.json') as f:
    lib = json.load(f)
filled = sum(1 for w in lib['workouts'].values() if w.get('name'))
total = len(lib['workouts'])
print(f'{filled}/{total}')
" 2>/dev/null || echo "?/?")
    ok "80/20 workout library ($FILLED workouts populated)"
else
    warn "Workout library not found at data/plan/8020_workout_library.json"
fi

if [ -d data/plan/templates ]; then
    ok "Plan templates directory exists"
else
    warn "Plan templates not found at data/plan/templates/"
fi

# --- Summary ---
echo ""
echo "========================================="
echo "Setup complete! To activate the virtualenv:"
echo "  pyenv activate T3Daily"
echo ""
echo "Remaining Phase 0 tasks:"
echo "  - Populate swim and bike workout descriptions"
echo "  - Enable TrainerRoad iCal feed"
echo "  - Get Intervals.icu API key"
echo "  - Have Garmin Connect credentials ready"
echo "  - Install Podman + podman-compose (if not installed)"
echo "  - Install Tailscale (if not installed)"
echo "========================================="
