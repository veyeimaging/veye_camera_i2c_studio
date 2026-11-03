# Release Log

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
