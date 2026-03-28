import os
import sys
import tempfile
import pytest
from unittest.mock import MagicMock

# ── Temp directories ──────────────────────────────────────────────────────────
_upload_dir = tempfile.mkdtemp(prefix="eco399_test_uploads_")
_output_dir = tempfile.mkdtemp(prefix="eco399_test_outputs_")

# ── Stub out heavy modules before any import ──────────────────────────────────
# paddlepaddle.py loads ML models at module level — mock the whole thing so
# tests don't need models installed or a GPU.
_paddlepaddle = MagicMock()
_paddlepaddle.UPLOAD_FOLDER = _upload_dir
_paddlepaddle.OUTPUT_FOLDER = _output_dir
_paddlepaddle.MAX_FILE_SIZE = 50 * 1024 * 1024
_paddlepaddle.allowed_file.side_effect = (
    lambda fname: "." in fname and fname.rsplit(".", 1)[1].lower() == "pdf"
)
sys.modules["paddlepaddle"] = _paddlepaddle

# celery_app.py would try to connect to Redis — mock it.
sys.modules["celery_app"] = MagicMock()

# tasks.process_pdf is called via .delay() — mock the whole module.
sys.modules["tasks"] = MagicMock()


@pytest.fixture(scope="session")
def app():
    from main import app as flask_app  # imported after mocks are in place
    flask_app.config["TESTING"] = True
    return flask_app


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture(scope="session")
def output_dir():
    return _output_dir


@pytest.fixture(autouse=True)
def reset_task_mock():
    sys.modules["tasks"].process_pdf.reset_mock()
    yield
