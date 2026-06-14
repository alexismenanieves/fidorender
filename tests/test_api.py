def test_health(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_render_rejects_empty_file(client):
    response = client.post(
        "/v1/renderer",
        files={"file": ("empty.pdf", b"", "application/pdf")},
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "Empty file"


def test_render_rejects_non_pdf(client):
    response = client.post(
        "/v1/renderer",
        files={"file": ("bad.pdf", b"hello", "application/pdf")},
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "File must be a PDF"


def test_render_rejects_bad_format(client, minimal_pdf):
    response = client.post(
        "/v1/renderer",
        data={"format": "gif"},
        files={"file": ("doc.pdf", minimal_pdf, "application/pdf")},
    )
    assert response.status_code == 400
    assert "Unsupported format" in response.json()["detail"]


def test_render_rejects_bad_response_mode(client, minimal_pdf):
    response = client.post(
        "/v1/renderer",
        data={"response": "xml"},
        files={"file": ("doc.pdf", minimal_pdf, "application/pdf")},
    )
    assert response.status_code == 400


def test_render_json_success(client, minimal_pdf):
    response = client.post(
        "/v1/renderer",
        data={"response": "json", "format": "png", "scale": "1.0"},
        files={"file": ("doc.pdf", minimal_pdf, "application/pdf")},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["page_count"] == 1
    assert len(payload["pages"]) == 1
    assert payload["pages"][0]["page"] == 1
    assert payload["pages"][0]["format"] == "png"
    assert payload["pages"][0]["data_base64"]


def test_render_zip_success(client, minimal_pdf):
    response = client.post(
        "/v1/renderer",
        data={"response": "zip", "format": "png", "scale": "1.0"},
        files={"file": ("doc.pdf", minimal_pdf, "application/pdf")},
    )
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/zip"
    assert response.content.startswith(b"PK")
