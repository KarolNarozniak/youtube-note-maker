from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.app.constants import APP_NAME
from backend.app.dependencies import create_ingestion_pipeline, db
from backend.app.routers import chat, library
from backend.app.worker import IngestionWorker


@asynccontextmanager
async def lifespan(app: FastAPI):
    db.init()
    worker = IngestionWorker(create_ingestion_pipeline())
    app.state.worker = worker
    worker.start(db.recoverable_job_ids())
    try:
        yield
    finally:
        await worker.stop()


app = FastAPI(title=APP_NAME, version="0.1.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://127.0.0.1:5173", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(library.router)
app.include_router(chat.router)
