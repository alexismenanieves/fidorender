import zipfile
from io import BytesIO

import pytest

from app.render import render_pdf, render_pdf_to_zip, validate_render_options


def test_validate_render_options_accepts_png():
    assert validate_render_options("png", 2.0, 85) == "png"


def test_validate_render_options_rejects_bad_format():
    with pytest.raises(ValueError, match="Unsupported format"):
        validate_render_options("gif", 2.0, 85)


def test_validate_render_options_rejects_bad_scale():
    with pytest.raises(ValueError, match="Scale"):
        validate_render_options("png", 0, 85)


def test_validate_render_options_rejects_bad_quality():
    with pytest.raises(ValueError, match="quality"):
        validate_render_options("png", 2.0, 0)


def test_render_pdf_returns_one_page(minimal_pdf):
    pages = render_pdf(minimal_pdf, fmt="png", scale=1.0)
    assert len(pages) == 1
    assert pages[0].page_number == 1
    assert pages[0].format == "png"
    assert pages[0].data.startswith(b"\x89PNG")


def test_render_pdf_to_zip_contains_page_file(minimal_pdf):
    zip_bytes = render_pdf_to_zip(minimal_pdf, fmt="png", scale=1.0)
    with zipfile.ZipFile(BytesIO(zip_bytes)) as zf:
        names = zf.namelist()
    assert names == ["page-001.png"]


def test_render_pdf_rejects_non_pdf():
    with pytest.raises((OSError, RuntimeError, ValueError)):
        render_pdf(b"not a pdf", fmt="png", scale=1.0)
