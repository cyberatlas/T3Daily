# Fitness Dashboard — Project Plan

## Overview

A self-hosted, containerized fitness intelligence dashboard that aggregates data from
Intervals.icu, Garmin Connect, TrainerRoad, and your 80/20 Triathlon plan. Runs on a
Raspberry Pi via Docker Compose, accessible anywhere via Tailscale, with push
notifications via self-hosted ntfy.

The app is a **single-pane-of-glass** for all your training data — it compiles every
data source and plan into one place, shows all recommendations side by side (Garmin,
TrainerRoad, 80/20, and its own), and lets you decide at a glance what to do today.

---

## Design Principles

- **Aggregator first** — the app's value is compiling data from many sources, not replacing them
- **Show everything, recommend one** — always display all options; the app's pick is a suggestion, not a mandate
- **No AI** — local algorithms based on established sports science
- **Security by default** — no exposed ports, no cloud storage, credentials never in code
- **Portable** — containerized, config-driven, eventually multi-user capable

---

## Stack

| Layer | Tool | Why |
|---|---|---|
| Backend | Python + FastAPI | Your strongest language, excellent ecosystem |
| Database | SQLite (+ Alembic migrations) | No separate server, file-based, easy backup |
| Scheduling | APScheduler | Lightweight, built into the Python process |
| Frontend | HTMX + Jinja2 | No separate build step, served by FastAPI |
| Push notifications | ntfy (self-hosted) | Open source, free, private, Android app available |
| Remote access | Tailscale | Solves dynamic IP, no exposed ports, encrypted |
| Weather | Open-Meteo | Free, no API key, no account |
| Containerization | Docker Compose | Same config across laptop, Pi, home server, or VPS |

---

## Data Sources

| Source | Method | Notes |
|---|---|---|
| Intervals.icu | REST API | CTL/ATL/TSB/Form, VO2 max, wellness, activities, planned workouts |
| Garmin Connect | garminconnect Python lib | Sleep, HRV, Body Battery, Training Status, Training Readiness, Endurance Score, Resting HR |
| TrainerRoad | iCal feed | Planned workouts — enable in TR Settings → Calendar |
| 80/20 Plan | Local JSON (manual transcription) | Weekly schedule chart from book |
| 80/20 Workout Library | Local JSON | Code → description, type, intensity zones |
| Weather | Open-Meteo | Free, no API key, privacy-respecting |

### Known Risks

**Garmin Connect** — the `garminconnect` Python library uses an unofficial API. Garmin
has historically broken third-party clients with auth changes (CAPTCHA, MFA, session
tokens). Fallback options if this breaks:
- Garmin data also syncs to intervals.icu (some metrics available there)
- Garmin Connect can export CSV/JSON manually
- Community typically patches the library within days of breakage

---

## Project Structure

```
fitness-dashboard/
├── docker-compose.yml
├── .env.example
├── .gitignore
├── alembic.ini
├── backend/
│   ├── Dockerfile
│   ├── requirements.txt
│   └── app/
│       ├── main.py
│       ├── config.py
│       ├── database.py
│       ├── models/
│       │   ├── wellness.py        # HRV, sleep, Body Battery, etc.
│       │   ├── activity.py        # Completed workouts
│       │   ├── fitness.py         # CTL, ATL, TSB, VO2 max
│       │   └── settings.py        # User settings / profile
│       ├── migrations/            # Alembic migrations
│       │   └── versions/
│       ├── sync/
│       │   ├── garmin.py          # garminconnect integration
│       │   ├── intervals.py       # intervals.icu REST API
│       │   ├── trainerroad.py     # iCal feed parser
│       │   └── scheduler.py       # APScheduler jobs
│       ├── algorithms/
│       │   ├── recovery.py        # Recovery score (0-100)
│       │   ├── recommendation.py  # Workout ranking + reasoning
│       │   └── clothing.py        # Weather-based outfit logic
│       ├── api/
│       │   ├── dashboard.py       # Main dashboard endpoint
│       │   ├── workouts.py        # Workout views
│       │   ├── trends.py          # VO2 max, TSB trends
│       │   └── sync.py            # Manual sync trigger
│       └── notifications/
│           └── ntfy.py
├── frontend/
│   ├── templates/
│   │   ├── base.html
│   │   ├── dashboard.html
│   │   └── trends.html
│   ├── manifest.json              # PWA manifest
│   ├── sw.js                      # Service worker
│   └── static/
│       └── css/
├── data/
│   ├── plan/
│   │   ├── 8020_schedule.json     # Week/day → workout code
│   │   └── 8020_workouts.json     # Code → description, type, zones
│   └── db/                        # SQLite lives here (mounted volume)
└── ntfy/
    └── server.yml                 # ntfy config
```

