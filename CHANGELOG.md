# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.4.1] - 2026-11-13

### Added
- **Automatic hardware MJPEG encoder selection per platform**: the Stage-1 provider now owns "which element encodes JPEG", driven by two class attributes (`JPEG_ENCODER_PREFERENCE`, `HW_JPEG_INPUT_FORMATS`) plus a cached `gst-inspect-1.0` probe
  - On Rockchip, GX/UYVY streams now run `v4l2src ! mppjpegenc rc-mode=fixqp q-factor=<quality> ! multipartmux` straight off the capture dmabuf - no `videoconvert`, no copy. Measured 1080p: 53.8 fps at quality 60 (78 KB/frame) vs 29.4 fps for the CPU path at quality 85
  - Jetson / Raspberry Pi / unknown platforms resolve to exactly the previous `videoconvert ! video/x-raw,format=I420 ! jpegenc` pipeline (verified by dumping the built argv per platform), and MV/GRAY8 stays on the CPU path because MPP does not accept it as input
- **`encoder` request field on `/api/stream/start`**: `"jpeg"` (default) lets the platform pick its fastest usable encoder, `"jpeg_sw"` forces the portable CPU encoder for A/B testing and fallbacks
- **Encoder visibility**: `/api/stream/{id}/status` reports the element actually encoding (`mppjpegenc` / `jpegenc`), `/api/stream/capabilities` reports `provider.jpeg_encoder_auto` and per-encoder availability, and both the popup preview page and the inline status line show it next to resolution/fps
- **Startup failure is now reported instead of hanging**: the first 1.5 s after launch is probed with `select()`, so a pipeline that dies during caps negotiation makes `/start` return HTTP 400 with the real GStreamer reason, while a successful start still returns in ~0.3 s
- **Post-mortem status for finished streams**: the last state of the 8 most recent streams is kept, so polling a stream the consumer already dropped answers 200 with `gone: true` plus the exit reason instead of a bare 404

