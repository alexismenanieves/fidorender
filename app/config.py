import os
from pathlib import Path
from dotenv import load_dotenv

_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(_ROOT / ".env")

def env(key: str, default:str = "") -> str:
    """Retrieve an environment value, based on the key"""
    return os.getenv(key, default)

# These defaults work for a minimal machine xx cpu, xxgb RAM
RENDER_WORKERS = int(env("RENDER_WORKERS", "2"))
MAX_UPLOAD_MB = int(env("MAX_UPLOAD_MB", "100"))
MAX_PAGES = int(env("MAX_PAGES", "200"))
REQUEST_TIMEOUT_SEC = int(env("REQUEST_TIMEOUT_SEC", "120"))

DEFAULT_SCALE = int(env("DEFAULT_SCALE", "2.0"))
DEFAULT_FORMAT = env("DEFAULT_FORMAT", "png")
DEFAULT_JPEG_QUALITY = int(env("DEFAULT_JPEG_QUALITY", "85"))