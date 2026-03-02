# Phase 1: Data Pipeline Implementation Plan

## Context

Phase 0 (pre-code setup) is complete — we have 479 workout descriptions, the 22-week training plan, and all credentials ready. Phase 1 builds the foundational data pipeline: a FastAPI app that syncs data from Garmin Connect and Intervals.icu into SQLite, with scheduled and on-demand sync capability. Everything downstream (dashboard, recommendations, notifications) depends on this data layer working reliably.

## Design Decisions

1. **Containerfile deferred to end of Phase 1** — validate sync layer locally first, containerize once it works
2. **FastAPI skeleton first, then Garmin immediately after** — need somewhere to store data, but Garmin is riskiest so validate early
3. **Single initial Alembic migration** — greenfield project, no production data, one migration for all Phase 1 tables
4. **APScheduler in-process via FastAPI lifespan** — single container, single process, simple for a single-user Pi app
5. **SQLite WAL mode** — enables concurrent reads while scheduler writes
6. **httpx for Intervals.icu** — async-capable, pairs well with FastAPI (using sync client for background jobs)
7. **APScheduler 3.x** (not 4.x) — 4.x is a rewrite with different API, 3.x is stable

## Implementation Steps

### Step 1: Project scaffolding
Create the runnable skeleton with a `/health` endpoint.

**New files:**
- `.gitignore` — exclude `.env`, `data/db/*.db`, `data/garmin_tokens/`, `__pycache__/`
- `.env.example` — template with `GARMIN_EMAIL`, `GARMIN_PASSWORD`, `GARMIN_TOKEN_DIR`, `INTERVALS_API_KEY`, `INTERVALS_ATHLETE_ID`, `DATABASE_URL`, `SYNC_HOUR`, `SYNC_MINUTE`, `TZ`
- `requirements.txt` — fastapi, uvicorn[standard], sqlalchemy, alembic, garminconnect, httpx, apscheduler (3.x), python-dotenv, pydantic-settings
- `backend/__init__.py`, `backend/app/__init__.py`
- `backend/app/config.py` — pydantic-settings `Settings` class loading from `.env`
- `backend/app/database.py` — SQLAlchemy 2.0 engine, session factory, `Base` class, WAL mode pragma
- `backend/app/main.py` — minimal FastAPI app with `/health`

**Verify:** `pip install -r requirements.txt && uvicorn backend.app.main:app`, `curl localhost:8000/health` returns 200

### Step 2: Database models + Alembic migration
Define all Phase 1 tables and create the initial migration.

**New files:**
- `backend/app/models/__init__.py` — re-exports all models
- `backend/app/models/wellness.py` — daily Garmin data (HRV, sleep, body battery, training readiness, etc.)
- `backend/app/models/fitness.py` — daily Intervals.icu data (CTL, ATL, TSB, VO2max)
- `backend/app/models/activity.py` — completed workouts from Intervals.icu
- `backend/app/models/settings.py` — single-row user config (plan start date, location, sleep target)
- `backend/app/models/sync_log.py` — last sync status per source
- `alembic.ini` + `backend/app/migrations/env.py` + `versions/001_initial_schema.py`

**Tables:** `settings`, `wellness`, `fitness_metrics`, `activities`, `sync_log`

**Table schemas:**

#### settings (single-row user profile)
| Column | Type | Notes |
|--------|------|-------|
| id | INTEGER PK | Always 1 |
| plan_start_date | DATE | |
| sleep_target_hours | FLOAT | e.g. 7.5 |
| latitude | FLOAT | For weather |
| longitude | FLOAT | For weather |
| timezone | TEXT | e.g. "America/New_York" |
| created_at | DATETIME | |
| updated_at | DATETIME | |

#### wellness (daily Garmin data)
| Column | Type | Notes |
|--------|------|-------|
| id | INTEGER PK | |
| date | DATE UNIQUE | |
| hrv_rmssd | FLOAT | Overnight HRV (ms) |
| hrv_status | TEXT | "balanced", "low", "high" |
| sleep_duration_seconds | INTEGER | |
| sleep_score | INTEGER | 0-100 |
| deep_sleep_seconds | INTEGER | |
| rem_sleep_seconds | INTEGER | |
| light_sleep_seconds | INTEGER | |
| awake_seconds | INTEGER | |
| body_battery_high | INTEGER | Daily high |
| body_battery_low | INTEGER | Daily low |
| body_battery_morning | INTEGER | Value at wake |
| resting_hr | INTEGER | |
| stress_avg | INTEGER | |
| training_readiness | INTEGER | 0-100 |
| training_readiness_hrv | FLOAT | Sub-component |
| training_readiness_sleep | FLOAT | Sub-component |
| training_readiness_recovery | FLOAT | Sub-component |
| training_readiness_load | FLOAT | Sub-component |
| training_status | TEXT | "Productive", "Recovery", etc. |
| endurance_score | INTEGER | |
| recovery_time_minutes | INTEGER | |
| source | TEXT | Default 'garmin' |
| created_at | DATETIME | |
| updated_at | DATETIME | |

#### fitness_metrics (daily Intervals.icu data)
| Column | Type | Notes |
|--------|------|-------|
| id | INTEGER PK | |
| date | DATE UNIQUE | |
| ctl | FLOAT | Chronic Training Load (fitness) |
| atl | FLOAT | Acute Training Load (fatigue) |
| tsb | FLOAT | Training Stress Balance = CTL - ATL |
| ramp_rate | FLOAT | Weekly CTL change |
| vo2max_run | FLOAT | |
| vo2max_cycle | FLOAT | |
| source | TEXT | Default 'intervals_icu' |
| created_at | DATETIME | |
| updated_at | DATETIME | |

