# Fidorender

<p align="center">
  <img src="Fido.svg" alt="Fido, the Fidorender mascot" width="200">
</p>

FastAPI service that renders PDF pages to PNG or JPEG images. Upload a PDF and receive rendered pages as a ZIP archive or JSON with base64-encoded images.

## Requirements

- Python 3.13+
- [uv](https://docs.astral.sh/uv/) (recommended)

## Local development

```bash
uv sync --group dev
uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 2727
```

Run tests, lint, format, and type checks:

```bash
uv run pytest -v
uv run ruff check .
uv run ruff format --check .
uv run mypy
```

Format code locally:

```bash
uv run ruff format .
```

## Configuration

Set these environment variables (defaults shown):

| Variable | Default | Description |
|----------|---------|-------------|
| `RENDER_WORKERS` | `2` | Process pool size for rendering |
| `MAX_UPLOAD_MB` | `100` | Maximum upload size (MB) |
| `MAX_PAGES` | `200` | Maximum pages per request |
| `REQUEST_TIMEOUT_SEC` | `120` | Render job timeout (seconds) |
| `DEFAULT_SCALE` | `2.0` | Default render scale |
| `DEFAULT_FORMAT` | `png` | Default output format |
| `DEFAULT_JPEG_QUALITY` | `85` | Default JPEG quality (1–100) |
| `LOG_LEVEL` | `INFO` | Log level: `DEBUG`, `INFO`, `WARNING`, `ERROR` |
| `PORT` | `2727` | HTTP server port |
| `GRACEFUL_SHUTDOWN_SEC` | `30` | Grace period for in-flight requests on shutdown |

Copy [`.env.example`](.env.example) to `.env` and adjust values for local development. Do not bake secrets or `.env` files into container images.

## API

Base URL when running locally: `http://localhost:2727`

### `GET /health`

Returns `{"status": "ok"}`.

```bash
curl http://localhost:2727/health
```

### `POST /v1/renderer`

Upload a PDF and receive rendered pages as a ZIP file (default) or JSON with base64-encoded images.

Multipart form fields:

| Field | Required | Default | Description |
|-------|----------|---------|-------------|
| `file` | yes | — | PDF file upload |
| `format` | no | `png` | `png`, `jpeg`, or `jpg` |
| `scale` | no | `2.0` | Render scale (0–10] |
| `pages` | no | all | Page selection, e.g. `1,3-5` |
| `quality` | no | `85` | JPEG quality (1–100) |
| `response` | no | `zip` | `zip` or `json` |

**ZIP response (default)** — saves `pages.zip` with `page-001.png`, `page-002.png`, …

```bash
curl -X POST http://localhost:2727/v1/renderer \
  -F "file=@document.pdf" \
  -o pages.zip
```

**JSON response** — returns `page_count` and a `pages` array with base64 image data:

```bash
curl -X POST http://localhost:2727/v1/renderer \
  -F "file=@document.pdf" \
  -F "response=json" \
  -F "format=png" \
  -F "scale=1.0"
```

**Selected pages and JPEG output:**

```bash
curl -X POST http://localhost:2727/v1/renderer \
  -F "file=@document.pdf" \
  -F "pages=1,3-5" \
  -F "format=jpeg" \
  -F "quality=90" \
  -o pages.zip
```

Replace `document.pdf` with the path to your PDF. When using Docker or Podman, the service must be reachable at port `2727` (see [Docker](#docker) below).

## Docker

Build and run locally:

```bash
docker build -t fidorender .
docker run --rm -p 2727:2727 fidorender
```

The container runs as a non-root `appuser`. Pass configuration via `-e` flags or your orchestrator.

## GitHub Container Registry

Images are published to `ghcr.io/<owner>/fidorender` on pushes to `main` and version tags.

```bash
docker pull ghcr.io/<owner>/fidorender:latest
docker run --rm -p 2727:2727 ghcr.io/<owner>/fidorender:latest
```

## Security notes

This service has **no built-in authentication**. Deploy behind a private network or reverse proxy with access controls. Large or concurrent uploads can consume significant memory; tune `MAX_UPLOAD_MB`, `MAX_PAGES`, and `RENDER_WORKERS` for your environment.

Future improvements: API key auth, rate limiting, request concurrency limits.
