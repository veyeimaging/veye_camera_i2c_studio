#!/bin/bash
# VEYE Web Studio - Multi-platform Installation Script
# Auto-detects Ubuntu version and Python version, intelligently selects dependency files

set -e

# Color output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

info()  { echo -e "${GREEN}✅ $1${NC}"; }
warn()  { echo -e "${YELLOW}⚠️  $1${NC}"; }
fail()  { echo -e "${RED}❌ $1${NC}"; exit 1; }
note()  { echo -e "${BLUE}ℹ️  $1${NC}"; }

echo "=========================================="
echo "  VEYE Web Studio - Multi-platform Setup"
echo "=========================================="
echo ""

# ─────────────────────────────────────────────
# 1. Detect System Information
# ─────────────────────────────────────────────
echo "--- System Detection ---"

# Detect Ubuntu version
if [ -f /etc/os-release ]; then
    . /etc/os-release
    DISTRO_NAME="$NAME"
    DISTRO_VERSION="$VERSION_ID"
    DISTRO_CODENAME="$VERSION_CODENAME"
    info "System: $DISTRO_NAME $DISTRO_VERSION ($DISTRO_CODENAME)"
else
    warn "Cannot detect system version"
    DISTRO_VERSION="unknown"
fi

# Detect architecture
ARCH=$(uname -m)
info "Architecture: $ARCH"

if [ "$ARCH" != "aarch64" ] && [ "$ARCH" != "x86_64" ]; then
    fail "Unsupported architecture: $ARCH (only supports aarch64 and x86_64)"
fi

# Detect Python version
PYTHON_VERSIONS=("python3.12" "python3.11" "python3.10" "python3.9" "python3")
BEST_PYTHON=""
BEST_PYTHON_VERSION=""

for py in "${PYTHON_VERSIONS[@]}"; do
    if command -v "$py" &>/dev/null; then
        py_version=$("$py" -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')" 2>/dev/null || echo "0")
        py_major=$("$py" -c "import sys; print(sys.version_info.major)" 2>/dev/null || echo "0")
        py_minor=$("$py" -c "import sys; print(sys.version_info.minor)" 2>/dev/null || echo "0")
        
        if [ "$py_major" -eq 3 ] && [ "$py_minor" -ge 9 ]; then
            BEST_PYTHON="$py"
            BEST_PYTHON_VERSION="$py_version"
            break
        fi
    fi
done

if [ -z "$BEST_PYTHON" ]; then
    fail "Python 3.9 or higher not found\n   Install with: sudo apt install python3.10"
fi

info "Python: $BEST_PYTHON_VERSION ($BEST_PYTHON)"

# ─────────────────────────────────────────────
# 2. Check Ubuntu 20.04 + Python 3.8 Special Case
# ─────────────────────────────────────────────
if [ "$DISTRO_VERSION" = "20.04" ] && [ "$BEST_PYTHON_VERSION" = "3.8" ]; then
    echo ""
    warn "Detected Ubuntu 20.04 + Python 3.8"
    note "This project requires Python 3.9+"
    echo ""
    echo "Please choose installation method:"
    echo "  1) Install Python 3.10 using deadsnakes PPA (recommended)"
    echo "  2) Use conda/miniconda"
    echo "  3) Compile Python 3.10 from source"
    echo "  4) Exit"
    echo ""
    
    read -p "Enter choice [1-4]: " choice
    
    case $choice in
        1)
            info "Installing Python 3.10..."
            sudo apt update
            sudo apt install -y software-properties-common
            sudo add-apt-repository -y ppa:deadsnakes/ppa
            sudo apt update
            sudo apt install -y python3.10 python3.10-venv python3.10-dev
            BEST_PYTHON="python3.10"
            BEST_PYTHON_VERSION="3.10"
            info "Python 3.10 installed successfully"
            ;;
        2)
            note "Please install miniconda manually:"
            echo "  wget https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-aarch64.sh"
            echo "  bash Miniconda3-latest-Linux-aarch64.sh"
            echo "  conda create -n veye python=3.10"
            echo "  conda activate veye"
            exit 0
            ;;
        3)
            note "Please refer to Python official documentation for source compilation"
            exit 0
            ;;
        4)
            exit 0
            ;;
        *)
            fail "Invalid option"
            ;;
    esac
