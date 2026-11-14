# VEYE Camera I2C Studio

**English** | [中文](README.md)

A web-based tool for managing and debugging VEYE cameras. Perform register-level read/write operations directly from your browser.

> **v0.5.0 Release** — Supports Jetson, Raspberry Pi 5, and Rockchip platforms. Supports both GX/GXC series and MV/RAW series cameras. Live preview in the browser (MJPEG over HTTP) now handles **multiple cameras at once** — one independent preview window per camera, up to 4 concurrent — and switching the selected camera no longer interrupts an existing preview. Uses the hardware JPEG encoder automatically on Rockchip and Jetson (`mppjpegenc` / `nvjpegenc`), with an automatic software-encoder fallback when a hardware launch fails. Network-resilient installer plus a smart installation strategy with maximum compatibility.

## Features

- Automatic detection of connected VEYE cameras (GX/GXC series and MV/RAW series)
- GX series: 108 register commands covering all configurable camera parameters
- MV/RAW series: 76 register commands with sensor register read support
- Register read/write with support for multiple parameter types (numeric, enumerated, bitfield)
- Command group browsing and search
- Bilingual interface (English / Chinese)
- Dark / light theme toggle
- Automatic feature filtering based on camera series (e.g., trigger modes)
- Live preview (MJPEG over HTTP): GX/GXC (UYVY) and MV/RAW (GREY) viewable directly in the browser, with resolution / framerate / ROI / quality controls prefilled from the camera's current configuration
- Concurrent multi-camera preview: one independent window per camera (up to 4), and selecting another camera no longer interrupts a running preview; the sidebar **Running Previews** list shows one row per pipeline with its camera label, resolution/framerate, the encoder actually in use and the measured fps, with per-row reopen/stop plus Stop All
- Per-platform automatic JPEG encoder selection: hardware `mppjpegenc` on Rockchip (dmabuf straight into the encoder, no color convert), GPU `nvjpegenc` on Jetson (kept behind the `nvvidconv` I420 stage), the portable software path on Raspberry Pi; `encoder` can force the CPU encoder for comparison
- Automatic hardware->software encoder fallback: if the auto-picked hardware encoder dies during startup the pipeline is relaunched once on `jpegenc`, with the fallback source reported in the result
- Visible preview failures: a failed start returns the real GStreamer reason at once, an unexpected process exit flips the stream to `error` with that reason, and the frontend stops polling a dead stream

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
│   ├── main.py                    # FastAPI entry point (v0.5.0)
│   ├── app/
│   │   ├── adapters/              # Platform adapters
│   │   │   └── jetson/            # Jetson platform adapter
│   │   ├── api/                   # API routes
│   │   │   ├── devices.py         # Camera probe & series detection
│   │   │   ├── commands.py        # Register command execution
│   │   │   └── stream.py          # Live preview API (/api/stream)
│   │   ├── services/              # Business logic layer
│   │   │   ├── command_service.py     # Register read/write execution
│   │   │   ├── probe_service.py       # Camera probe & series detection
│   │   │   ├── stream_service.py      # Preview pipeline lifecycle / device ownership / fps metering
│   │   │   ├── documentation_service.py # Documentation service
│   │   │   ├── system_service.py      # System information
│   │   │   └── log_service.py         # Operation logs
│   │   ├── streaming/             # Four-layer live preview subsystem
│   │   │   ├── profile.py         # Pipeline parameters (caps, encoder choice)
│   │   │   ├── pipeline.py        # gst-launch argv assembly
│   │   │   ├── configurators/     # Stage 0: per-platform media-ctl / I2C setup
│   │   │   ├── providers/         # Stage 1: color conversion + hardware encoder selection
│   │   │   └── transports/        # Stage 2: MJPEG multipart delivery
│   │   ├── static/                # Frontend static files
│   │   │   ├── app.js
│   │   │   ├── style.css
│   │   │   └── logo*.png
│   │   └── templates/             # HTML templates
│   │       ├── index.html
│   │       └── preview.html       # Popup preview page (MJPEG consumer)
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
- **Live preview**: GStreamer capture → MJPEG multipart → HTTP streaming response, rendered by a plain browser `<img>`; nothing is written to disk
- **Preview layering** (`app/streaming/`): Stage 0 Configurator (media-ctl / I2C setup) → Stage 1 Provider (color conversion and encoder choice) → Stage 2 Transport (MJPEG muxing/delivery) → Stage 3 StreamService (pipeline lifecycle, exclusive capture-node ownership, teardown when the consumer leaves)

