"""HTTP-layer helpers for the PDF render endpoint."""

import asyncio
import base64
import time
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from functools import partial
from typing import Any, Literal

from fastapi import HTTPException, UploadFile
from fastapi.responses import JSONResponse, Response
from loguru import logger

from app.config import MAX_PAGES, MAX_UPLOAD_MB
from app.render import (
    RenderedPage,
    render_pdf,
    render_pdf_to_zip,
    validate_render_options,
)

PDF_MAGIC = b"%PDF-"

type RunInPool[T] = Callable[[Callable[[], T]], Awaitable[T]]


@dataclass(frozen=True)
class RenderRequestParams:
    """Validated form parameters for a render request."""

    fmt: str
    scale: float
    pages: str | None
    jpeg_quality: int
    response: str


async def execute_render_request(
    file: UploadFile,
    run_in_pool: RunInPool[Any],
    params: RenderRequestParams,
) -> Response | JSONResponse:
    """Validate input, render the PDF, and return ZIP or JSON."""
    started = time.perf_counter()
    logger.info(
        "Render request received filename={} format={} scale={} response={} pages={}",
        file.filename,
        params.fmt,
        params.scale,
        params.response,
        params.pages,
    )

    try:
        data = await read_and_validate_upload(file)
        validate_pdf_content(data)
        response_mode = parse_response_mode(params.response)
        kwargs = build_render_kwargs(
            fmt=params.fmt,
            scale=params.scale,
            pages=params.pages,
            jpeg_quality=params.jpeg_quality,
        )
        result = await dispatch_render_response(
            data, response_mode, run_in_pool, **kwargs
        )
        _log_render_completed(file.filename, response_mode, len(data), started)
        return result
    except HTTPException as exc:
        _log_render_rejected(file.filename, exc, started)
        raise
    except Exception as exc:
        http_exc = map_render_exception(exc)
        _log_render_failed(file.filename, http_exc, exc, started)
        raise http_exc from exc


def _log_render_completed(
    filename: str | None,
    response_mode: str,
    size_bytes: int,
    started: float,
) -> None:
    elapsed_ms = (time.perf_counter() - started) * 1000
    logger.info(
        (
            "Render request completed filename={} response={} "
            "size_bytes={} elapsed_ms={:.1f}"
        ),
        filename,
        response_mode,
        size_bytes,
        elapsed_ms,
    )


def _log_render_rejected(
    filename: str | None, exc: HTTPException, started: float
) -> None:
    elapsed_ms = (time.perf_counter() - started) * 1000
    logger.warning(
        "Render request rejected filename={} status={} detail={} elapsed_ms={:.1f}",
        filename,
        exc.status_code,
        exc.detail,
        elapsed_ms,
    )


def _log_render_failed(
    filename: str | None,
    http_exc: HTTPException,
    exc: Exception,
    started: float,
) -> None:
    elapsed_ms = (time.perf_counter() - started) * 1000
    logger.error(
        ("Render request failed filename={} status={} elapsed_ms={:.1f} error_type={}"),
        filename,
        http_exc.status_code,
        elapsed_ms,
        type(exc).__name__,
    )


async def dispatch_render_response(
    data: bytes,
    response_mode: Literal["zip", "json"],
    run_in_pool: RunInPool[Any],
    **kwargs: Any,
) -> Response | JSONResponse:
    """Route rendering to ZIP or JSON response builders."""
    if response_mode == "zip":
        return await render_zip_response(data, run_in_pool, **kwargs)
    return await render_json_response(data, run_in_pool, **kwargs)


