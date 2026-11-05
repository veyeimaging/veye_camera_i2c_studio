# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.3.0] - 2026-11-05

### Added
- **Smart Installation Strategy**: Intelligent three-tier fallback mechanism in `setup.sh`
  - Attempt 1: Prefer pre-compiled wheel packages (fastest, no compilation needed)
  - Attempt 2: Standard installation with automatic compilation fallback
  - Attempt 3: Alternative mirror source (Aliyun/Tsinghua based on region)
  - Ensures maximum compatibility across different platforms and environments

### Changed
- **Setup Script Enhancement**: Improved dependency installation reliability
  - Added `--only-binary=:all:` and `--prefer-binary` for initial attempts
  - Automatic fallback to compilation if pre-compiled packages unavailable
  - Better error handling and user feedback during installation
  - Optimized for resource-constrained devices (Raspberry Pi, etc.)

### Fixed
- **ARM64 Compilation Issues**: Resolved `httptools` and `uvloop` build failures
  - Pre-compiled wheels now preferred, avoiding local compilation
  - Fallback strategy ensures installation success even when wheels unavailable
  - Tested on Raspberry Pi 5 (aarch64) with Python 3.9

### Technical Details
- Modified installation commands in `setup.sh`:
  - Primary: `--only-binary=:all: --prefer-binary`
  - Secondary: `--no-binary=none` (allow compilation)
  - Tertiary: Alternative mirror with `--prefer-binary`

---

## [0.2.0] - 2026-11-03

### Added
- **MV/RAW Series Support**: Full web register access for MV and RAW series cameras
  - 88 MV series registers defined in `config/mv_register.json`
  - 76 MV commands across 11 command groups
  - Auto-detection of camera series (GX vs MV/RAW) from sysfs
  - Series-specific command groups and register maps

- **Trigger Mode Capability Filtering**: Dynamic dropdown filtering based on hardware capabilities
  - Trigger mode options filtered by `trgmodecap` (0x0030) register bits
  - Frontend reads capability register and filters enum options accordingly
  - Supports bit-mapped capability checking for flexible hardware feature detection

- **Enhanced Result Display**: Special formatting for specific command types
  - **Exposure Time Range**: Shows max/min exposure time with unit conversion (μs/ms)
  - **Sensor Register Read**: Verifies ready bit (bit 31) and displays actual register value
  - **Temperature Commands**: Shows both Kelvin and Celsius values
  - All special displays support both English and Chinese languages

- **Command Organization Improvements**
  - BLC Mode and Black Level moved from Advanced Debug to ISP Processing group
  - Exposure Time Range moved from Advanced Debug to Exposure & Gain group
  - ROI Configuration placed above Frame Rate in video modes

### Changed
- **Version Format**: L version now displays in hex format (e.g., "F3.20" instead of "243.20")
- **Command Generation**: Refactored `generate_commands.py` to support multiple camera series
  - Added `--series` argument (gx or mv)
  - Separate command builders for GX and MV series
  - Series-specific wiki URLs and register definitions

- **API Endpoints**: All command APIs now accept `series` parameter
  - `/api/commands?series=mv` for MV series commands
  - `/api/commands/groups?series=mv` for MV series groups
  - `/api/commands/{id}?series=mv` for specific MV commands

### Fixed
- **Async Function Handling**: Fixed `renderOpPanel` to properly handle async capability reading
- **I2C Configuration**: Fixed capability filter to use `getEffectiveI2c()` instead of undefined state properties
- **Cache Busting**: Updated JS version parameter to force browser cache refresh

### Files Added
- `config/mv_commands.json` - MV series command definitions (76 commands)
- `config/mv_command_groups.json` - MV series command group definitions (11 groups)
- `config/gx_commands.json` - GX series command definitions (renamed from commands.json)
- `config/gx_command_groups.json` - GX series command group definitions

### Files Modified
- `scripts/generate_commands.py` - Added MV series command builder
- `scripts/patch_execution_steps.py` - Added MV series execution steps
- `app/static/app.js` - Added series support, capability filtering, enhanced displays
- `app/api/commands.py` - Added series parameter support
- `app/api/devices.py` - Added series detection from sysfs
- `app/services/command_service.py` - Added series-aware command execution
- `app/services/probe_service.py` - Added series detection and version format fix
- `config/mv_register.json` - MV series register definitions (88 registers)
- `config/i18n.json` - Added series-related translations
- `app/templates/index.html` - Added series display badge