### Fixed
- **Rockchip live preview died instantly with `not-negotiated (-4)`**: capture caps no longer carry `framerate=`. Rockchip `rkcif` advertises only 1-30 fps in `VIDIOC_ENUM_FRAMEINTERVALS` (a `S_FMT` limit, not a transport limit), so asking for 60/1 in the caps rejected an otherwise healthy 1080p60 stream. Frame rate is owned by Stage 0 only - the I2C fps register and the `@1/fps` on the sensor pad
- **GX video-mode capability misdetection**: `VideoModeCap` (0x005C) is now evaluated by its ROI/Preset bits instead of being returned as a raw register value; a value such as 60 previously masqueraded as a capability and skipped the `videomode` write
- **Silent preview failures**: when the pipeline process exits on its own the stream now moves to `state=error`, reporting `alive`, `exit_code` and the parsed stderr reason (keyword table picks the specific "reason ..." line over GStreamer's generic `Internal data stream error.`), and stderr can no longer fill up unnoticed
- **Frontend no longer polls a dead stream forever**: a 404, a `alive: false` status, or the popup window ending stops the poll and shows "Preview process exited: <reason>"; five consecutive zero-fps polls raise a separate "running, but no frames received yet" hint; new i18n keys `stream.status_died` / `stream.status_noframes`
- **Executable bits restored** on `setup.sh` and the four `tools/probe/probe_camera_info-*.sh` scripts (were committed 644)

### Files Modified
- `veye_camera_web_studio/app/streaming/providers/base.py` - encoder preference/probe machinery, `needs_cpu_convert()`, richer `capabilities()`
- `veye_camera_web_studio/app/streaming/providers/rockchip.py` - `mppjpegenc` opt-in with `rc-mode=fixqp` quality mapping
- `veye_camera_web_studio/app/streaming/providers/jetson.py` - skips the converter when a hardware encoder is selected
- `veye_camera_web_studio/app/streaming/transports/{base,mjpeg}.py` - `sink_tokens(profile, provider)` so the transport frames whatever encoder the platform chose
- `veye_camera_web_studio/app/streaming/pipeline.py` - no dangling `!` when the provider contributes no converter stage
- `veye_camera_web_studio/app/streaming/profile.py` - caps without `framerate`, new `encoder` / `encoder_element` fields
- `veye_camera_web_studio/app/services/stream_service.py` - startup probe, error extraction, finished-stream tombstones, encoder resolution
- `veye_camera_web_studio/app/services/command_service.py` - `VideoModeCap` bit test
- `veye_camera_web_studio/app/api/stream.py` - `encoder` field, 404 detail carries the death reason
- `veye_camera_web_studio/app/static/app.js`, `app/templates/preview.html`, `config/i18n.json` - stopped/died handling, encoder display, new strings
- `setup.sh`, `veye_camera_web_studio/tools/probe/probe_camera_info-*.sh` - mode 644 -> 755

### Tested On
- Orange Pi CM5 (Rockchip, 8-core, Ubuntu 22.04 aarch64) with VEYE GX MIPI 1080p camera - preset and ROI modes, 30/60 fps, quality 60-85
- Pipeline assembly regression-checked for Jetson, Raspberry Pi 4/5 and unknown platforms

---

## [0.4.0] - 2026-11-13

### Added
- **Live Preview (MJPEG over HTTP)**: New real-time preview subsystem supporting both the GX series (UYVY) and the MV/RAW series (8-bit GREY)
  - Four-layer architecture under `app/streaming/`: Stage-0 Configurator (per-platform `media-ctl`/`v4l2-ctl`/`config_camera-rpi5.sh` setup for Jetson, Raspberry Pi (4/5), Rockchip RK3588), Stage-1 Provider (format conversion), Stage-2 Transport (MJPEG multipart stream), Stage-3 `StreamService` (pipeline lifecycle, device-exclusive ownership, teardown on disconnect)
  - New `/api/stream` router (capabilities / configure / start / stop / status) with clean pipeline shutdown on app exit
  - Standalone `GET /preview` page is the single MJPEG consumer (popup window), with an inline fallback when the popup is blocked
  - Server-side measured framerate (rolling 1-second window) surfaced in the preview UI
  - Non-fatal `ensure_capture_deps` step in `setup.sh` installs GStreamer + v4l-utils for GX/MV capture (warns but does not abort when `sudo` is unavailable)
- **Live Preview prefills current ROI + framerate**: The panel now reads the camera's actual ROI (offset X/Y, width, height) and frame rate and fills them into the controls instead of always defaulting to 1920x1080@30
  - Applies to MV/RAW (always ROI) and to GX in ROI mode (VideoModeCap = 1); GX preset cameras continue to be driven by the preset selector

### Fixed
- **MV/GX Live Preview ROI default**: The preview panel no longer shows a fixed 1920x1080@30; it reads the live `roi` registers (0x0820/0x0824/0x0818/0x081C -> X/Y/W/H) and `fps` (MV 0x0814/100, GX 0x0850/10000) and prefills width/height/fps/ROI offsets

### Files Modified
- `veye_camera_web_studio/app/streaming/` - New four-layer live-preview subsystem (configurators / providers / transports / util)
- `veye_camera_web_studio/app/services/stream_service.py` - Stage-3 orchestration + `read_current_picture()` ROI/fps prefill
- `veye_camera_web_studio/app/api/stream.py` - New `/api/stream` router
- `veye_camera_web_studio/app/templates/preview.html` - Standalone MJPEG popup consumer
- `veye_camera_web_studio/app/static/app.js` - Live Preview panel, capability detection, ROI/fps prefill
- `veye_camera_web_studio/app/static/style.css` - Live Preview panel styles
- `veye_camera_web_studio/main.py` - Registers stream router + lifespan shutdown; version bump to 0.4.0
- `setup.sh` - Added `ensure_capture_deps` (GStreamer + v4l-utils, non-fatal)
- `veye_camera_web_studio/app/templates/index.html` - Version display and cache busting update

---

## [0.3.1] - 2026-11-07

### Added
- **Trigger & Sync Page Workmode Filtering**: Automatically filter displayed registers based on current work mode
  - Reads current workmode on page entry and shows a banner indicator
  - **Video Streaming mode (0)**: Only shows workmode register
  - **Trigger mode (1)**: Hides slavemode register
  - **Pulse Trigger mode (3)**: Hides slavemode, trigger delay, trigger interval, and trigger frame count
  - **Multi-camera Sync mode (4)**: Only shows workmode and slavemode registers
  - Auto-refreshes the command list when workmode is changed
  - Supports both GX and MV series with mode-specific filtering logic

### Changed
- **Slow Shutter Command Overhaul**:
  - Renamed parameter 1 from "Enable" (Disable/Enable) to "Mode" (Fixed Frame Rate / Auto Frame Reduction)
  - Removed gain threshold parameter max limit (was 409.5 dB, now unlimited)
  - Updated documentation with comprehensive feature description including AE strategy details
  - Added register info (0x0CBC, 0x0CC0) back to notes
  - Notes now support multi-line display (`white-space: pre-wrap`)
- **Workmode Naming**: Renamed "脉冲触发" (Pulse Trigger) to "电平触发" (Pulse Trigger Mode) for mode 3
- **Slow Shutter Read Display**: Fixed gain threshold display - now shows correct dB value (register / 10) instead of raw register value

### Fixed
- **Slow Shutter Parameter Validation**: Setting gain threshold to values above 409.5 no longer fails
- **Slow Shutter Read-back**: Reading after writing 600 dB now correctly displays 600 dB (was showing 6000)
- **Parameter Population**: After reading slowshutter, input field correctly populates with 600 instead of raw value 6000

### Files Modified
- `veye_camera_web_studio/app/static/app.js` - Added trigger_sync filtering, workmode banner, slowshutter display fix
- `veye_camera_web_studio/app/static/style.css` - Added `white-space: pre-wrap` for notes, workmode banner styles
- `veye_camera_web_studio/config/gx_commands.json` - Updated slowshutter and workmode definitions
- `veye_camera_web_studio/scripts/generate_commands.py` - Updated slowshutter and workmode source definitions
- `veye_camera_web_studio/main.py` - Version bump to 0.3.1
- `veye_camera_web_studio/app/templates/index.html` - Version display and cache busting update
---

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

[0.4.1]: https://github.com/yourusername/veye_camera_i2c_studio/compare/v0.4.0...v0.4.1
[0.4.0]: https://github.com/yourusername/veye_camera_i2c_studio/compare/v0.3.1...v0.4.0
[0.3.1]: https://github.com/yourusername/veye_camera_i2c_studio/compare/v0.3.0...v0.3.1
[0.3.0]: https://github.com/yourusername/veye_camera_i2c_studio/compare/v0.2.0...v0.3.0
[0.2.0]: https://github.com/yourusername/veye_camera_i2c_studio/compare/v0.1.3...v0.2.0
[0.1.3]: https://github.com/yourusername/veye_camera_i2c_studio/compare/v0.1.2...v0.1.3
[0.1.2]: https://github.com/yourusername/veye_camera_i2c_studio/compare/v0.1.1...v0.1.2
[0.1.1]: https://github.com/yourusername/veye_camera_i2c_studio/releases/tag/v0.1.1