async def read_and_validate_upload(file: UploadFile) -> bytes:
    """Read upload bytes and enforce size limits.

    Args:
        file: Uploaded file from multipart form data.

    Returns:
        Raw file bytes.

    Raises:
        HTTPException: 400 for empty files, 413 when over MAX_UPLOAD_MB.
    """
    data = await file.read()
    if not data:
        logger.warning("Rejected empty upload filename={}", file.filename)
        raise HTTPException(status_code=400, detail="Empty file")
    max_bytes = MAX_UPLOAD_MB * 1024 * 1024
    if len(data) > max_bytes:
        logger.warning(
            "Upload too large filename={} size_bytes={} limit_mb={}",
            file.filename,
            len(data),
            MAX_UPLOAD_MB,
        )
        raise HTTPException(
            status_code=413,
            detail=f"File exceeds {MAX_UPLOAD_MB} MB limit",
        )
    logger.debug(
        "Upload validated filename={} size_bytes={}",
        file.filename,
        len(data),
    )
    return data


def validate_pdf_content(data: bytes) -> None:
    """Reject uploads that do not look like PDF files.

    Args:
        data: Raw upload bytes.

    Raises:
        HTTPException: 400 when the PDF magic header is missing.
    """
    if not data.startswith(PDF_MAGIC):
        logger.warning("Rejected non-PDF upload size_bytes={}", len(data))
        raise HTTPException(status_code=400, detail="File must be a PDF")


def parse_response_mode(response: str) -> Literal["zip", "json"]:
    """Normalize and validate the response delivery mode.

    Args:
        response: Requested response format (zip or json).

    Returns:
        Lowercased response mode.

    Raises:
        HTTPException: 400 when mode is not zip or json.
    """
    response_mode = response.lower().strip()
    if response_mode == "zip":
        return "zip"
    if response_mode == "json":
        return "json"
    logger.warning("Invalid response mode requested mode={}", response)
    raise HTTPException(status_code=400, detail="Response must be zip or json")


def build_render_kwargs(
    *,
    fmt: str,
    scale: float,
    pages: str | None,
    jpeg_quality: int,
) -> dict[str, Any]:
    """Build render keyword arguments with early parameter validation.

    Args:
        fmt: Output image format.
        scale: Render scale factor.
        pages: Optional page selection spec.
        jpeg_quality: JPEG quality when applicable.

    Returns:
        Keyword arguments for render_pdf / render_pdf_to_zip.
    """
    validate_render_options(fmt, scale, jpeg_quality)
    return {
        "fmt": fmt,
        "scale": scale,
        "pages": pages,
        "jpeg_quality": jpeg_quality,
        "max_pages": MAX_PAGES,
    }


def map_render_exception(exc: Exception) -> HTTPException:
    """Map render pipeline exceptions to HTTP error responses.

    Args:
        exc: Exception raised during rendering.

    Returns:
        HTTPException with an appropriate status code and detail.
    """
    if isinstance(exc, HTTPException):
        return exc
    if isinstance(exc, asyncio.TimeoutError):
        logger.error("Render request timed out")
        return HTTPException(status_code=504, detail="Render request timed out")
    if isinstance(exc, ValueError):
        logger.warning("Render validation failed error={}", exc)
        return HTTPException(status_code=400, detail=str(exc))
    logger.exception("Failed to parse or render PDF")
    return HTTPException(status_code=422, detail="Failed to parse or render PDF")


async def render_zip_response(
    data: bytes, run_in_pool: RunInPool[bytes], **kwargs: Any
) -> Response:
    """Render PDF pages to a ZIP file response."""
    job = partial(render_pdf_to_zip, data, **kwargs)
    zip_bytes = await run_in_pool(job)
    return Response(
        content=zip_bytes,
        media_type="application/zip",
        headers={"Content-Disposition": 'attachment; filename="pages.zip"'},
    )


async def render_json_response(
    data: bytes, run_in_pool: RunInPool[list[RenderedPage]], **kwargs: Any
) -> JSONResponse:
    """Render PDF pages to a JSON response with base64-encoded images."""
    job = partial(render_pdf, data, **kwargs)
    rendered = await run_in_pool(job)
    return JSONResponse(
        {
            "page_count": len(rendered),
            "pages": [
                {
                    "page": page.page_number,
                    "format": page.format,
                    "data_base64": base64.b64encode(page.data).decode("ascii"),
                }
                for page in rendered
            ],
        }
    )
