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
echo "  VEYE Camera I2C Web Studio - Setup"
echo "=========================================="
echo ""

# ─────────────────────────────────────────────
# Configure pip mirror for faster installation
# ─────────────────────────────────────────────
# Auto-detect region, or force via REGION environment variable
# REGION=cn for China mirrors, REGION=global for official PyPI

# Measure how fast a host is reachable (seconds); prints 999 on failure/timeout.
probe_latency() {
    local url="$1" timeout="${2:-5}" t
    t=$(curl -s -o /dev/null -m "$timeout" -w '%{time_total}' "$url" 2>/dev/null) || t=999
    case "$t" in
        ''|*[!0-9.]*) t=999 ;;
    esac
    echo "$t"
}

setup_pip_mirror() {
    local region="${REGION:-auto}"
    
    if [ "$region" = "auto" ]; then
        # Timezone is only a HINT: many domestic boards ship with a wrong/UTC
        # timezone, so trusting it alone silently picks the slow global PyPI.
        local timezone
        timezone=$(cat /etc/timezone 2>/dev/null \
            || timedatectl show --property=Timezone --value 2>/dev/null \
            || echo "")
        if [[ "$timezone" == *"Shanghai"* ]] || [[ "$timezone" == *"Chongqing"* ]] || [[ "$timezone" == *"Asia/Hong"* ]]; then
            region="cn"
            REGION_SOURCE="timezone"
        elif command -v curl &>/dev/null; then
            # Otherwise decide by real reachability, not the (possibly wrong) clock.
            echo "  Probing mirror latency (network check)..."
            local t_cn t_global
            t_cn=$(probe_latency "https://pypi.tuna.tsinghua.edu.cn/simple/")
            t_global=$(probe_latency "https://pypi.org/simple/")
            if awk -v c="$t_cn" -v g="$t_global" 'BEGIN{exit !(c+0 <= g+0)}'; then
                region="cn"
            else
                region="global"
            fi
            REGION_SOURCE="latency probe (CN=${t_cn}s, Global=${t_global}s)"
        else
            region="global"
            REGION_SOURCE="default (no curl to probe)"
            warn "Cannot auto-detect region; set REGION=cn for a domestic board"
        fi
    fi
    
    case "$region" in
        cn|china|CN)
            PIP_INDEX_URL="https://pypi.tuna.tsinghua.edu.cn/simple"
            PIP_TRUSTED_HOST="pypi.tuna.tsinghua.edu.cn"
            PIP_ALT_INDEX_URL="https://mirrors.aliyun.com/pypi/simple/"
            PIP_ALT_TRUSTED_HOST="mirrors.aliyun.com"
            PIP_ALT_NAME="Aliyun"
            REGION_NAME="China (Tsinghua Mirror)"
            ;;
        *)
            PIP_INDEX_URL="https://pypi.org/simple"
            PIP_TRUSTED_HOST="pypi.org"
            PIP_ALT_INDEX_URL="https://pypi.tuna.tsinghua.edu.cn/simple"
            PIP_ALT_TRUSTED_HOST="pypi.tuna.tsinghua.edu.cn"
            PIP_ALT_NAME="Tsinghua"
            REGION_NAME="Global (Official PyPI)"
            ;;
    esac
    
    echo "  Region: $REGION_NAME${REGION_SOURCE:+ [$REGION_SOURCE]}"
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
    # Upgrading pip is best-effort: on flaky connections the downloaded wheel can
    # be truncated ("hashes do not match"), which must NOT abort setup. The venv's
    # bundled pip is fully usable, so tolerate failures here.
    if ! "$PIP_CMD" install --quiet --upgrade pip \
        --index-url "$PIP_INDEX_URL" \
        --trusted-host "$PIP_TRUSTED_HOST" \
        --timeout 60 --retries 5 2>/dev/null; then
        warn "pip upgrade skipped (network/hash check failed); continuing with bundled pip ($("$PIP_CMD" --version | awk '{print $2}'))"
    fi
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
    
    # Try 1: Prefer pre-compiled wheels (faster, no compilation needed)
    echo "  [Attempt 1/3] Trying pre-compiled packages (recommended)..."
    if $PIP_CMD install -r "$PROJECT_DIR/requirements.txt" \
        --index-url "$PIP_INDEX_URL" \
        --trusted-host "$PIP_TRUSTED_HOST" \
        --timeout 60 --retries 5 \
        --only-binary=:all: \
        --prefer-binary \
        $($USE_VENV || echo "--break-system-packages --user") 2>/dev/null; then
        info "Dependencies installed (pre-compiled)"
    else
        # Try 2: Fallback to normal installation (may compile if needed)
        warn "Pre-compiled packages not available, trying standard installation..."
        echo "  [Attempt 2/3] Standard installation with compilation fallback..."
        if $PIP_CMD install -r "$PROJECT_DIR/requirements.txt" \
            --index-url "$PIP_INDEX_URL" \
            --trusted-host "$PIP_TRUSTED_HOST" \
            --timeout 60 --retries 5 \
            --no-binary=none \
            $($USE_VENV || echo "--break-system-packages --user") 2>/dev/null; then
            info "Dependencies installed (compiled locally)"
        else
            # Try 3: Alternative mirror
            warn "Standard installation failed, trying alternative mirror..."
            echo "  [Attempt 3/3] Trying alternative mirror ($PIP_ALT_NAME)..."
            $PIP_CMD install -r "$PROJECT_DIR/requirements.txt" \
                --index-url "$PIP_ALT_INDEX_URL" \
                --trusted-host "$PIP_ALT_TRUSTED_HOST" \
                --timeout 60 --retries 5 \
                --prefer-binary \
                $($USE_VENV || echo "--break-system-packages --user") \
                || fail "Failed to install dependencies from $PIP_ALT_NAME mirror"
            info "Dependencies installed (alternative mirror)"
        fi
    fi
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
# 5b. Ensure the current user can access /dev/i2c-*
# ─────────────────────────────────────────────
# I2C device nodes are owned by root:i2c with mode 0660 on Debian/Ubuntu-based
# boards (Rockchip/Jetson images included). A user outside the i2c group cannot
# open them, so every register read/write fails with an unhelpful empty error.
ensure_i2c_group() {
    echo ""
    echo "--- Checking I2C access ---"
    local user="${SUDO_USER:-$USER}"

    if id -nG "$user" 2>/dev/null | tr ' ' '\n' | grep -qx i2c; then
        info "User '$user' is already in the i2c group"
        return 0
    fi

    if ! getent group i2c >/dev/null 2>&1; then
        warn "No 'i2c' group on this system; skipping (run the server as root if needed)"
        return 0
    fi

    local SUDO="sudo"
    command -v sudo >/dev/null 2>&1 || SUDO=""
    if [ -z "$SUDO" ] && [ "$(id -u)" != "0" ]; then
        warn "Cannot change group membership (no sudo, not root)."
        warn "Manual: sudo usermod -aG i2c $user  (then re-login)"
        return 0
    fi

    echo "  Adding '$user' to the i2c group..."
    if $SUDO usermod -aG i2c "$user" 2>/dev/null; then
        info "Added '$user' to the i2c group"
        warn "Group membership applies only in a NEW login session."
        warn "  -> Reconnect SSH (or reboot), then relaunch: ./setup.sh --start"
        warn "  -> Or apply it in this shell right now:      newgrp i2c"
    else
        warn "Could not auto-add. Manual: sudo usermod -aG i2c $user  (then re-login)"
    fi
}

