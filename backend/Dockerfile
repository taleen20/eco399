FROM python:3.12-slim

# System deps for OpenCV (libgl1, libglib2.0-0) and PaddlePaddle (libgomp1)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender1 \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir "poetry>=2.0.0,<3.0.0"

WORKDIR /app

# Install deps first for layer caching — only re-runs when lockfile changes
COPY pyproject.toml poetry.lock ./
RUN poetry config virtualenvs.create false \
    && poetry install --only main --no-interaction --no-ansi

COPY src/ ./src/

ENV PYTHONPATH=/app/src

RUN mkdir -p uploads outputs

# Default: Flask via gunicorn (override with celery worker command in docker-compose)
CMD ["gunicorn", "-w", "2", "-b", "0.0.0.0:5000", "--timeout", "120", "main:app"]
