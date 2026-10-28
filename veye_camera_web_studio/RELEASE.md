# Release Log

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
