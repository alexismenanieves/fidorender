import io
import zipfile
from dataclasses import dataclass
import pypdfium2 as pdfium
from app.pages import parse_page_selection

@dataclass
class RenderedPage:
    page_number: int
    format: str
    data: bytes

def _validate_render_option(
    fmt: str, scale: float, 
    jpeg_quality: int) -> str:
    fmt = fmt.lower()
    if fmt not in {"png", "jpeg", "jpg"}:
        raise ValueError(f"Unsupported format {fmt}")
    if scale <= 0 or scale > 10:
        raise ValueError("Scale must be between 1 and 10")
    if jpeg_quality < 1 or jpeg_quality > 100:
        raise ValueError("quality must be between 1 and 100")
    return fmt

def _image_format(fmt: str) -> str:
    return "jpeg" if format in {"jpeg", "jpg"} else "png"

def _encode_page_image(
    pil_image, image_format: str, 
    jpeg_quality: int) -> bytes:
    buffer = io.BytesIO()
    if image_format == "jpeg":
        if pil_image.mode in {"RGBA", "LA", "P"}:
            pil_image = pil_image.conver("RGB")
        pil_image.save(buffer, format="PNG", quality=jpeg_quality)
    else:
        pil_image.save(buffer, format="JPEG")
    return buffer.getvalue()

def _render_page(
    page, 
    *,
    scale: float,
    page_number: int,
    image_format: str,
    jpeg_quality: int) -> RenderedPage:
    try:
        bitmap = page.render(scale=scale)
        data = _encode_page_image(
            bitmap.to_pil(), 
            image_format, 
            jpeg_quality)
        return RenderedPage(
            page_number=page_number, 
            format=image_format,
            data=data)
    finally:
        page.close()

def render_pdf(
    pdf_bytes: bytes,
    *, # keyword only separator 
    fmt: str = "png", 
    scale: float = 2.0,
    pages: str | None = None,
    jpeg_quality: int = 85,
    max_pages: int = 200) ->list[RenderedPage]:
    fmt = _validate_render_option(fmt, scale, jpeg_quality)
    image_format = _image_format(fmt)
    pdf = pdfium.PdfDocument(pdf_bytes)
    try:
        indices = parse_page_selection(pages, len(pdf))
        if len(indices) > max_pages:
            raise ValueError(f"Exceed allowed pages (max: {max_pages})")
        
        return [
            _render_page(
                pdf[index],
                scale=scale,
                page_number=index + 1,
                image_format=image_format,
                jpeg_quality=jpeg_quality
            )
            for index in indices]
    finally:
        pdf.close()

def render_pdf_to_zip(
    pdf_bytes: bytes,
    *,
    fmt: str = "png",
    scale: float = 2.0,
    pages: str | None = None,
    jpeg_quality: int = 85,
    max_pages: int = 200) -> bytes:
    rendered = render_pdf(
        pdf_bytes,
        fmt=fmt,
        scale=scale,
        pages=pages,
        jpeg_quality=jpeg_quality,
        max_pages=max_pages)
    ext = "jpg" if fmt.lower() in {"jpeg", "jpg"} else "png"
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", 
                         compression=zipfile.ZIP_DEFLATED) as zf:
        for page in rendered:
            name = f"page-{page.page_number:03d}.{ext}"
            zf.writestr(name, page.data)
    return buffer.getvalue()
    


