#!/bin/bash
# VEYE Web Studio - Universal Setup & Launch Script
# Compiles I2C tools from source, sets up Python environment, and launches the server.
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$SCRIPT_DIR/veye_camera_web_studio"
VENV_DIR="$PROJECT_DIR/.venv"
TOOLS_DIR="$PROJECT_DIR/tools"
SOURCE_DIR="$TOOLS_DIR/source"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

info()  { echo -e "${GREEN}✅ $1${NC}"; }
warn()  { echo -e "${YELLOW}⚠️  $1${NC}"; }
fail()  { echo -e "${RED}❌ $1${NC}"; exit 1; }

echo "=========================================="
echo "  VEYE Web Studio - Setup"
echo "=========================================="
echo ""

# ─────────────────────────────────────────────
# 1. Check Python 3
# ─────────────────────────────────────────────
if ! command -v python3 &>/dev/null; then
    fail "Python 3 is required but not found.\n   Install with: sudo apt install python3"
fi
PY_VERSION=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
info "Python $PY_VERSION found"

# ─────────────────────────────────────────────
# 2. Compile I2C tools from source
# ─────────────────────────────────────────────
echo ""
echo "--- Compiling I2C tools ---"

if ! command -v gcc &>/dev/null; then
    fail "gcc is required but not found.\n   Install with: sudo apt install gcc"
fi

if [ ! -f "$SOURCE_DIR/i2c_vread.c" ] || [ ! -f "$SOURCE_DIR/i2c_vwrite.c" ]; then
    fail "Source files not found in $SOURCE_DIR"
fi

cd "$SOURCE_DIR"

echo "  Compiling i2c_vread..."
gcc -Wall -O2 -o ../i2c_vread i2c_vread.c strfunc.c
echo "  Compiling i2c_vwrite..."
gcc -Wall -O2 -o ../i2c_vwrite i2c_vwrite.c strfunc.c

chmod +x "$TOOLS_DIR/i2c_vread" "$TOOLS_DIR/i2c_vwrite"
ARCH=$(uname -m)
info "I2C tools compiled for $ARCH"

cd "$SCRIPT_DIR"

# ─────────────────────────────────────────────
# 3. Set up Python environment
# ─────────────────────────────────────────────
echo ""
echo "--- Setting up Python environment ---"

USE_VENV=false
PYTHON_CMD="python3"
PIP_CMD="pip3"

# Try venv first
if python3 -m venv --help &>/dev/null 2>&1; then
    if [ ! -d "$VENV_DIR" ] || [ ! -x "$VENV_DIR/bin/pip" ]; then
        # venv missing or broken — (re)create it
        rm -rf "$VENV_DIR" 2>/dev/null || true
        echo "  Creating virtual environment..."
        if python3 -m venv "$VENV_DIR" 2>/dev/null; then
            USE_VENV=true
        else
            warn "venv creation failed (missing python3-venv package?), falling back to system pip"
        fi
    else
        USE_VENV=true
    fi
fi

if $USE_VENV; then
    PYTHON_CMD="$VENV_DIR/bin/python"
    PIP_CMD="$VENV_DIR/bin/pip"
    "$PIP_CMD" install --quiet --upgrade pip
    info "Virtual environment ready"
else
    # Fallback: use system pip with --break-system-packages (PEP 668 on Ubuntu 24.04+)
    if ! command -v pip3 &>/dev/null; then
        echo "  Installing pip..."
        curl -sS https://bootstrap.pypa.io/get-pip.py | python3 - --break-system-packages --user 2>/dev/null \
            || fail "Cannot install pip. Try: sudo apt install python3-pip"
    fi
    PIP_CMD="pip3"
    warn "Using system Python (no venv)"
fi

# Install dependencies
echo "  Installing dependencies..."
$PIP_CMD install --quiet -r "$PROJECT_DIR/requirements.txt" \
    $($USE_VENV || echo "--break-system-packages --user") 2>/dev/null \
    || $PIP_CMD install --quiet -r "$PROJECT_DIR/requirements.txt"
info "Dependencies installed"

# ─────────────────────────────────────────────
# 4. Make probe scripts executable
# ─────────────────────────────────────────────
PROBE_DIR="$TOOLS_DIR/probe"
if [ -d "$PROBE_DIR" ]; then
    chmod +x "$PROBE_DIR"/*.sh 2>/dev/null || true
    info "Probe scripts configured"
fi

# ─────────────────────────────────────────────
# 5. Create logs directory
# ─────────────────────────────────────────────
mkdir -p "$PROJECT_DIR/logs"

# ─────────────────────────────────────────────
# Done
# ─────────────────────────────────────────────
echo ""
echo "=========================================="
echo "  Setup complete!"
echo "=========================================="
echo ""
echo "To start the server:"
echo "  cd $PROJECT_DIR"
echo "  $PYTHON_CMD main.py"
echo ""
echo "Or use: ./setup.sh --start"
echo ""
echo "Then open: http://localhost:8080"
echo ""

# ─────────────────────────────────────────────
# Handle --start flag
# ─────────────────────────────────────────────
if [ "$1" = "--start" ]; then
    echo "🚀 Starting VEYE Web Studio on http://0.0.0.0:8080"
    cd "$PROJECT_DIR"
    exec $PYTHON_CMD main.py
fi
