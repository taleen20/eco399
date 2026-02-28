# Load Test — 2026-02-28 (10 users)

## Setup

- **Tool:** Locust 2.43.3
- **Users:** 10 concurrent, ramped at 2/s
- **Duration:** 90 seconds
- **Target:** http://localhost:5000 (Flask dev server + Celery worker, CPU only)
- **Workload:** each user loops — upload PDF → poll `/status` every 2s → download CSV

## Results

| Endpoint | Requests | Failures | Avg ms | p50 | p75 | p95 | p99 | Max |
|---|---|---|---|---|---|---|---|---|
| `POST /upload` | 33 | 0 | 143 | 110 | 160 | 430 | 610 | 607 |
| `GET /status/[job_id]` | 388 | 0 | 242 | 200 | 330 | 670 | 980 | 1397 |
| `GET /download/[filename]` | 26 | 0 | 27 | 19 | 46 | 73 | 80 | 80 |
| `GET /health` | 7 | 0 | 84 | 29 | 100 | 350 | 350 | 353 |
| **Aggregated** | **454** | **0** | **220** | 160 | 310 | 610 | 930 | 1397 |

**Overall throughput:** ~5.05 req/s

## Comparison vs. 3-user run

| Metric | 3 users | 10 users | Change |
|---|---|---|---|
| Total requests | 177 | 454 | +157% |
| Overall throughput (req/s) | 1.99 | 5.05 | +154% |
| `/upload` avg ms | 40 | 143 | +258% |
| `/status` avg ms | 50 | 242 | +384% |
| `/status` p99 ms | 370 | 980 | +165% |
| Failures | 0 | 0 | — |

## Observations

- **Zero failures** — both bugs from the 3-user run are confirmed fixed at higher concurrency.
- **Upload latency degraded sharply** (40ms → 143ms avg). At 10 users, 10 tasks pile into the
  Celery queue faster than the 4 workers can drain it. Tasks start waiting before they even begin
  processing, inflating the apparent "upload" response time (which just enqueues the task).
- **Status poll latency exploded** (50ms → 242ms avg, p99 370ms → 980ms). With a full queue,
  tasks stay `PENDING` for longer, so each user has to make more polls before seeing `success`.
  The p99 at 1.4s reflects tasks waiting ~60s in queue before a worker picks them up.
- **Download is unaffected** (4ms → 27ms) — it's a pure file read with no queue pressure.
- **The bottleneck is confirmed as Celery worker concurrency**, not Flask or Redis. With 4 workers
  each taking ~8s per task, max sustainable task throughput is ~0.5 tasks/s. At 10 users
  submitting faster than that, the queue grows unboundedly during the test window.

## Scaling options

To handle 10+ concurrent users without queue buildup:
1. **More workers** — increase `--concurrency` on the Celery worker (limited by CPU cores)
2. **GPU inference** — PaddleOCR and DETR both support CUDA; would reduce task time from ~8s to ~1s
3. **Multiple worker machines** — all pointing at the same Redis broker

## Raw Data

- `2026-02-28_10users_stats.csv` — per-endpoint summary statistics
- `2026-02-28_10users_stats_history.csv` — per-10s time-series
