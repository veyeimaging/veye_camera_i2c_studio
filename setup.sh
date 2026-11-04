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
# Configure pip mirror for faster installation
# ─────────────────────────────────────────────
# Auto-detect region, or force via REGION environment variable
# REGION=cn for China mirrors, REGION=global for official PyPI

setup_pip_mirror() {
    local region="${REGION:-auto}"
    
    if [ "$region" = "auto" ]; then
        # Auto-detect based on timezone
        local timezone=$(cat /etc/timezone 2>/dev/null || echo "")
        if [[ "$timezone" == *"Shanghai"* ]] || [[ "$timezone" == *"Chongqing"* ]] || [[ "$timezone" == *"Asia/China"* ]]; then
            region="cn"
        else
            region="global"
        fi
    fi
    
    case "$region" in
        cn|china|CN)
            PIP_INDEX_URL="https://pypi.tuna.tsinghua.edu.cn/simple"
            PIP_TRUSTED_HOST="pypi.tuna.tsinghua.edu.cn"
            REGION_NAME="China (Tsinghua Mirror)"
            ;;
        *)
            PIP_INDEX_URL="https://pypi.org/simple"
            PIP_TRUSTED_HOST="pypi.org"
            REGION_NAME="Global (Official PyPI)"
            ;;
    esac
    
    echo "  Region: $REGION_NAME"
}

# ─────────────────────────────────────────────
# Check if dependencies are already installed
# ─────────────────────────────────────────────
check_dependencies_installed() {
    local required_packages=("fastapi" "uvicorn" "pydantic" "jinja2")
    local all_installed=true
    
    for pkg in "${required_packages[@]}"; do
        if ! $PIP_CMD show "$pkg" &>/dev/null; then
            all_installed=false
            break
        fi
    done
    
    $all_installed
}

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

if [ ! -f "$SOURCE_DIR/Makefile" ]; then
    fail "Makefile not found in $SOURCE_DIR"
fi

cd "$SOURCE_DIR"
make clean
make -j$(nproc)

chmod +x "$TOOLS_DIR/i2c_vread" "$TOOLS_DIR/i2c_vwrite" \
         "$TOOLS_DIR/i2c_4read" "$TOOLS_DIR/i2c_4write" 2>/dev/null || true
ARCH=$(uname -m)
info "I2C tools compiled for $ARCH"

cd "$SCRIPT_DIR"

# ─────────────────────────────────────────────
# 3. Set up Python environment
# ─────────────────────────────────────────────
echo ""
echo "--- Setting up Python environment ---"

# Setup pip mirror
setup_pip_mirror

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
    "$PIP_CMD" install --quiet --upgrade pip --index-url "$PIP_INDEX_URL" --trusted-host "$PIP_TRUSTED_HOST"
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

# ─────────────────────────────────────────────
# Check if dependencies are already installed
# ─────────────────────────────────────────────
check_dependencies_installed() {
    local required_packages=("fastapi" "uvicorn" "pydantic" "jinja2")
    local all_installed=true
    
    for pkg in "${required_packages[@]}"; do
        if ! $PIP_CMD show "$pkg" &>/dev/null; then
            all_installed=false
            break
        fi
    done
    
    $all_installed
}

# Install dependencies
echo "  Checking dependencies..."
if check_dependencies_installed; then
    info "Dependencies already installed (skipping)"
else
    echo "  Installing dependencies..."
    $PIP_CMD install -r "$PROJECT_DIR/requirements.txt" \
        --index-url "$PIP_INDEX_URL" \
        --trusted-host "$PIP_TRUSTED_HOST" \
        --timeout 60 \
        $($USE_VENV || echo "--break-system-packages --user") \
        || {
            warn "Installation failed. Trying with alternative mirror..."
            # If failed, try alternative mirror
            if [ "$region" = "cn" ]; then
                echo "  Switching to Aliyun mirror..."
                $PIP_CMD install -r "$PROJECT_DIR/requirements.txt" \
                    --index-url "https://mirrors.aliyun.com/pypi/simple/" \
                    --trusted-host "mirrors.aliyun.com" \
                    --timeout 60 \
                    $($USE_VENV || echo "--break-system-packages --user") \
                    || fail "Failed to install dependencies"
            else
                echo "  Switching to Tsinghua mirror..."
                $PIP_CMD install -r "$PROJECT_DIR/requirements.txt" \
                    --index-url "https://pypi.tuna.tsinghua.edu.cn/simple" \
                    --trusted-host "pypi.tuna.tsinghua.edu.cn" \
                    --timeout 60 \
                    $($USE_VENV || echo "--break-system-packages --user") \
                    || fail "Failed to install dependencies"
            fi
        }
    info "Dependencies installed"
fi

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