#### activities (completed workouts from Intervals.icu)
| Column | Type | Notes |
|--------|------|-------|
| id | INTEGER PK | |
| external_id | TEXT UNIQUE | Intervals.icu activity ID for dedup |
| date | DATE | |
| sport | TEXT | "run", "bike", "swim", etc. |
| name | TEXT | |
| duration_seconds | INTEGER | |
| distance_meters | FLOAT | |
| tss | FLOAT | Training Stress Score |
| hr_avg | INTEGER | |
| hr_max | INTEGER | |
| power_avg | FLOAT | |
| power_normalized | FLOAT | |
| calories | INTEGER | |
| description | TEXT | |
| source | TEXT | Default 'intervals_icu' |
| created_at | DATETIME | |

#### sync_log (sync status per source)
| Column | Type | Notes |
|--------|------|-------|
| id | INTEGER PK | |
| source | TEXT UNIQUE | "garmin", "intervals_icu" |
| last_success | DATETIME | |
| last_attempt | DATETIME | |
| last_error | TEXT | |
| records_synced | INTEGER | |
| created_at | DATETIME | |

**Verify:** `alembic upgrade head`, then `sqlite3 data/db/t3daily.db ".tables"` shows all 5 tables

### Step 3: Garmin sync module (riskiest — validate first)
Authenticate and pull sleep, HRV, body battery, training readiness, training status, endurance score, resting HR.

**New files:**
- `backend/app/sync/__init__.py`
- `backend/app/sync/garmin.py` — `GarminSyncService` class with token persistence via garth, defensive parsing (fields may be null), upsert by date

**Key details:**
- Token persistence in `data/garmin_tokens/` (mounted volume later)
- Try loading saved tokens first, fall back to full login
- Wrap each API call individually so one failure doesn't block others
- Sync today + previous N days (default 2) to catch late-arriving data
- Garmin API methods: `get_sleep_data()`, `get_hrv_data()`, `get_body_battery()`, `get_training_readiness()`, `get_training_status()`, `get_endurance_score()`, `get_rhr_day()`

**Verify:** Manual test script pulls data, rows appear in `wellness` table

### Step 4: Intervals.icu sync module
Pull CTL/ATL/TSB/VO2max from wellness endpoint and recent activities.

**New files:**
- `backend/app/sync/intervals_icu.py` — `IntervalsIcuSyncService` class using httpx with Basic auth (`API_KEY` / api_key)

**Endpoints used:**
- `GET /api/v1/athlete/{id}/wellness?oldest=...&newest=...` — CTL (`ctl`), ATL (`atl`), ramp rate
- `GET /api/v1/athlete/{id}/activities?oldest=...&newest=...` — completed workouts
- Activities deduped on `external_id`

**Verify:** Manual test script pulls data, rows appear in `fitness_metrics` and `activities` tables

### Step 5: APScheduler integration
Wire up automatic daily sync.

**New files:**
- `backend/app/sync/scheduler.py` — `run_sync_all()` function, `setup_scheduler()` factory

**Modified files:**
- `backend/app/main.py` — add `lifespan` context manager to start/stop scheduler

**Details:**
- `BackgroundScheduler` (not AsyncIO) — sync functions are synchronous, runs in thread pool
- CronTrigger at configured hour/minute in configured timezone
- Error isolation: Garmin failure doesn't block Intervals.icu sync

### Step 6: API endpoints (`/status`, `/sync`)
Monitoring and manual trigger endpoints.

**New files:**
- `backend/app/api/__init__.py`
- `backend/app/api/status.py` — `GET /status` returns sync health, data freshness, scheduler state
- `backend/app/api/sync.py` — `POST /sync` triggers on-demand sync with optional `source` and `days_back` params

**Verify:** `curl localhost:8000/status` shows green, `curl -X POST localhost:8000/sync` triggers sync

### Step 7: Containerfile + podman-compose
Package the working pipeline.

**New files:**
- `Containerfile` — python:3.12-slim, pip install, copy backend + data, expose 8000
- `podman-compose.yml` — single `app` service, volumes for db + garmin tokens + plan data (read-only), port bound to 127.0.0.1 only, env_file from `.env`

**Verify:** `podman-compose up --build`, `curl localhost:8000/status`, data persists across restarts

## Potential Risks

| Risk | Impact | Mitigation |
|------|--------|------------|
| Garmin CAPTCHA/MFA | Auth blocked | First-time manual browser step; fallback to Intervals.icu for partial data |
| Intervals.icu field names | Wrong data mapping | Inspect actual API response, adapt field names |
| SQLite locking | Concurrent access errors | WAL mode + `check_same_thread=False` |
| Garmin rate limiting | Throttled requests | Sync only 2-3 days, once daily, exponential backoff |
| garminconnect lib breakage | No Garmin data | Community patches typically within days; Intervals.icu fallback |

## End-to-End Verification
1. `podman-compose up --build`
2. `curl localhost:8000/health` → 200
3. `curl -X POST localhost:8000/sync -H "Content-Type: application/json" -d '{"source":"all"}'` → sync results
4. `curl localhost:8000/status` → all sources green, data counts > 0
5. `sqlite3 data/db/t3daily.db "SELECT date, hrv_rmssd, training_readiness FROM wellness ORDER BY date DESC LIMIT 3"` → recent data
