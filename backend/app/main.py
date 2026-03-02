import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from backend.app.api.status import router as status_router
from backend.app.api.sync import router as sync_router
from backend.app.sync.scheduler import setup_scheduler

logger = logging.getLogger(__name__)

# Module-level reference so API endpoints can inspect scheduler state
scheduler = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global scheduler
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)-8s %(name)s — %(message)s",
    )
    scheduler = setup_scheduler()
    scheduler.start()
    jobs = scheduler.get_jobs()
    if jobs:
        logger.info("Scheduler started — next run: %s", jobs[0].next_run_time)
    else:
        logger.info("Scheduler started — no jobs configured")
    yield
    scheduler.shutdown(wait=False)
    logger.info("Scheduler shut down")


app = FastAPI(title="T3Daily", version="0.1.0", lifespan=lifespan)
app.include_router(status_router)
app.include_router(sync_router)


@app.get("/health")
def health():
    return {"status": "ok"}
