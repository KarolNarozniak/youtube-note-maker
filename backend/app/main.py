from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.app.constants import APP_NAME
from backend.app.dependencies import create_ingestion_pipeline, db, settings
from backend.app.routers import chat, library
from backend.app.worker import IngestionWorker


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage backend startup and shutdown resources. Input is the FastAPI app; output is a lifespan context that starts/stops the worker."""
    db.init()
    worker = IngestionWorker(create_ingestion_pipeline())
    app.state.worker = worker
    worker.start(db.recoverable_job_ids())
    try:
        yield
    finally:
        await worker.stop()


app = FastAPI(title=APP_NAME, version="0.1.0", lifespan=lifespan)
frontend_origins = {
    f"http://{settings.frontend_host}:{settings.frontend_port}",
    f"http://localhost:{settings.frontend_port}",
}
app.add_middleware(
    CORSMiddleware,
    allow_origins=sorted(frontend_origins),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(library.router)
app.include_router(chat.router)
