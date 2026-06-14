import asyncio
import base64
from concurrent.futures import ProcessPoolExecutor
from contextlib import asynccontextmanager
from functools import partial

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import JSONResponse, Response

from app.config import (
    DEFAULT_FORMAT,
    DEFAULT_JPEG_QUALITY,
    DEFAULT_SCALE,
    MAX_PAGES,
    MAX_UPLOAD_MB,
    RENDER_WORKERS,
    REQUEST_TIMEOUT_SEC
)

from app.render import render_pdf, render_pdf_to_zip

_executor: ProcessPoolExecutor | None = None

def _get_executor() -> ProcessPoolExecutor:
    if _executor is None:
        raise RuntimeError("Process pool not initialized")
    return _executor

@asynccontextmanager
async def lifespan(_app: FastAPI):
    global _executor
    _executor = ProcessPoolExecutor(max_workers=RENDER_WORKERS)
    yield
    _executor.shutdown(wait=True)
    _executor = None

app = FastAPI(
    title="File document (fido) renderer", 
    version="0.1.0", lifespan=lifespan)

@app.get("/health")
def health():
    return {"status": "ok"}

async def _run_in_pool(func):
    loop = asyncio.get_running_loop()
    return await asyncio.wait_for(
        loop.run_in_executor(_get_executor(), func),
        timeout=REQUEST_TIMEOUT_SEC
    )

@app.post("v1/renderer")
async def render_endpoint(
    file: UploadFile = File(...),
    format: str = Form(default=DEFAULT_FORMAT),
    scale: float = Form(default=DEFAULT_SCALE),
    pages: str | None = Form(default=None),
    quality: int = Form(default=DEFAULT_JPEG_QUALITY),
    response: str = Form(default="zip")):
    data = await file.read()
    if not data:
        raise HTTPException(status_code=400, detail="Empty file")
    max_bytes = MAX_UPLOAD_MB * 1024 * 1024
    if len(data) > max_bytes:
        raise HTTPException(
            status_code=413, 
            detail=f"File exceeds {MAX_UPLOAD_MB} MB limit")
    
    response_mode = response.lower().strip()
    if response_mode not in {"zip", "json"}:
        raise HTTPException(
            status_code=400, 
            detail="Response must be zip or json"
        )

    kwargs = {
        "fmt": format,
        "scale": scale,
        "pages": pages,
        "jpeg_quality": quality,
        "max_pages": MAX_PAGES
    } 

    try:
        if response_mode == "zip":
            job = partial(render_pdf_to_zip, data, **kwargs)
            zip_bytes = await _run_in_pool(job)
            return Response(
                content=zip_bytes,
                media_type="application/zip",
                headers={
                    "Content-Disposition": 'attachment, filename="pages.zip'
                    }
            )
        
        job = partial(render_pdf, data, **kwargs)
        rendered = await _run_in_pool(job)
        return JSONResponse(
            {
                "page_count": len(rendered),
                "pages": [
                    {
                        "page": page.page_number,
                        "format": page.format,
                        "data_base64": 
                        base64.b64encode(page.data).decode("ascii"),
                    }
                    for page in rendered
                ]
            })
    except asyncio.TimeoutError as exc:
        raise HTTPException