fi

# ─────────────────────────────────────────────
# 3. Select Dependency File
# ─────────────────────────────────────────────
echo ""
echo "--- Dependency Selection ---"

PROJECT_DIR="$(cd "$(dirname "$0")/veye_camera_web_studio" && pwd)"
REQUIREMENTS_FILE=""

# Select dependencies based on Python version
py_minor=$(echo "$BEST_PYTHON_VERSION" | cut -d. -f2)

if [ "$py_minor" -ge 10 ]; then
    # Python 3.10+ use full locked version
    if [ -f "$PROJECT_DIR/requirements.lock" ]; then
        REQUIREMENTS_FILE="$PROJECT_DIR/requirements.lock"
        info "Using locked dependencies: requirements.lock (Python 3.10+)"
    else
        REQUIREMENTS_FILE="$PROJECT_DIR/requirements.txt"
        warn "Lock file not found, using requirements.txt"
    fi
elif [ "$py_minor" -eq 9 ]; then
    # Python 3.9 can also use locked version
    if [ -f "$PROJECT_DIR/requirements.lock" ]; then
        REQUIREMENTS_FILE="$PROJECT_DIR/requirements.lock"
        info "Using locked dependencies: requirements.lock (Python 3.9)"
    else
        REQUIREMENTS_FILE="$PROJECT_DIR/requirements.txt"
        warn "Lock file not found, using requirements.txt"
    fi
else
    # Python 3.8 needs compatible version (if available)
    if [ -f "$PROJECT_DIR/requirements-py38.txt" ]; then
        REQUIREMENTS_FILE="$PROJECT_DIR/requirements-py38.txt"
        warn "Using Python 3.8 compatible dependencies: requirements-py38.txt"
    else
        fail "Python 3.8 is not supported, please upgrade to Python 3.9+\n   Run: sudo apt install python3.10"
    fi
fi

# ─────────────────────────────────────────────
# 4. Platform-specific Optimizations
# ─────────────────────────────────────────────
echo ""
echo "--- Platform Optimization ---"

# Detect CPU cores
CPU_CORES=$(nproc)
note "Detected $CPU_CORES CPU cores"

# Jetson platform special handling
if grep -q "NVIDIA" /proc/device-tree/model 2>/dev/null; then
    info "Detected NVIDIA Jetson platform"
    note "Recommend setting maximum performance mode:"
    echo "  sudo nvpmodel -m 0"
    echo "  sudo jetson_clocks"
fi

# RK3588 platform special handling
if grep -q "RK3588\|Rockchip" /proc/device-tree/model 2>/dev/null; then
    info "Detected Rockchip RK3588 platform"
    export MAKEFLAGS="-j$CPU_CORES"
    note "Set parallel compilation: MAKEFLAGS=-j$CPU_CORES"
fi

# Raspberry Pi platform special handling
if grep -q "Raspberry Pi" /proc/device-tree/model 2>/dev/null; then
    info "Detected Raspberry Pi platform"
    # Pi 5 has more cores
    if [ "$CPU_CORES" -ge 4 ]; then
        note "High-performance Raspberry Pi detected"
    fi
fi

# ─────────────────────────────────────────────
# 5. Execute Installation
# ─────────────────────────────────────────────
echo ""
echo "--- Starting Installation ---"

# Call main installation script
export BEST_PYTHON
export REQUIREMENTS_FILE
cd "$(dirname "$0")"
./setup.sh

echo ""
info "Installation complete!"
echo ""
echo "=========================================="
echo "  Platform: $DISTRO_NAME $DISTRO_VERSION"
echo "  Python: $BEST_PYTHON_VERSION"
echo "  Dependencies: $(basename $REQUIREMENTS_FILE)"
echo "=========================================="
echo ""
echo "To start the server:"
echo "  cd $PROJECT_DIR"
echo "  $BEST_PYTHON main.py"
echo ""
