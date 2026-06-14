"""Uvicorn entrypoint with graceful shutdown settings."""

import uvicorn

from app.config import GRACEFUL_SHUTDOWN_SEC, PORT

if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=PORT,
        timeout_graceful_shutdown=GRACEFUL_SHUTDOWN_SEC,
    )
