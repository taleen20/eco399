import io
import os
import sys
import pytest
from unittest.mock import MagicMock, patch


MINIMAL_PDF = (
    b"%PDF-1.0\n"
    b"1 0 obj<</Type /Catalog /Pages 2 0 R>>endobj\n"
    b"2 0 obj<</Type /Pages /Kids [3 0 R] /Count 1>>endobj\n"
    b"3 0 obj<</Type /Page /MediaBox [0 0 612 792]>>endobj\n"
    b"xref\n0 4\n"
    b"0000000000 65535 f\n"
    b"0000000009 00000 n\n"
    b"0000000058 00000 n\n"
    b"0000000115 00000 n\n"
    b"trailer<</Size 4 /Root 1 0 R>>\n"
    b"startxref\n190\n%%EOF"
)


# ── /health ───────────────────────────────────────────────────────────────────

def test_health(client):
    res = client.get("/health")
    assert res.status_code == 200
    assert res.get_json()["status"] == "healthy"


# ── /upload ───────────────────────────────────────────────────────────────────

def test_upload_no_file(client):
    res = client.post("/upload")
    assert res.status_code == 400
    assert "error" in res.get_json()


def test_upload_empty_filename(client):
    res = client.post(
        "/upload",
        data={"file": (io.BytesIO(b""), ""), "language": "en"},
        content_type="multipart/form-data",
    )
    assert res.status_code == 400
    assert res.get_json()["error"] == "No file selected"


def test_upload_wrong_type(client):
    res = client.post(
        "/upload",
        data={"file": (io.BytesIO(b"hello"), "document.txt"), "language": "en"},
        content_type="multipart/form-data",
    )
    assert res.status_code == 400
    assert "PDF" in res.get_json()["error"]


def test_upload_too_large(client, app):
    original = app.config["MAX_CONTENT_LENGTH"]
    app.config["MAX_CONTENT_LENGTH"] = 10  # 10 bytes
    try:
        res = client.post(
            "/upload",
            data={"file": (io.BytesIO(b"x" * 100), "big.pdf"), "language": "en"},
            content_type="multipart/form-data",
        )
        assert res.status_code == 413
    finally:
        app.config["MAX_CONTENT_LENGTH"] = original


def test_upload_success(client):
    mock_task = MagicMock()
    mock_task.id = "test-job-abc123"
    sys.modules["tasks"].process_pdf.delay.return_value = mock_task

    res = client.post(
        "/upload",
        data={"file": (io.BytesIO(MINIMAL_PDF), "test.pdf"), "language": "en"},
        content_type="multipart/form-data",
    )

    assert res.status_code == 202
    assert res.get_json()["job_id"] == "test-job-abc123"
    sys.modules["tasks"].process_pdf.delay.assert_called_once()


def test_upload_defaults_language_to_en(client):
    mock_task = MagicMock()
    mock_task.id = "job-lang-test"
    sys.modules["tasks"].process_pdf.delay.return_value = mock_task

    client.post(
        "/upload",
        data={"file": (io.BytesIO(MINIMAL_PDF), "test.pdf")},
        content_type="multipart/form-data",
    )

    _, kwargs = sys.modules["tasks"].process_pdf.delay.call_args
    args, _ = sys.modules["tasks"].process_pdf.delay.call_args
    assert args[1] == "en"


# ── /status ───────────────────────────────────────────────────────────────────

def test_status_pending(client):
    mock_result = MagicMock()
    mock_result.state = "PENDING"

    with patch("main.AsyncResult", return_value=mock_result):
        res = client.get("/status/some-job-id")

    assert res.status_code == 200
    data = res.get_json()
    assert data["state"] == "pending"
    assert data["step"] == "Queued"


def test_status_progress(client):
    mock_result = MagicMock()
    mock_result.state = "PROGRESS"
    mock_result.info = {"step": "Running OCR on 2 table(s)"}

    with patch("main.AsyncResult", return_value=mock_result):
        res = client.get("/status/some-job-id")

    assert res.status_code == 200
    data = res.get_json()
    assert data["state"] == "progress"
    assert data["step"] == "Running OCR on 2 table(s)"


def test_status_success(client):
    mock_result = MagicMock()
    mock_result.state = "SUCCESS"
    mock_result.result = {
        "filename": "output.csv",
        "tables_found": 3,
        "ocr_failed": 0,
    }

    with patch("main.AsyncResult", return_value=mock_result):
        res = client.get("/status/some-job-id")

    assert res.status_code == 200
    data = res.get_json()
    assert data["state"] == "success"
    assert data["filename"] == "output.csv"
    assert data["tables_found"] == 3
    assert data["ocr_failed"] == 0


def test_status_success_with_partial_failure(client):
    mock_result = MagicMock()
    mock_result.state = "SUCCESS"
    mock_result.result = {
        "filename": "output.csv",
        "tables_found": 4,
        "ocr_failed": 2,
    }

    with patch("main.AsyncResult", return_value=mock_result):
        res = client.get("/status/some-job-id")

    data = res.get_json()
    assert data["ocr_failed"] == 2


def test_status_failure(client):
    mock_result = MagicMock()
    mock_result.state = "FAILURE"
    mock_result.info = Exception("OCR model crashed")

    with patch("main.AsyncResult", return_value=mock_result):
        res = client.get("/status/some-job-id")

    assert res.status_code == 200
    data = res.get_json()
    assert data["state"] == "failure"
    assert "OCR model crashed" in data["error"]


# ── /download ─────────────────────────────────────────────────────────────────

def test_download_not_found(client):
    res = client.get("/download/nonexistent.csv")
    assert res.status_code == 404


def test_download_success(client, output_dir):
    csv_content = b'"col1","col2"\n"val1","val2"'
    csv_path = os.path.join(output_dir, "result.csv")
    with open(csv_path, "wb") as f:
        f.write(csv_content)

    res = client.get("/download/result.csv")

    assert res.status_code == 200
    assert res.data == csv_content


def test_download_deletes_file_after_serving(client, output_dir):
    csv_path = os.path.join(output_dir, "todelete.csv")
    with open(csv_path, "w") as f:
        f.write("a,b,c")

    client.get("/download/todelete.csv")

    assert not os.path.exists(csv_path)