---

## Database Schema

```
settings          — user profile: plan start date, sleep target hours, location
                   (lat/lon for weather), notification time, sport balance targets,
                   clothing inventory/preferences

wellness          — daily: HRV, sleep duration, sleep stages, Body Battery,
                   resting HR, stress, Training Readiness, Training Status,
                   Endurance Score, recovery time

fitness_metrics   — daily: CTL, ATL, TSB, Form, VO2 max (run + cycling)

activities        — completed workouts: sport, duration, TSS, HR, power

planned_workouts  — from TrainerRoad iCal + intervals.icu events

recommendations   — cached daily recommendation + reasoning text

sync_log          — last successful sync timestamp per source
```

---

## Algorithms (no AI)

### Recovery Score (0–100)

A composite score that aggregates recovery signals from all data sources into one
number. This intentionally overlaps with Garmin Training Readiness — the goal is to
compile all sources (Garmin, intervals.icu, recent training load) into a unified view,
not to replace any single metric.

Weighted combination of:
- HRV vs your 7-day baseline (highest weight)
- Garmin Training Readiness (high weight — already a composite, displayed alongside)
- Body Battery at wake
- Sleep duration vs target (from settings)
- Sleep quality (REM + deep % from Garmin)
- Resting HR vs baseline
- TSB (Training Stress Balance, from intervals.icu)

The dashboard always shows **both** the app's recovery score and Garmin's Training
Readiness side by side so you can compare and calibrate.

### 80/20 Plan Tracking

The app tracks your position in the 80/20 plan using:
- **Plan start date** (stored in settings)
- **Current week/day** calculated from start date
- **Handling gaps** — missed days don't shift the plan; the plan stays anchored to the
  calendar. If you miss a workout, it shows as missed and the smart pick logic can
  suggest catching up on key sessions later in the week.

### Workout Recommendation Logic

For each of the 4 candidate workouts (TrainerRoad, 80/20 strict, 80/20 smart pick, Garmin):
1. Score intensity match against recovery state
2. Score sport balance (swim/bike/run ratio over last 7 days)
3. Score TSS appropriateness (projected TSS vs current fatigue)
4. Pick highest score — that is the recommendation
5. Generate plain-English reasoning from the actual data points

Example output:
```
RECOMMENDATION: RF2 (Easy Run, 45 min) from your 80/20 plan

Why: HRV is 14% below baseline. Body Battery at 38. TSB is -22
(fatigued). Garmin Training Readiness is 32 (low). TrainerRoad has
a hard bike (95 TSS) scheduled — not advisable today. RF2 is
low-zone, different muscle group from yesterday's ride, keeps your
weekly run volume on track.

All options:
  TrainerRoad:    CF-90 (hard bike, 90 min, 95 TSS)
  80/20 strict:   RF2 (easy run, 45 min)         ← today's plan
  80/20 smart:    RF2                             ← same here
  Garmin:         Easy run, 30–40 min
  App pick:       RF2 ✓
```

### Clothing Logic

Per activity (cycling / running / walking):
- Temperature + wind chill → base layer decision
- Precipitation → waterproof yes/no
- Returns 2–3 outfit options ranked by comfort
- Configurable: user specifies what clothing they own (stored in settings)

---

## Build Phases

### Phase 0 — Pre-code Setup (one-time, done by you)
- [ ] Enable TrainerRoad iCal calendar feed (Settings → Calendar)
- [ ] Get Intervals.icu API key (Settings → API)
- [ ] Have Garmin Connect username + password ready
- [ ] Transcribe 80/20 plan chart to `8020_schedule.json`
- [ ] Build `8020_workouts.json` from book descriptions
- [ ] Install Docker + Docker Compose on laptop and Pi
- [ ] Install Tailscale on Pi and Android phone

### Phase 1 — Data Pipeline
- FastAPI skeleton + SQLite setup with Alembic migrations
- Settings table with plan start date, location, sleep target
- Garmin sync: sleep, HRV, Body Battery, Training Readiness, Training Status, Endurance Score
- Intervals.icu sync: CTL/ATL/TSB/Form, VO2 max, wellness
- APScheduler: syncs every morning at 6am + on-demand endpoint
- `/status` endpoint to verify all sources are returning data
- `/sync` manual trigger endpoint for debugging
- **Validate Garmin auth early** — this is the riskiest integration

