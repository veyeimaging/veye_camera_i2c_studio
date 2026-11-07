# Release Log

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
