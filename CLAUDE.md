# Fitness Dashboard — Project Instructions

## Project Rules

- **Never delete completed checklist items.** Mark them `[x]` instead. All progress must remain visible.
- The canonical project plan is `FITNESS_DASHBOARD_PLAN.md` — keep it up to date as decisions are made.
- Emphasize security in all decisions. Prefer the more secure option when trade-offs arise.
- Use Podman, not Docker. Use `Containerfile` instead of `Dockerfile`. Use `podman-compose.yml` instead of `docker-compose.yml`.
- Use Python virtual environments for local development.
- Training plan imports support both JSON and CSV formats.
- Discuss design decisions with the user before implementing. Don't assume — present options with trade-offs.
- When updating project docs (plan, hardware, etc.), edit in place. Don't rewrite from scratch unless necessary.

## Design Philosophy

- **Aggregator first** — the app compiles data from many sources into one view, it doesn't replace them
- **Show everything, recommend one** — always display all workout options; the app's pick is a suggestion with reasoning
- **No AI** — local algorithms based on established sports science (CTL/ATL/TSB, HRV analysis, etc.)
- **Portability** — containerized and config-driven; should run on laptop, Pi, home server, or VPS unchanged
- **Easy data import** — make it trivial to drop in new training plans via JSON or CSV

## Tech Stack

- **Backend:** Python + FastAPI
- **Database:** SQLite + Alembic
- **Frontend:** HTMX + Jinja2 (served by FastAPI)
- **Containers:** Podman (rootless) + podman-compose
- **Notifications:** ntfy (self-hosted)
- **Remote access:** Tailscale
- **Weather:** Open-Meteo

## Key Files

- `FITNESS_DASHBOARD_PLAN.md` — full project plan with phase checklists
- `HARDWARE_RECOMMENDATIONS.md` — Raspberry Pi purchasing guide
- `data/plan/` — training plans and workout libraries (JSON + CSV)
- `data/plan/templates/` — blank templates for new plans

## Data Sources

- **Intervals.icu** — REST API (primary fitness metrics: CTL/ATL/TSB/Form, VO2 max)
- **Garmin Connect** — garminconnect Python lib (sleep, HRV, Body Battery, Training Readiness, Training Status, Endurance Score). Uses unofficial API — riskiest integration, validate early.
- **TrainerRoad** — iCal feed (planned workouts only, no public API)
- **Training plans** — local JSON/CSV files using the generic template format
- **Open-Meteo** — weather (free, no API key)

## User Context

- Training for Ironman distance triathlon (swim/bike/run)
- Garmin Forerunner 955 Solar + additional Garmin cycling devices
- Actively uses intervals.icu and TrainerRoad
- Following 80/20 Triathlon plan (Ironman Distance Level 1, 22 weeks)
- Deploying to Raspberry Pi 4 4GB with Tailscale for remote access
- ISP uses DHCP (Tailscale solves the dynamic IP problem)

## User Preferences

- Emojis are fine to use
- Explain reasoning behind recommendations
- Prefer free/cheap and open source tooling
- Python and Java are the user's strongest languages
- The user runs Manjaro Linux and uses an Android phone
- Prefers to be consulted on design decisions rather than having them made for him