# ─────────────────────────────────────────────
# 6. Live Preview capture/streaming dependencies (best-effort)
# ─────────────────────────────────────────────
# Live Preview (GX UYVY + MV GREY) runs:
#   v4l2src -> videoconvert -> jpegenc -> multipartmux   (via gst-launch-1.0)
# and configures the sensor with v4l2-ctl / media-ctl.  The MV/GREY path uses
# the SAME plugins as GX (videoconvert in plugins-base, jpegenc+multipartmux in
# plugins-good), so this covers both series with no extra GStreamer package.
# Installing these is NON-FATAL: the studio's I2C control works without them;
# only the web Live Preview needs them.
ensure_capture_deps() {
    local need_install=false
    for bin in gst-launch-1.0 v4l2-ctl media-ctl; do
        command -v "$bin" &>/dev/null || need_install=true
    done
    if ! $need_install; then
        info "Live Preview capture tools already present"
        return 0
    fi
    local CAPTURE_PKGS=(
        gstreamer1.0-tools
        gstreamer1.0-plugins-base
        gstreamer1.0-plugins-good
        v4l-utils
    )
    if ! command -v apt-get &>/dev/null; then
        warn "apt-get not found; for Live Preview install manually: ${CAPTURE_PKGS[*]}"
        return 0
    fi
    echo "  Installing Live Preview capture/streaming packages..."
    local SUDO=""
    if command -v sudo &>/dev/null; then SUDO="sudo -n"; fi
    # shellcheck disable=SC2086
    $SUDO apt-get update -y 2>/dev/null \
        || warn "apt-get update needs sudo/password; skipped"
    # shellcheck disable=SC2086
    $SUDO apt-get install -y "${CAPTURE_PKGS[@]}" 2>/dev/null \
        || warn "Could not auto-install capture deps. Manual: sudo apt install ${CAPTURE_PKGS[*]}"
    for bin in gst-launch-1.0 v4l2-ctl media-ctl; do
        if command -v "$bin" &>/dev/null; then
            info "$bin available"
        else
            warn "$bin missing - Live Preview unavailable until installed"
        fi
    done
}
ensure_capture_deps || true
ensure_i2c_group || true

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
