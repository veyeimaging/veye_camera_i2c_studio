# VEYE Camera I2C Studio

**English** | [中文](README.md)

A web-based tool for managing and debugging VEYE cameras. Perform register-level read/write operations directly from your browser.

> **v0.2.0 Release** — Supports Jetson, Raspberry Pi 5, and Rockchip platforms. Supports both GX/GXC series and MV/RAW series cameras.

## Features

- Automatic detection of connected VEYE cameras (GX/GXC series and MV/RAW series)
- GX series: 108 register commands covering all configurable camera parameters
- MV/RAW series: 76 register commands with sensor register read support
- Register read/write with support for multiple parameter types (numeric, enumerated, bitfield)
- Command group browsing and search
- Bilingual interface (English / Chinese)
- Dark / light theme toggle
- Automatic feature filtering based on camera series (e.g., trigger modes)

## Project Structure

```
veye_camera_i2c_studio/
├── gx_i2c_tools/                   # GX/GXC series camera I2C toolset
│   ├── gx_mipi_i2c.sh             # Command-line I2C read/write script
│   ├── i2c_functions.sh           # I2C function library
│   ├── i2c_vread / i2c_vwrite     # Pre-compiled binary tools
│   └── source/                    # C source code
├── mv_i2c_tools/                   # MV/RAW series camera I2C toolset
│   ├── mv_mipi_i2c.sh             # Command-line I2C read/write script
│   ├── lut_rw                     # LUT read/write tool
│   ├── i2c_4read / i2c_4write     # Pre-compiled binary tools
│   └── sources/                   # C source code
├── veye_camera_web_studio/         # Web server main application
│   ├── main.py                    # FastAPI entry point (v0.2.0)
│   ├── app/
│   │   ├── adapters/              # Platform adapters
│   │   │   └── jetson/            # Jetson platform adapter
│   │   ├── api/                   # API routes
│   │   │   ├── devices.py         # Camera probe & series detection
│   │   │   └── commands.py        # Register command execution
│   │   ├── services/              # Business logic layer
│   │   │   ├── command_service.py     # Register read/write execution
│   │   │   ├── probe_service.py       # Camera probe & series detection
│   │   │   ├── documentation_service.py # Documentation service
│   │   │   ├── system_service.py      # System information
│   │   │   └── log_service.py         # Operation logs
│   │   ├── static/                # Frontend static files
│   │   │   ├── app.js
│   │   │   ├── style.css
│   │   │   └── logo*.png
│   │   └── templates/             # HTML templates
│   │       └── index.html
│   ├── config/                    # Configuration files
│   │   ├── gx_commands.json       # GX series 108 command definitions
│   │   ├── gx_command_groups.json # GX command groups
│   │   ├── gx_register.json       # GX register reference data
│   │   ├── mv_commands.json       # MV series 76 command definitions
│   │   ├── mv_command_groups.json # MV command groups
│   │   ├── mv_register.json       # MV register reference data
│   │   ├── default_i2c.json       # Default I2C configuration
│   │   └── i18n.json              # Internationalization
│   ├── tools/                     # I2C tools & probe scripts
│   │   ├── i2c_vread / i2c_vwrite     # GX series tools (compiled)
│   │   ├── i2c_4read / i2c_4write     # MV series tools (compiled)
│   │   ├── source/                # C source (gx/ and mv/ subdirs)
│   │   └── probe/                 # Platform probe scripts
│   ├── scripts/                   # Helper scripts
│   │   ├── generate_commands.py   # Command config generator
│   │   ├── patch_execution_steps.py # Execution step patches
│   │   └── update_script_functions.py
│   ├── requirements.txt           # Python dependencies
│   └── RELEASE.md                 # Release notes
├── for_reference/                  # Reference materials (register manuals)
├── setup.sh                        # Installation and launch script
├── CHANGELOG.md                    # Version history
└── README.md / README.en.md        # Project documentation
```

## I2C Toolset

### gx_i2c_tools - GX/GXC Series Tools

The `gx_i2c_tools/` directory contains universal I2C read/write tools for GX/GXC series cameras on embedded platforms:

- **gx_mipi_i2c.sh** — Command-line script for direct register read/write
- **i2c_functions.sh** — I2C operation function library
- **source/** — C source code, compilable to binary tools

For detailed documentation, see: [Gx_mipi_i2c.sh User Guide](https://wiki.veye.cc/index.php/Gx_mipi_i2c.sh_user_guide)

### mv_i2c_tools - MV/RAW Series Tools

The `mv_i2c_tools/` directory contains I2C read/write tools for MV/RAW series cameras:

- **mv_mipi_i2c.sh** — Command-line script for register read/write and LUT configuration
- **lut_rw** — LUT (Look-Up Table) read/write tool
- **sources/** — C source code

#### Usage Examples

```bash
# GX series: Read camera manufacturer info
./gx_i2c_tools/gx_mipi_i2c.sh -r manufacturer

# GX series: Write factory default parameters
./gx_i2c_tools/gx_mipi_i2c.sh -w factoryparam

# MV series: Read camera version
./mv_i2c_tools/mv_mipi_i2c.sh -r version

# MV series: Read sensor register
./mv_i2c_tools/mv_mipi_i2c.sh -r snsreg
```

## Architecture

```
Browser (HTML + JS + CSS)
    ↕  HTTP / JSON
FastAPI (Python)
    ↕  System calls
i2c_vread / i2c_vwrite (GX series C tools)
i2c_4read / i2c_4write (MV series C tools)
    ↕  I2C bus
Camera hardware (GX/GXC or MV/RAW series)
```

- **Backend**: Python 3 + FastAPI + Uvicorn
- **Frontend**: Vanilla JavaScript, no framework dependencies
- **Hardware communication**: Direct I2C bus access via compiled binary tools
- **Series detection**: Automatic camera series detection via sysfs (GX or MV/RAW)

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

- **Jetson**, **Raspberry Pi 5**, and **Rockchip** are fully tested
- Other Raspberry Pi versions and platforms need further validation
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