### Phase 2 — Workout Sources
- TrainerRoad iCal parser → today's planned workout
- 80/20 JSON loader → strict plan workout for today (using plan start date to calculate current week/day)
- Garmin suggested workout via API
- API endpoint returning all 4 raw workout options for today

### Phase 3 — Recommendation Engine
- Recovery score algorithm
- Workout scoring + smart 80/20 pick logic
- Recommendation with plain-English reasoning
- Daily recommendation cached to DB at sync time

### Phase 4 — Dashboard Frontend
- PWA shell (installable on Android home screen)
- Daily dashboard: recovery score + Garmin Training Readiness side by side, all 5 workout views, key metrics
- Trends view: TSB over time, VO2 max trend, sleep trend

### Phase 5 — Push Notifications
- ntfy container added to Docker Compose
- Morning notification (7am): recovery score + recommended workout
- ntfy Android app on phone pointed at Tailscale address

### Phase 6 — Weather & Clothing
- Open-Meteo integration (hourly forecast for user's location from settings)
- Clothing recommendation logic for cycling, running, walking
- Clothing inventory config (what you own)
- Multiple outfit options per activity displayed on dashboard

### Phase 7 — Hardening
- Move Garmin credentials from `.env` to Docker secrets or Python `keyring`
- Basic auth on the web interface
- HTTPS via Tailscale's built-in cert (free, automatic)
- Rate limiting on API endpoints
- Structured logging
- Automated SQLite backup (daily, 30-day retention)
- Data retention policy: archive or prune old activity/wellness data
- `.env.example` fully documented

### Phase 8 — Android Widget
- KWGT or Tasker-based widget pulling from the dashboard API
- Or: native Android widget using a lightweight Kotlin/Java wrapper
- Shows at-a-glance on home screen: recovery score, today's recommended workout, next planned workout
- Tapping opens the full PWA dashboard

### Phase 9 — Multi-user & Portability
- User accounts with registration and login (replaces basic auth)
- Per-user settings, data isolation, and credential storage
- Each user connects their own Garmin, intervals.icu, and TrainerRoad
- Each user imports their own training plan
- Designed so a friend can run their own instance or create an account on yours
- Migration path: SQLite → PostgreSQL if needed for concurrent multi-user access

---

## Security Model

- **No ports exposed to the internet** — Tailscale only (until Phase 9 multi-user, if hosted)
- **Garmin credentials** in `.env` initially, migrated to Docker secrets or keyring in Phase 7
- **All health data stays on your hardware** — Pi or home server
- **HTTPS** via Tailscale's built-in TLS (no cert management needed)
- **Basic auth** gates the web UI (upgraded to proper auth in Phase 9)
- **`.env` never committed** — `.gitignore` enforced from day one
- **ntfy self-hosted** — notification content never hits external servers
- **Multi-user isolation** — in Phase 9, users cannot see each other's data

---

## Garmin Forerunner 955 Solar — Available Metrics

| Metric | Available | Notes |
|---|---|---|
| Training Readiness | Yes | 0–100 composite score |
| HRV Status | Yes | Overnight 5-min measurement + trend |
| Body Battery | Yes | 0–100 |
| Training Status | Yes | Productive / Peaking / Recovery / Strained / etc. |
| Endurance Score | Yes | Newer metric, 955 supports it |
| VO2 Max | Yes | Running + cycling |
| Recovery Time | Yes | Hours until ready |
| Sleep Stages | Yes | Light / deep / REM |

Additional Garmin cycling devices sync to the same Garmin Connect account —
power, cycling dynamics, etc. come through automatically.

---

## Pre-code Checklist (Phase 0 detail)

Before writing any code, gather:

1. **Intervals.icu API key** — Profile → Settings → API
2. **TrainerRoad iCal URL** — Settings → Calendar → Export
3. **Garmin Connect credentials** — username + password
4. **80/20 schedule JSON** — we will provide the format, you transcribe from book
5. **80/20 workout library JSON** — we will provide format + help populate codes

---

## Next Step

Start with **Phase 1**: get data flowing from Garmin and Intervals.icu and verify
it before building anything else. No point building a dashboard if the sync layer
doesn't work. Validate Garmin auth first since it's the riskiest integration.
