# T3Daily

A personal fitness dashboard that aggregates data from Garmin Connect and Intervals.icu into a single view. Built for triathlon training — syncs wellness metrics, fitness data, and completed workouts on a daily schedule.

**Status:** Phase 1 (data pipeline) complete. The app syncs data and exposes API endpoints. Dashboard UI coming in a later phase.

## What it does

- Pulls daily wellness data from **Garmin Connect** (HRV, sleep, Body Battery, Training Readiness, Training Status, Endurance Score, resting HR, stress)
- Pulls fitness metrics from **Intervals.icu** (CTL, ATL, TSB, VO2max, completed activities)
- Stores everything in SQLite with automatic daily sync via APScheduler
- Exposes API endpoints for health checks, sync status, and on-demand sync triggers

## Prerequisites

- Python 3.12+ (developed on 3.14)
- [pyenv](https://github.com/pyenv/pyenv) (recommended for managing Python versions)
- A Garmin Connect account with a compatible device
- An Intervals.icu account with an API key
- Podman + podman-compose (for containerized deployment, optional for local dev)

## Getting your API credentials

### Garmin Connect
Just use your normal Garmin Connect login email and password. The app uses the `garminconnect` library which authenticates via the unofficial API.

> **Note:** First-time authentication may trigger CAPTCHA or MFA on Garmin's side. If this happens, you may need to log in via browser first and then retry.

### Intervals.icu
1. Go to [intervals.icu](https://intervals.icu) and log in
2. Click your profile icon → **Settings** → **Developer**
3. Generate an API key
4. Your athlete ID is shown on the same page (starts with `i`, e.g. `i12345`)

## Setup (local development)

### 1. Clone and create virtual environment

```bash
git clone <repo-url> T3Daily
cd T3Daily

# Create and activate a virtualenv (using pyenv)
pyenv virtualenv 3.14.3 T3Daily    # or your Python version
pyenv activate T3Daily
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure environment

```bash
cp .env.example .env
```

Edit `.env` with your credentials:

```bash
# Required — Garmin Connect
GARMIN_EMAIL=you@example.com
GARMIN_PASSWORD=your-password

# Required — Intervals.icu
INTERVALS_API_KEY=your-api-key
INTERVALS_ATHLETE_ID=i12345

# Optional — customize sync schedule (defaults shown)
SYNC_HOUR=5
SYNC_MINUTE=0
TZ=America/Denver
```

### 4. Initialize the database

```bash
alembic upgrade head
```

This creates `data/db/t3daily.db` with all tables in WAL mode.

### 5. Run the app

```bash
uvicorn backend.app.main:app --host 127.0.0.1 --port 8000
```

The scheduler starts automatically and will sync daily at the configured time.

## Setup (containerized with Podman)

```bash
cp .env.example .env
# Edit .env with your credentials

podman-compose up --build
```

The container runs migrations on startup, then starts the app on port 8000 (bound to localhost only). Data persists across restarts via volume mounts.

## API endpoints

### `GET /health`
Liveness check. Returns `200 OK` if the app is running.

```bash
curl http://localhost:8000/health
# {"status":"ok"}
```

### `GET /status`
Returns sync health, data freshness, and scheduler state.

```bash
curl http://localhost:8000/status
```

Example response:
```json
{
  "status": "ok",
  "sources": {
    "garmin": {"status": "success", "rows_synced": 3},
    "intervals_icu": {"status": "success", "rows_synced": 21}
  },
  "data": {
    "wellness": {"count": 3, "latest": "2026-03-01"},
    "fitness_metrics": {"count": 14, "latest": "2026-03-01"},
    "activities": {"count": 7, "latest": "2026-02-28"}
  },
  "scheduler": {
    "running": true,
    "jobs": [{"id": "daily_sync", "next_run": "2026-03-02T05:00:00-06:00"}]
  }
}
```

### `POST /sync`
Trigger an on-demand sync. Useful for initial data load and debugging.

```bash
# Sync all sources
curl -X POST http://localhost:8000/sync

# Sync only Garmin, last 7 days
curl -X POST http://localhost:8000/sync \
  -H "Content-Type: application/json" \
  -d '{"source": "garmin", "days_back": 7}'

# Sync only Intervals.icu, last 30 days
curl -X POST http://localhost:8000/sync \
  -H "Content-Type: application/json" \
  -d '{"source": "intervals_icu", "days_back": 30}'
```

## First run checklist

1. Start the app: `uvicorn backend.app.main:app --host 127.0.0.1 --port 8000`
2. Trigger initial sync: `curl -X POST http://localhost:8000/sync -H "Content-Type: application/json" -d '{"source": "all", "days_back": 14}'`
3. Check status: `curl http://localhost:8000/status`
4. Verify data in DB: `sqlite3 data/db/t3daily.db "SELECT date, hrv_rmssd, training_readiness FROM wellness ORDER BY date DESC LIMIT 5"`

## Project structure

```
T3Daily/
├── backend/
│   └── app/
│       ├── api/                 # FastAPI route handlers
│       │   ├── status.py        #   GET /status
│       │   └── sync.py          #   POST /sync
│       ├── models/              # SQLAlchemy models
│       │   ├── activity.py      #   completed workouts
│       │   ├── fitness.py       #   CTL/ATL/TSB/VO2max
│       │   ├── settings.py      #   user config
│       │   ├── sync_log.py      #   sync tracking
│       │   └── wellness.py      #   Garmin daily data
│       ├── sync/                # Data sync services
│       │   ├── garmin.py        #   Garmin Connect client
│       │   ├── intervals_icu.py #   Intervals.icu client
│       │   └── scheduler.py     #   APScheduler setup
│       ├── migrations/          # Alembic migrations
│       ├── config.py            # pydantic-settings config
│       ├── database.py          # SQLAlchemy engine + session
│       └── main.py              # FastAPI app entrypoint
├── data/
│   ├── db/                      # SQLite database (gitignored)
│   ├── garmin_tokens/           # Garth auth tokens (gitignored)
│   └── plan/                    # Training plans (JSON/CSV)
├── .env.example                 # Environment variable template
├── alembic.ini                  # Alembic config
├── Containerfile                # Container image definition
├── podman-compose.yml           # Container orchestration
└── requirements.txt             # Python dependencies
```

## Troubleshooting

**Garmin returns authentication errors:**
Delete `data/garmin_tokens/` and restart. If CAPTCHA is triggered, log into Garmin Connect via your browser first, then retry.

**Intervals.icu returns 404:**
Double-check your `INTERVALS_ATHLETE_ID` in `.env` — it should start with `i` (e.g., `i12345`).

**"address already in use" on startup:**
Another process is using port 8000. Find and kill it with `fuser -k 8000/tcp`, or run on a different port: `uvicorn backend.app.main:app --port 8001`.
