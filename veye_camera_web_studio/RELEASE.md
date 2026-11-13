# Release Log

## v0.4.1 (2026-11-13)

### New Features
- **Automatic hardware MJPEG encoder selection**: the platform provider now decides which element encodes JPEG, based on a declared encoder preference + input format list and a cached `gst-inspect-1.0` probe
  - Rockchip + GX/UYVY runs `v4l2src ! mppjpegenc rc-mode=fixqp q-factor=<quality> ! multipartmux`, feeding the encoder from the capture dmabuf with no `videoconvert` and no copy — 1080p measured 53.8 fps at quality 60 (78 KB/frame) versus 29.4 fps on the CPU path at quality 85
  - Jetson / Raspberry Pi / unknown platforms keep the byte-for-byte same pipeline as before (`videoconvert ! video/x-raw,format=I420 ! jpegenc`); MV/GRAY8 also stays on the CPU path since MPP does not take it as input
- **`encoder` field in `/api/stream/start`**: `jpeg` (default) = auto (hardware where available), `jpeg_sw` = force the portable CPU encoder — lets you A/B without touching code
- **Encoder visibility**: stream status reports the encoding element, `/api/stream/capabilities` exposes `provider.jpeg_encoder_auto` and per-encoder availability, and the preview status line shows which encoder is live next to resolution/fps
- **Honest start failures**: the 1.5 s startup window is probed with `select()`, so a pipeline that dies during negotiation returns HTTP 400 with the actual GStreamer reason instead of a stream id that is already dead (successful starts still return in ~0.3 s)
- **Finished streams keep their last status** (most recent 8): polling a stream that already went away answers 200 with `gone: true` plus the reason rather than a bare 404

