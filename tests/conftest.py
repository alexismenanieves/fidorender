import pytest
from fastapi.testclient import TestClient

from app.main import app

MINIMAL_PDF = b"""%PDF-1.1
1 0 obj
<< /Type /Catalog /Pages 2 0 R >>
endobj
2 0 obj
<< /Type /Pages /Kids [3 0 R] /Count 1 >>
endobj
3 0 obj
<< /Type /Page /MediaBox [0 0 612 792] /Parent 2 0 R /Resources << >> >>
endobj
xref
0 4
0000000000 65535 f
0000000009 00000 n
0000000058 00000 n
0000000115 00000 n
trailer
<< /Size 4 /Root 1 0 R >>
startxref
190
%%EOF"""


@pytest.fixture
def minimal_pdf() -> bytes:
    return MINIMAL_PDF


@pytest.fixture
def client(monkeypatch):
    async def run_in_pool_sync(func):
        return func()

    monkeypatch.setattr("app.main._run_in_pool", run_in_pool_sync)
    with TestClient(app) as test_client:
        yield test_client
