# eco399 — PDF to CSV Converter

Extracts tables from PDF documents and converts them to CSV. Upload a PDF, and the app runs DETR table detection followed by PaddleOCR to extract table contents.

## Architecture

```
Browser → React (Vite) → Flask API → Celery worker → Redis
                                          │
                              PyMuPDF → DETR → PaddleOCR → CSV
```

- **Frontend:** React 19 + TypeScript + Tailwind CSS, served via Vite (dev) or Nginx (prod)
- **Backend:** Flask 3 handles uploads and status polling; Celery processes PDFs asynchronously
- **Models:** `TahaDouaji/detr-doc-table-detection` for table detection, PaddleOCR for text extraction
- **Broker:** Redis (job queue + result backend)

---

## Running Locally

### Prerequisites

- Python ≥ 3.12 with [Poetry](https://python-poetry.org/docs/#installation)
- Node.js ≥ 20 with npm
- Redis (`redis-server` or `brew install redis`)

### Install dependencies

```bash
make install
```

### Start Redis

```bash
redis-server
```

### Start all services

```bash
make run-all
```

This starts Flask (port 5000), the Celery worker, and the Vite dev server (port 3000) in the background. Open `http://localhost:3000`.

Or start each service individually in separate terminals:

```bash
make run-backend    # Flask on :5000
make run-worker     # Celery worker
make run-frontend   # Vite dev server on :3000
```

> **Note:** The Celery worker downloads PaddleOCR and DETR model weights on first run (~1–2 GB). This takes a few minutes but only happens once.

---

## Running with Docker

### Prerequisites

- [Docker](https://docs.docker.com/get-docker/) with the Compose plugin

### Build and start

```bash
docker compose up --build
```

Open `http://localhost`. The backend healthcheck waits for models to load before the frontend comes up — first start takes ~60–90s.

To rebuild only the worker (e.g. after changing `tasks.py`):

```bash
docker compose up --build worker
```

To stop and remove volumes:

```bash
docker compose down -v
```

---

## Deploying to a Remote Server

The `deploy/` directory contains two scripts for deploying to a Linux server over SSH.

### 1. Provision (one-time)

Installs Docker CE and configures the firewall (ports 22, 80, 443) on a fresh Ubuntu 22.04/24.04 server:

```bash
./deploy/provision.sh <host> [user] [ssh-key]

# Examples:
./deploy/provision.sh 192.168.1.100
./deploy/provision.sh 192.168.1.100 ubuntu ~/.ssh/my_key.pem
```

### 2. Deploy

Syncs code via rsync and restarts containers:

```bash
./deploy/deploy.sh <host> [user] [ssh-key]

# Examples:
./deploy/deploy.sh 192.168.1.100
./deploy/deploy.sh 192.168.1.100 ubuntu ~/.ssh/my_key.pem
```

Safe to run repeatedly — only changed files are transferred. The app will be live at `http://<host>` when the script completes.

---

## API

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/upload` | Upload a PDF. Returns `{job_id}`. |
| `GET` | `/status/<job_id>` | Poll job status. Returns state + step label, or result on completion. |
| `GET` | `/download/<filename>` | Download the output CSV. |
| `GET` | `/health` | Health check. |

### Status response states

| State | Meaning |
|-------|---------|
| `pending` | Job queued, not yet started |
| `progress` | Processing — `step` field describes current stage |
| `success` | Done — `filename` and `tables_found` fields present |
| `failure` | Error — `error` field contains the message |

---

## Processing Pipeline

1. **PDF → images** — PyMuPDF at 300 DPI
2. **Preprocessing** — denoising, CLAHE contrast enhancement, unsharp masking, adaptive binarization
3. **Table detection** — DETR (`TahaDouaji/detr-doc-table-detection`) finds and crops table regions
4. **OCR** — PaddleOCR runs on each cropped table
5. **CSV assembly** — OCR results grouped into rows by y-coordinate and written to CSV

Both ML models load once per worker process at startup.

---

## Development

### Backend only

```bash
cd backend
poetry run python src/main.py                                          # Flask on :5000
PYTHONPATH=src poetry run celery -A celery_app worker --loglevel=info  # Celery worker
```

### Frontend only

```bash
cd frontend
npm run dev    # Vite dev server on :3000
npm run build  # Production build
npm run lint   # ESLint
```

Vite proxies `/api/*` to `http://localhost:5000`, stripping the `/api` prefix before forwarding.

### Load testing

Locust is included as a dev dependency:

```bash
cd backend
poetry run locust -f locustfile.py --host http://localhost:5000
```

---

## Project Structure

```
eco399/
├── backend/
│   ├── src/
│   │   ├── main.py          # Flask app + routes
│   │   ├── celery_app.py    # Celery instance
│   │   ├── tasks.py         # process_pdf Celery task
│   │   └── paddlepaddle.py  # ML models + image processing pipeline
│   ├── uploads/             # Incoming PDFs (auto-created)
│   ├── outputs/             # Output CSVs (auto-created)
│   └── pyproject.toml
├── frontend/
│   ├── src/
│   │   ├── main.tsx
│   │   └── App.tsx
│   └── package.json
├── deploy/
│   ├── provision.sh         # One-time server setup
│   └── deploy.sh            # Code sync + container restart
├── docker-compose.yml
├── Dockerfile               # Backend image
└── Makefile
```
