# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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

[0.1.3]: https://github.com/yourusername/veye_camera_i2c_studio/compare/v0.1.2...v0.1.3
[0.1.2]: https://github.com/yourusername/veye_camera_i2c_studio/compare/v0.1.1...v0.1.2
[0.1.1]: https://github.com/yourusername/veye_camera_i2c_studio/releases/tag/v0.1.1
