FROM python:3.13-slim-bookworm

WORKDIR /app

RUN useradd --create-home appuser

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app/ app/

USER appuser

ENV PORT=2727
ENV GRACEFUL_SHUTDOWN_SEC=30

EXPOSE 2727

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD python -c "import os, urllib.request; urllib.request.urlopen(f'http://127.0.0.1:{os.environ[\"PORT\"]}/health')"

CMD ["python", "-m", "app.server"]