### Bug Fixes
- Live preview on Rockchip no longer exits immediately with `not-negotiated (-4)`: capture caps dropped `framerate=`. `rkcif` only advertises 1-30 fps in `VIDIOC_ENUM_FRAMEINTERVALS` — an `S_FMT` restriction, not a transport limit — so `60/1` in the caps was rejecting a healthy 1080p60 stream; frame rate is now owned solely by the I2C fps register and the sensor-pad `@1/fps`
- `VideoModeCap` (0x005C) is tested by its ROI/Preset bits instead of being handed back as a raw register value (60 previously looked like a capability and skipped the `videomode` write)
- A pipeline that exits on its own now surfaces as `state=error` with `exit_code` and a parsed stderr reason (the specific `reason not-negotiated (-4)`-style line is preferred over GStreamer's generic `Internal data stream error.`)
- Frontend stops polling dead streams: 404 / `alive: false` / the popup window ending now show "Preview process exited: <reason>"; five consecutive zero-fps polls show "running, but no frames received yet"; the popup reports its end reason back to the main page
- `setup.sh` and the four `tools/probe/probe_camera_info-*.sh` scripts restored to mode 755

### Files Modified
- `app/streaming/providers/base.py` — encoder preference + capability probe machinery, `needs_cpu_convert()`, extended `capabilities()`
- `app/streaming/providers/rockchip.py` — `mppjpegenc` opt-in and `rc-mode=fixqp` quality mapping
- `app/streaming/providers/jetson.py` — converter skipped when a hardware encoder is chosen
- `app/streaming/transports/base.py`, `app/streaming/transports/mjpeg.py` — `sink_tokens(profile, provider)`
- `app/streaming/pipeline.py` — no dangling `!` when there is no converter stage
- `app/streaming/profile.py` — caps without `framerate`; `encoder` / `encoder_element` fields
- `app/services/stream_service.py` — startup probe, stderr cause extraction, finished-stream tombstones, encoder resolution, `encoder` argument
- `app/services/command_service.py` — `VideoModeCap` bit test
- `app/api/stream.py` — `encoder` request field; 404 detail carries the death reason
- `app/static/app.js`, `app/templates/preview.html`, `config/i18n.json` — dead-stream reporting, encoder display, new strings
- `main.py`, `app/templates/index.html` — version bump to 0.4.1 and cache busting
- `../setup.sh`, `tools/probe/probe_camera_info-*.sh` — mode 644 -> 755

### Tested On
- Orange Pi CM5 (Rockchip, Ubuntu 22.04 aarch64) with VEYE GX MIPI 1080p: preset + ROI modes, 30/60 fps, quality 60-85, every delivered frame validated as a standalone JPEG (SOI/APP0-JFIF/DQT/SOF/DHT/SOS/EOI + PIL decode)
- Pipeline assembly verified unchanged for Jetson, Raspberry Pi 4/5 and generic platforms

---

## v0.4.0 (2026-11-13)

### New Features
- **Live Preview (MJPEG over HTTP)**: Real-time preview for the GX series (UYVY) and MV/RAW series (8-bit GREY)
  - Four-layer architecture under `app/streaming/`: Stage-0 Configurator (per-platform media-ctl/v4l2-ctl setup for Jetson, RPi 4/5, RK3588), Stage-1 Provider (format conversion), Stage-2 Transport (MJPEG multipart), Stage-3 StreamService (pipeline lifecycle, device-exclusive ownership, teardown on disconnect)
  - New `/api/stream` router (capabilities / configure / start / stop / status); pipelines shut down cleanly on app exit
  - Standalone `GET /preview` page is the single MJPEG consumer (popup), with an inline fallback when the popup is blocked
  - Server-side measured framerate (rolling 1s window) shown in the preview UI
  - `setup.sh` adds a non-fatal `ensure_capture_deps` step (GStreamer + v4l-utils)
- **Live Preview prefills current ROI + framerate**: the panel reads the camera's live ROI (offset X/Y, width, height) and frame rate and fills them in instead of a fixed 1920x1080@30 (MV/RAW always; GX in ROI mode; preset cameras keep using the preset selector)

### Bug Fixes
- Live Preview no longer defaults to 1920x1080@30 — reads the live ROI (0x0820/0x0824/0x0818/0x081C) and fps (MV 0x0814/100, GX 0x0850/10000) registers to prefill the fields

### Files Modified
- `app/streaming/` — New four-layer live-preview subsystem (configurators / providers / transports / util)
- `app/services/stream_service.py` — Stream orchestration + `read_current_picture()` ROI/fps prefill
- `app/api/stream.py` — New `/api/stream` router
- `app/templates/preview.html` — Standalone MJPEG popup consumer
- `app/static/app.js` — Live Preview panel, capability detection, ROI/fps prefill
- `app/static/style.css` — Live Preview panel styles
- `main.py` — Registers stream router + lifespan shutdown; version bump to 0.4.0
- `../setup.sh` — Added `ensure_capture_deps` (GStreamer + v4l-utils, non-fatal)
- `app/templates/index.html` — Version display and cache busting update

---

## v0.3.1 (2026-11-07)

### New Features
- **Trigger & Sync Page Workmode Filtering**: Automatically filter displayed registers based on current work mode
  - Reads current workmode on page entry and shows a banner indicator
  - Video Streaming mode: Only shows workmode register
  - Trigger mode: Hides slavemode register
  - Pulse Trigger mode: Hides slavemode, trigger delay, trigger interval, and trigger frame count
  - Multi-camera Sync mode: Only shows workmode and slavemode registers
  - Auto-refreshes the command list when workmode is changed
  - Supports both GX and MV series

### Improvements
- **Slow Shutter Command Overhaul**:
  - Renamed parameter 1 from "Enable" to "Mode" (Fixed Frame Rate / Auto Frame Reduction)
  - Removed gain threshold parameter max limit (was 409.5 dB, now unlimited)
  - Updated documentation with comprehensive feature description
  - Notes now support multi-line display
- **Workmode Naming**: Renamed "脉冲触发" to "电平触发" (Pulse Trigger Mode) for mode 3
- **Slow Shutter Read Display**: Fixed gain threshold display — now shows correct dB value instead of raw register value

### Bug Fixes
- Setting gain threshold to values above 409.5 no longer fails
- Reading after writing 600 dB now correctly displays 600 dB (was showing 6000)
- After reading slowshutter, input field correctly populates with converted value

### Files Modified
- `app/static/app.js` — Trigger/sync filtering, workmode banner, slowshutter display fix
- `app/static/style.css` — Notes line-break support, workmode banner styles
- `config/gx_commands.json` — Updated slowshutter and workmode definitions
- `scripts/generate_commands.py` — Updated slowshutter and workmode source definitions
- `main.py` — Version bump to 0.3.1
- `app/templates/index.html` — Version display and cache busting update
---

## v0.3.0 (2026-11-05)

### New Features
- **Smart Installation Strategy**: Intelligent three-tier fallback mechanism in `setup.sh`
  - Attempt 1: Prefer pre-compiled wheel packages (fastest, no compilation needed)
  - Attempt 2: Standard installation with automatic compilation fallback
  - Attempt 3: Alternative mirror source (Aliyun/Tsinghua based on region)
  - Ensures maximum compatibility across different platforms and environments

### Improvements
- **Setup Script Enhancement**: Improved dependency installation reliability
  - Added `--only-binary=:all:` and `--prefer-binary` for initial attempts
  - Automatic fallback to compilation if pre-compiled packages unavailable
  - Better error handling and user feedback during installation
  - Optimized for resource-constrained devices (Raspberry Pi, etc.)

### Bug Fixes
- **ARM64 Compilation Issues**: Resolved `httptools` and `uvloop` build failures
  - Pre-compiled wheels now preferred, avoiding local compilation
  - Fallback strategy ensures installation success even when wheels unavailable
  - Tested on Raspberry Pi 5 (aarch64) with Python 3.9

### Technical Details
- Modified installation commands in `setup.sh`:
  - Primary: `--only-binary=:all: --prefer-binary`
  - Secondary: `--no-binary=none` (allow compilation)
  - Tertiary: Alternative mirror with `--prefer-binary`

### Files Modified
- `setup.sh` - Added smart installation strategy with three-tier fallback
- `CHANGELOG.md` - Added v0.3.0 release notes

---

## v0.2.0 (2026-11-03)

### New Features
- **MV/RAW Series Support**: Full web register access for MV and RAW series cameras
  - 88 MV series registers with 76 commands across 11 groups
  - Auto-detection of camera series (GX vs MV/RAW) from sysfs
  - Series-specific command groups and register maps

- **Trigger Mode Capability Filtering**: Dynamic dropdown filtering based on hardware capabilities
  - Options filtered by `trgmodecap` (0x0030) register bits
  - Supports bit-mapped capability checking

- **Enhanced Result Display**: Special formatting for specific commands
  - Exposure Time Range: max/min with unit conversion
  - Sensor Register Read: ready bit verification and value masking
  - Temperature: Kelvin and Celsius display
  - Full bilingual support (English/Chinese)

### Changes
- L version displays in hex format (e.g., "F3.20")
- BLC Mode and Black Level moved to ISP Processing group
- Exposure Time Range moved to Exposure & Gain group
- ROI Configuration placed above Frame Rate
- Command generation refactored for multi-series support

### Files Added
- `config/mv_commands.json`, `config/mv_command_groups.json`
- `config/gx_commands.json`, `config/gx_command_groups.json`

---

## v0.1.1 (2026-10-28)

### New Features
- **Configurable Default I2C Settings**: Default I2C bus and address are now read from `config/default_i2c.json` instead of being hardcoded
- **Default I2C Display**: When no camera is detected, the left panel now shows the default I2C settings being used

### Changes
- Added `config/default_i2c.json` for configurable default I2C parameters
- Updated `/api/config` endpoint to read defaults from config file
- Frontend now loads and uses configurable defaults when no camera is probed
- Added visual indicator in left panel showing "Using default I2C settings" when no camera detected

### Files Modified
- `main.py` - Added `_load_default_i2c_config()` function
- `config/default_i2c.json` - New config file for default I2C settings
- `config/i18n.json` - Added `device.no_camera_hint` translation
- `app/templates/index.html` - Added default I2C info display section
- `app/static/app.js` - Added `loadDefaultConfig()`, `getEffectiveI2c()` helpers
- `app/static/style.css` - Added styles for default I2C info panel

---

## v0.1.0 (Initial Release)

Initial release of VEYE Camera Web Studio.
