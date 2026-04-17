from __future__ import annotations

import asyncio
from contextlib import suppress

from backend.app.services.ingest import IngestionPipeline


class IngestionWorker:
    def __init__(self, pipeline: IngestionPipeline) -> None:
        self.pipeline = pipeline
        self.queue: asyncio.Queue[str] = asyncio.Queue()
        self.task: asyncio.Task[None] | None = None

    def start(self, initial_job_ids: list[str]) -> None:
        if self.task is None:
            self.task = asyncio.create_task(self._run())
        for job_id in initial_job_ids:
            self.enqueue(job_id)

    def enqueue(self, job_id: str) -> None:
        self.queue.put_nowait(job_id)

    async def stop(self) -> None:
        if self.task is None:
            return
        self.task.cancel()
        with suppress(asyncio.CancelledError):
            await self.task
        self.task = None

    async def _run(self) -> None:
        while True:
            job_id = await self.queue.get()
            try:
                await self.pipeline.run(job_id)
            finally:
                self.queue.task_done()