---

## [0.1.3] - 2026-11-03

### Added
- **Rockchip Platform Support**: Full compatibility with Rockchip RK3588 platform
  - Verified on Orange Pi CM5 with Ubuntu 22.04 (aarch64)
  - Platform detection via `/proc/device-tree/compatible`
  - Camera probe functionality tested with VEYE GXC-MIPI-IMX662
  - I2C communication validated on `/dev/i2c-5`

### Fixed
- **TemplateResponse API Compatibility**: Fixed `TypeError` with newer Starlette versions
  - Updated `Jinja2Templates.TemplateResponse()` call in `main.py`
  - Changed from keyword arguments to positional arguments for compatibility
  - Resolves "Internal Server Error" when accessing web interface

### Tested Platforms
- ✅ Nvidia Jetson (original platform)
- ✅ Raspberry Pi 5 (Debian 13 / aarch64)
- ✅ Rockchip RK3588 (Orange Pi CM5 / Ubuntu 22.04)

---

## [0.1.2] - 2026-11-02

### Added
- **Raspberry Pi 5 Support**: Full compatibility with Raspberry Pi 5 (aarch64)
  - Enhanced platform detection to identify Raspberry Pi 5 via `/proc/cpuinfo` Model field
  - Verified I2C communication and camera probe functionality on RPi5
  - Tested with VEYE GX camera series on Raspberry Pi 5

### Fixed
- **FastAPI Compatibility**: Updated `TemplateResponse` API call for compatibility with Starlette 1.10.0+
  - Changed positional arguments to keyword arguments in `main.py`
  - Resolved `TypeError: unhashable type: 'dict'` error

- **Platform Detection**: Improved Raspberry Pi 5 detection logic
  - Added check for "raspberry pi 5" in `/proc/cpuinfo` Model field
  - Maintains backward compatibility with bcm2712 chipset detection

### Changed
- **Dependencies**: Updated to use pre-compiled ARM64 wheel packages
  - `pydantic-core` 2.50.2 (aarch64 wheel)
  - `fastapi` 0.162.0
  - `uvicorn` 0.54.0
  - No compilation required on ARM64 platforms

### Tested Platforms
- ✅ Nvidia Jetson (original platform)
- ✅ Raspberry Pi 5 (Debian 13 / aarch64)
- ✅ Python 3.13

---

## [0.1.1] - Previous Release

### Initial Features
- Web-based VEYE camera management tool
- 108 register commands for GX/GXC series cameras
- I2C read/write operations via compiled C tools
- Bilingual support (Chinese/English)
- Dark/Light theme switching
- Auto camera detection and probe scripts
- FastAPI backend with Uvicorn server

### Supported Platforms
- Nvidia Jetson (tested)
- Raspberry Pi (scripts included but not fully tested)
- Rockchip (scripts included but not fully tested)

---

## Version Guidelines

- **Major version** (x.0.0): Breaking changes or major architecture updates
- **Minor version** (0.x.0): New features, significant improvements
- **Patch version** (0.0.x): Bug fixes, platform support, minor improvements

## Platform Support Status

| Platform | Status | Notes |
|----------|--------|-------|
| Nvidia Jetson | ✅ Full Support | Original development platform |
| Raspberry Pi 5 | ✅ Full Support | Tested with Debian 13 (aarch64) |
| Raspberry Pi 4 | ⚠️ Untested | Scripts available, needs validation |
| Rockchip RK3588 | ✅ Full Support | Tested on Orange Pi CM5 |

[0.3.0]: https://github.com/yourusername/veye_camera_i2c_studio/compare/v0.2.0...v0.3.0
[0.2.0]: https://github.com/yourusername/veye_camera_i2c_studio/compare/v0.1.3...v0.2.0
[0.1.3]: https://github.com/yourusername/veye_camera_i2c_studio/compare/v0.1.2...v0.1.3
[0.1.2]: https://github.com/yourusername/veye_camera_i2c_studio/compare/v0.1.1...v0.1.2
[0.1.1]: https://github.com/yourusername/veye_camera_i2c_studio/releases/tag/v0.1.1
