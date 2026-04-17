from __future__ import annotations

import asyncio
from contextlib import suppress

from backend.app.services.ingest import IngestionPipeline


class IngestionWorker:
    def __init__(self, pipeline: IngestionPipeline) -> None:
        """Create a single-consumer ingestion worker. Input is an ingestion pipeline; output is a worker with an empty queue."""
        self.pipeline = pipeline
        self.queue: asyncio.Queue[str] = asyncio.Queue()
        self.task: asyncio.Task[None] | None = None

    def start(self, initial_job_ids: list[str]) -> None:
        """Start the background queue loop and enqueue recoverable jobs. Input is a list of job ids; output is no value."""
        if self.task is None:
            self.task = asyncio.create_task(self._run())
        for job_id in initial_job_ids:
            self.enqueue(job_id)

    def enqueue(self, job_id: str) -> None:
        """Queue one ingestion job for processing. Input is a job id; output is no value."""
        self.queue.put_nowait(job_id)

    async def stop(self) -> None:
        """Cancel and await the background worker task. Takes no input and returns after shutdown completes."""
        if self.task is None:
            return
        self.task.cancel()
        with suppress(asyncio.CancelledError):
            await self.task
        self.task = None

    async def _run(self) -> None:
        """Continuously process queued job ids. Takes queued ids as input from the async queue and returns only when cancelled."""
        while True:
            job_id = await self.queue.get()
            try:
                await self.pipeline.run(job_id)
            finally:
                self.queue.task_done()
