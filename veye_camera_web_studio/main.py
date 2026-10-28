"""VEYE Camera Web Studio - Main FastAPI Application."""
import os
import sys
import json
import logging

# Ensure the project root (veye_web_studio/) is on sys.path so that
# ``from app.…`` imports resolve correctly when this file is executed
# directly (``python main.py``).
_PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware

from app.api.devices import router as devices_router
from app.api.commands import router as commands_router

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

# Paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(BASE_DIR, "app", "static")
TEMPLATE_DIR = os.path.join(BASE_DIR, "app", "templates")
CONFIG_DIR = os.path.join(BASE_DIR, "config")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup/shutdown lifecycle."""
    logger.info("VEYE Camera Web Studio starting up...")
    # Load config files to verify they exist
    for fname in ["commands.json", "command_groups.json", "i18n.json"]:
        path = os.path.join(CONFIG_DIR, fname)
        if os.path.isfile(path):
            logger.info(f"  Config loaded: {fname}")
        else:
            logger.warning(f"  Config missing: {fname}")
    yield
    logger.info("VEYE Camera Web Studio shutting down.")


app = FastAPI(
    title="VEYE Camera Web Studio",
    description="Web-based tool for managing and debugging VEYE cameras",
    version="0.1.1",
    lifespan=lifespan,
)

# Add CORS middleware for cross-origin support
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, restrict to specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

# Templates
templates = Jinja2Templates(directory=TEMPLATE_DIR)

# Register API routers
app.include_router(devices_router)
app.include_router(commands_router)


@app.get("/api/i18n")
def get_i18n():
    """Return internationalization strings."""
    path = os.path.join(CONFIG_DIR, "i18n.json")
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return {"error": "i18n.json not found"}


def _load_default_i2c_config() -> dict:
    """Load default I2C config from config/default_i2c.json."""
    path = os.path.join(CONFIG_DIR, "default_i2c.json")
    defaults = {"default_i2c_bus": 10, "default_i2c_addr": "0x3b"}
    try:
        with open(path, "r") as f:
            data = json.load(f)
            defaults["default_i2c_bus"] = int(data.get("default_i2c_bus", 10))
            defaults["default_i2c_addr"] = str(data.get("default_i2c_addr", "0x3b"))
    except (FileNotFoundError, json.JSONDecodeError, ValueError):
        pass
    return defaults


@app.get("/api/config")
def get_config():
    """Return application configuration."""
    i2c_defaults = _load_default_i2c_config()
    config = {
        "app_name": "VEYE Camera Web Studio",
        "version": "0.1.1",
        "default_i2c_bus": i2c_defaults["default_i2c_bus"],
        "default_i2c_addr": i2c_defaults["default_i2c_addr"],
        "default_timeout": 5,
        "supported_languages": ["en", "zh"],
    }
    # Try to load platform config from config/ directory
    platform_path = os.path.join(CONFIG_DIR, "platform.json")
    try:
        with open(platform_path, "r") as f:
            pdata = json.load(f)
            config["detected_platform"] = pdata.get("platform", "unknown")
    except (FileNotFoundError, json.JSONDecodeError):
        # Fall back to runtime detection
        from app.services.system_service import SystemService
        config["detected_platform"] = SystemService._detect_platform()
    return config


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    """Serve the main application page."""
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/health")
def health_check():
    """Health check endpoint."""
    return {"status": "ok", "app": "VEYE Camera Web Studio"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8080,
        reload=True,
        log_level="info",
    )
