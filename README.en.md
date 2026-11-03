# VEYE Camera I2C Studio

**English** | [中文](README.md)

A web-based tool for managing and debugging VEYE cameras. Perform register-level read/write operations directly from your browser.

> **v0.1.3 Beta Release** — Supports Jetson, Raspberry Pi 5, and Rockchip platforms. Only GX/GXC series cameras are supported.

## Features

- Automatic detection of connected VEYE GX/GXC series cameras
- 108 register commands covering all configurable camera parameters
- Register read/write with support for multiple parameter types (numeric, enumerated)
- Command group browsing and search
- Bilingual interface (English / Chinese)
- Dark / light theme toggle

## Project Structure

```
veye_camera_i2c_studio/
├── gx_i2c_tools/                # GX/GXC series camera I2C toolset
│   ├── gx_mipi_i2c.sh          # Command-line I2C read/write script
│   ├── i2c_functions.sh        # I2C function library
│   └── source/                 # C source code
│       ├── i2c_vread.c         # I2C read tool source
│       ├── i2c_vwrite.c        # I2C write tool source
│       ├── i2c_vcomm.h         # I2C communication header
│       ├── strfunc.c           # String utility functions
│       └── Makefile            # Build configuration
├── veye_camera_web_studio/      # Web server main application
│   ├── main.py                 # FastAPI entry point
│   ├── app/
│   │   ├── api/                # API routes
│   │   │   ├── devices.py      # Camera probe endpoints
│   │   │   └── commands.py     # Register command endpoints
│   │   ├── services/           # Business logic
│   │   │   ├── command_service.py  # Register read/write execution
│   │   │   ├── probe_service.py    # Camera detection
│   │   │   ├── system_service.py   # System information
│   │   │   └── log_service.py      # Operation logs
│   │   ├── static/             # Frontend static files
│   │   │   ├── app.js
│   │   │   └── style.css
│   │   └── templates/          # HTML templates
│   │       └── index.html
│   ├── config/
│   │   ├── commands.json       # 108 register command definitions
│   │   ├── command_groups.json # Command group definitions
│   │   ├── i18n.json           # Internationalization strings
│   │   └── gx_register.json    # GX register reference data
│   ├── tools/                  # I2C tools (compiled binaries)
│   │   ├── i2c_vread
│   │   └── i2c_vwrite
│   └── scripts/                # Helper scripts
├── for_reference/              # Reference materials
├── setup.sh                    # Installation and launch script
└── README.md / README.en.md    # Project documentation
```

## gx_i2c_tools - I2C Toolset

The `gx_i2c_tools/` directory contains universal I2C read/write tools for GX/GXC series cameras on embedded platforms:

- **gx_mipi_i2c.sh** — Command-line script for direct register read/write
- **i2c_functions.sh** — I2C operation function library
- **source/** — C source code, compilable to binary tools

For detailed documentation, see: [Gx_mipi_i2c.sh User Guide](https://wiki.veye.cc/index.php/Gx_mipi_i2c.sh_user_guide)

### Usage Examples

```bash
# Read camera manufacturer info
./gx_i2c_tools/gx_mipi_i2c.sh -r manufacturer

# Read camera model
./gx_i2c_tools/gx_mipi_i2c.sh -r model

# Write factory default parameters
./gx_i2c_tools/gx_mipi_i2c.sh -w factoryparam
```

## Architecture

```
Browser (HTML + JS + CSS)
    ↕  HTTP / JSON
FastAPI (Python)
    ↕  System calls
i2c_vread / i2c_vwrite (C tools)
    ↕  I2C bus
Camera hardware
```

- **Backend**: Python 3 + FastAPI + Uvicorn
- **Frontend**: Vanilla JavaScript, no framework dependencies
- **Hardware communication**: Direct I2C bus access via compiled `i2c_vread` / `i2c_vwrite` binaries

## Quick Start

### Prerequisites

- Python 3.8+
- GCC (for compiling I2C tools, only needed if pre-compiled packages unavailable)
- Supported platforms:
  - **Nvidia Jetson** (JetPack 4.x/5.x)
  - **Raspberry Pi 5** (Debian 12+/Bookworm, aarch64)
  - Raspberry Pi 4 (experimental support)
  - Rockchip RK3588 (experimental support)

**Raspberry Pi 5 additional dependencies:**
```bash
sudo apt install media-ctl gawk
```

### Installation & Launch

```bash
# Run the setup script (compiles I2C tools, installs Python dependencies)
./setup.sh

# Start the server
cd veye_camera_web_studio
python3 main.py
```

Open `http://localhost:8080` in your browser.

**Note:** On Raspberry Pi 5, if network is slow, you can use a proxy:
```bash
# Install dependencies via proxy (optional)
cd veye_camera_web_studio
.venv/bin/pip install --proxy=http://<PROXY_IP>:<PORT> -i https://pypi.tuna.tsinghua.edu.cn/simple -r requirements.txt
```

### One-Command Launch

```bash
./setup.sh --start
```

## Known Limitations

- Only **GX/GXC series** cameras are supported (MV series not yet adapted)
- **Jetson**, **Raspberry Pi 5**, and **Rockchip** are fully tested
- Requires I2C bus access permissions (may need root or proper udev rules)
- Multiple clients accessing the I2C bus concurrently may cause conflicts

## Platform Compatibility

| Platform | Status | Notes |
|----------|--------|-------|
| Nvidia Jetson | ✅ Full Support | Original development platform |
| Raspberry Pi 5 | ✅ Full Support | Tested with Debian 13 / aarch64 |
| Raspberry Pi 4 | ⚠️ Experimental | Scripts included, needs validation |
| Rockchip RK3588 | ✅ Full Support | Tested on Orange Pi CM5 |

## Changelog

See [CHANGELOG.md](CHANGELOG.md) for detailed version history.

## License

MIT