## Quick Start

### Prerequisites

- Python 3.8+
- GCC (for compiling I2C tools, only needed if pre-compiled packages unavailable)
- Live preview dependencies: GStreamer 1.0 (base / good plugins) and v4l-utils, installed automatically by `setup.sh` (warns instead of aborting when `sudo` is unavailable). Hardware JPEG encoding on Rockchip additionally requires `gstreamer1.0-rockchip1` (provides `mppjpegenc`), on Jetson the L4T `nvjpegenc` plugin; when the plugin is missing or a hardware launch fails the software encoder is used automatically
- Supported platforms:
  - **Nvidia Jetson** (JetPack 4.x/5.x)
  - **Raspberry Pi 5** (Debian 12+/Bookworm, aarch64)
  - Raspberry Pi 4 (experimental support)
  - **Rockchip RK3588** platform

### Installation & Launch

```bash
# Run the setup script (compiles I2C tools, installs Python dependencies)
./setup.sh

# Start the server
cd veye_camera_web_studio
python3 main.py
```

Open `http://localhost:8080` in your browser.

### One-Command Launch

```bash
./setup.sh --start
```

## Known Limitations

- **Jetson**, **Raspberry Pi 5**, and **Rockchip** platforms are fully tested (including live preview)
- Raspberry Pi 4 and other platforms need further validation
- Requires I2C bus access permissions (may need root or proper udev rules)
- Jetson's `nvjpegenc` only accepts I420/GRAY8 input (never raw UYVY), so its hardware path keeps the `nvvidconv` convert stage - unlike Rockchip's dmabuf-fed `mppjpegenc`; if that element fails to launch on a given board, the pipeline is relaunched once on the software `jpegenc`
- Multiple clients accessing the I2C bus concurrently may cause conflicts
- Live preview allows one consumer per capture node at a time (the popup page takes precedence); the pipeline is torn down as soon as the consumer disconnects
- Concurrent previews are capped at 4 (`_MAX_STREAMS`) because a browser allows only six HTTP/1.1 connections per origin; when pop-ups are blocked the view falls back to the single inline thumbnail, and in that mode only one preview can be watched at a time
- Concurrent hardware encoding is measured on Jetson only: two `nvjpegenc` instances side by side delivered 30.0 fps at 1080p@30 and 40.0 fps at 1080p@60; a second `mppjpegenc` instance on Rockchip is still unverified on hardware
- 1080p software encoding tops out near 30 fps (`videoconvert` and `jpegenc` are both single-threaded); the Rockchip hardware path reaches ~54 fps at quality 60 but only ~31 fps at quality 85, because at higher quality the bottleneck moves to "byte read-out → HTTP delivery" (~4 MB/s)
- Rockchip `rkcif` lists only 1-30 fps in `VIDIOC_ENUM_FRAMEINTERVALS` (an `S_FMT` restriction, not a transport limit); the capture caps no longer carry `framerate` - frame rate comes from the I2C 0x0850 register and the media-ctl pad - so entering the camera's nominal maximum (e.g. 60) in the preview form is correct
- In dark scenes AE extends exposure (slow shutter), so the sensor delivers fewer frames than requested; that drop is not a software issue. Compare `v4l2-ctl -d /dev/videoXX --stream-mmap` against the UI's `measured_fps` to tell the camera side from the encode side

## Platform Compatibility

| Platform | Status | Notes |
|----------|--------|-------|
| Nvidia Jetson | ✅ Full Support | Original development platform; hardware MJPEG needs the L4T `nvjpegenc` plugin, with automatic software fallback when it is missing |
| Raspberry Pi 5 | ✅ Full Support | Tested with Debian 13 / aarch64 |
| Raspberry Pi 4 | ⚠️ Experimental | Scripts included, needs validation |
| Rockchip RK3588 | ✅ Full Support | Tested on Orange Pi CM5; hardware MJPEG needs `gstreamer1.0-rockchip1` |

## Changelog

See [CHANGELOG.md](CHANGELOG.md) for detailed version history.

## License

MIT
