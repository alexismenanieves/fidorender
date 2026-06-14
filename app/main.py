"""FastAPI application entry point for the Fidorender PDF service."""

import asyncio
from collections.abc import AsyncIterator, Callable
from concurrent.futures import ProcessPoolExecutor
from contextlib import asynccontextmanager

from fastapi import FastAPI, File, Form, UploadFile
from fastapi.responses import JSONResponse, Response
from loguru import logger

from app.api import RenderRequestParams, execute_render_request
from app.config import (
    DEFAULT_FORMAT,
    DEFAULT_JPEG_QUALITY,
    DEFAULT_SCALE,
    RENDER_WORKERS,
    REQUEST_TIMEOUT_SEC,
)
from app.log_config import configure_logging

configure_logging()

_executor: ProcessPoolExecutor | None = None


def _get_executor() -> ProcessPoolExecutor:
    global _executor
    if _executor is None:
        logger.debug("Creating process pool workers={}", RENDER_WORKERS)
        _executor = ProcessPoolExecutor(max_workers=RENDER_WORKERS)
    return _executor


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    """Create and tear down the process pool used for PDF rendering."""
    logger.info("Application startup workers={}", RENDER_WORKERS)
    yield
    global _executor
    if _executor is not None:
        logger.info("Shutting down process pool")
        _executor.shutdown(wait=True)
        _executor = None


app = FastAPI(
    title="File document (fido) renderer",
    version="0.1.0",
    lifespan=lifespan,
)


@app.get("/health")
def health() -> dict[str, str]:
    """Return a simple health check payload."""
    return {"status": "ok"}


async def _run_in_pool[T](func: Callable[[], T]) -> T:
    """Run a synchronous render function in the process pool with timeout."""
    loop = asyncio.get_running_loop()
    return await asyncio.wait_for(
        loop.run_in_executor(_get_executor(), func),
        timeout=REQUEST_TIMEOUT_SEC,
    )


@app.post("/v1/renderer", response_model=None)
async def render_endpoint(
    file: UploadFile = File(...),  # noqa: B008
    format: str = Form(default=DEFAULT_FORMAT),
    scale: float = Form(default=DEFAULT_SCALE),
    pages: str | None = Form(default=None),
    quality: int = Form(default=DEFAULT_JPEG_QUALITY),
    response: str = Form(default="zip"),
) -> Response | JSONResponse:
    """Render an uploaded PDF to PNG/JPEG pages as ZIP or JSON."""
    params = RenderRequestParams(format, scale, pages, quality, response)
    return await execute_render_request(file, _run_in_pool, params)
