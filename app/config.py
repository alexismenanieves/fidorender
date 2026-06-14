"""Application configuration loaded from environment variables.

Environment variables:
    RENDER_WORKERS: Process pool size (default: 2).
    MAX_UPLOAD_MB: Maximum upload size in megabytes (default: 100).
    MAX_PAGES: Maximum pages rendered per request (default: 200).
    REQUEST_TIMEOUT_SEC: Render job timeout in seconds (default: 120).
    DEFAULT_SCALE: Default render scale (default: 2.0).
    DEFAULT_FORMAT: Default output format (default: png).
    DEFAULT_JPEG_QUALITY: Default JPEG quality 1-100 (default: 85).
    LOG_LEVEL: Logging level DEBUG, INFO, WARNING, or ERROR (default: INFO).
"""

import os
from pathlib import Path

from dotenv import load_dotenv

_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(_ROOT / ".env")


def env(key: str, default: str = "") -> str:
    """Retrieve an environment value, based on the key."""
    return os.getenv(key, default)


RENDER_WORKERS = int(env("RENDER_WORKERS", "2"))
MAX_UPLOAD_MB = int(env("MAX_UPLOAD_MB", "100"))
MAX_PAGES = int(env("MAX_PAGES", "200"))
REQUEST_TIMEOUT_SEC = int(env("REQUEST_TIMEOUT_SEC", "120"))

DEFAULT_SCALE = float(env("DEFAULT_SCALE", "2.0"))
DEFAULT_FORMAT = env("DEFAULT_FORMAT", "png")
DEFAULT_JPEG_QUALITY = int(env("DEFAULT_JPEG_QUALITY", "85"))
LOG_LEVEL = env("LOG_LEVEL", "INFO").upper()
