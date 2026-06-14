"""PDF rendering pipeline using pypdfium2."""

import io
import zipfile
from dataclasses import dataclass
from typing import Any

import pypdfium2 as pdfium
from loguru import logger
from PIL import Image

from app.pages import parse_page_selection


@dataclass
class RenderedPage:
    """A single rendered PDF page as encoded image bytes."""

    page_number: int
    format: str
    data: bytes


def validate_render_options(fmt: str, scale: float, jpeg_quality: int) -> str:
    """Validate render parameters and return the normalized format string.

    Args:
        fmt: Output image format (png, jpeg, or jpg).
        scale: Render scale factor (exclusive 0, inclusive 10].
        jpeg_quality: JPEG quality from 1 to 100.

    Returns:
        Lowercased format string.

    Raises:
        ValueError: If any parameter is out of range or unsupported.
    """
    fmt = fmt.lower()
    if fmt not in {"png", "jpeg", "jpg"}:
        raise ValueError(f"Unsupported format {fmt}")
    if scale <= 0 or scale > 10:
        raise ValueError("Scale must be between 0 and 10")
    if jpeg_quality < 1 or jpeg_quality > 100:
        raise ValueError("quality must be between 1 and 100")
    return fmt


def _image_format(fmt: str) -> str:
    return "jpeg" if fmt in {"jpeg", "jpg"} else "png"


def _encode_page_image(
    pil_image: Image.Image, image_format: str, jpeg_quality: int
) -> bytes:
    buffer = io.BytesIO()
    if image_format == "jpeg":
        if pil_image.mode in {"RGBA", "LA", "P"}:
            pil_image = pil_image.convert("RGB")
        pil_image.save(buffer, format="JPEG", quality=jpeg_quality)
    else:
        pil_image.save(buffer, format="PNG")
    return buffer.getvalue()


def _render_page(
    page: Any,
    *,
    scale: float,
    page_number: int,
    image_format: str,
    jpeg_quality: int,
) -> RenderedPage:
    try:
        bitmap = page.render(scale=scale)
        data = _encode_page_image(bitmap.to_pil(), image_format, jpeg_quality)
        return RenderedPage(page_number=page_number, format=image_format, data=data)
    finally:
        page.close()


def render_pdf(
    pdf_bytes: bytes,
    *,
    fmt: str = "png",
    scale: float = 2.0,
    pages: str | None = None,
    jpeg_quality: int = 85,
    max_pages: int = 200,
) -> list[RenderedPage]:
    """Render selected PDF pages to encoded images.

    Args:
        pdf_bytes: Raw PDF file contents.
        fmt: Output image format (png, jpeg, or jpg).
        scale: Render scale factor.
        pages: Optional page selection spec (e.g. ``"1,3-5"``).
        jpeg_quality: JPEG quality when fmt is jpeg/jpg.
        max_pages: Maximum number of pages allowed in one request.

    Returns:
        List of rendered pages in selection order.

    Raises:
        ValueError: Invalid options, page selection, or page count limit.
    """
    fmt = validate_render_options(fmt, scale, jpeg_quality)
    image_format = _image_format(fmt)
    pdf = pdfium.PdfDocument(pdf_bytes)
    try:
        indices = parse_page_selection(pages, len(pdf))
        if len(indices) > max_pages:
            raise ValueError(f"Exceed allowed pages (max: {max_pages})")

        logger.debug(
            "Rendering pages count={} format={} scale={}",
            len(indices),
            image_format,
            scale,
        )
        rendered = [
            _render_page(
                pdf[index],
                scale=scale,
                page_number=index + 1,
                image_format=image_format,
                jpeg_quality=jpeg_quality,
            )
            for index in indices
        ]
        logger.info("Render complete page_count={} format={}", len(rendered), fmt)
        return rendered
    finally:
        pdf.close()


def render_pdf_to_zip(
    pdf_bytes: bytes,
    *,
    fmt: str = "png",
    scale: float = 2.0,
    pages: str | None = None,
    jpeg_quality: int = 85,
    max_pages: int = 200,
) -> bytes:
    """Render PDF pages and package them as a ZIP archive.

    Args:
        pdf_bytes: Raw PDF file contents.
        fmt: Output image format (png, jpeg, or jpg).
        scale: Render scale factor.
        pages: Optional page selection spec (e.g. ``"1,3-5"``).
        jpeg_quality: JPEG quality when fmt is jpeg/jpg.
        max_pages: Maximum number of pages allowed in one request.

    Returns:
        ZIP file bytes containing ``page-NNN.{png|jpg}`` entries.
    """
    rendered = render_pdf(
        pdf_bytes,
        fmt=fmt,
        scale=scale,
        pages=pages,
        jpeg_quality=jpeg_quality,
        max_pages=max_pages,
    )
    ext = "jpg" if fmt.lower() in {"jpeg", "jpg"} else "png"
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for page in rendered:
            name = f"page-{page.page_number:03d}.{ext}"
            zf.writestr(name, page.data)
    return buffer.getvalue()
