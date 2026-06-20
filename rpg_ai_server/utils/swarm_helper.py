from __future__ import annotations

import asyncio
import random
import time
from typing import Any, Callable, Coroutine


class SwarmJob:
    def __init__(self, job_id: str, payload: dict, handler: Callable[[dict], dict]):
        self.job_id = job_id
        self.payload = payload
        self.handler = handler
        self.result: dict | None = None
        self.error: str | None = None
        self.duration: float = 0.0


class SwarmBatch:
    def __init__(self, jobs: list[SwarmJob]):
        self.jobs = jobs
        self.completed: list[SwarmJob] = []
        self.failed: list[SwarmJob] = []
        self.skipped: list[SwarmJob] = []
        self.start_time: float = 0.0
        self.end_time: float = 0.0

    @property
    def total_duration(self) -> float:
        return self.end_time - self.start_time if self.end_time > self.start_time else 0.0

    @property
    def summary(self) -> dict:
        return {
            "total": len(self.jobs),
            "completed": len(self.completed),
            "failed": len(self.failed),
            "skipped": len(self.skipped),
            "duration_ms": round(self.total_duration * 1000, 1),
        }


def _run_job(job: SwarmJob) -> SwarmJob:
    start = time.time()
    try:
        job.result = job.handler(job.payload)
        job.duration = time.time() - start
    except Exception as e:
        job.error = str(e)
        job.duration = time.time() - start
    return job


async def _run_job_async(job: SwarmJob) -> SwarmJob:
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, _run_job, job)


async def swarm_process(
    jobs: list[SwarmJob],
    concurrency: int = 5,
) -> SwarmBatch:
    batch = SwarmBatch(jobs)
    batch.start_time = time.time()

    semaphore = asyncio.Semaphore(concurrency)

    async def _process(job: SwarmJob) -> SwarmJob:
        async with semaphore:
            result = await _run_job_async(job)
            if result.error:
                batch.failed.append(result)
            else:
                batch.completed.append(result)
            return result

    tasks = [_process(job) for job in jobs]
    await asyncio.gather(*tasks, return_exceptions=True)

    batch.end_time = time.time()
    return batch


def swarm_dispatch(
    items: list[dict],
    handler: Callable[[dict], dict],
    concurrency: int = 5,
) -> dict:
    jobs = []
    for i, item in enumerate(items):
        job_id = item.get("_job_id", f"job_{i}")
        jobs.append(SwarmJob(job_id, item, handler))

    loop = asyncio.new_event_loop()
    try:
        asyncio.set_event_loop(loop)
        batch = loop.run_until_complete(swarm_process(jobs, concurrency))
    finally:
        loop.close()

    results = []
    for job in batch.completed:
        results.append(job.result)

    return {
        "summary": batch.summary,
        "results": results,
        "failures": [
            {"job_id": j.job_id, "error": j.error, "payload": j.payload}
            for j in batch.failed
        ],
    }


def format_swarm_results(batch_result: dict, skill_name: str) -> str:
    summary = batch_result["summary"]
    results = batch_result["results"]
    failures = batch_result["failures"]

    lines = [f"=== {skill_name.title()} Batch Results ==="]
    lines.append(f"Total: {summary['total']}, Completed: {summary['completed']}, Failed: {summary['failed']}, Time: {summary['duration_ms']}ms")
    lines.append("")

    successes = [r for r in results if r.get("success")]
    fails = [r for r in results if not r.get("success")]

    if successes:
        lines.append(f"Successful ({len(successes)}):")
        for r in successes[:5]:
            lines.append(f"  - {r.get('effect', 'ok')}")
        if len(successes) > 5:
            lines.append(f"  ... and {len(successes) - 5} more")

    if fails:
        lines.append(f"Failed ({len(fails)}):")
        for r in fails[:3]:
            lines.append(f"  - {r.get('effect', 'failed')}")

    if failures:
        lines.append(f"Errors ({len(failures)}):")
        for f in failures:
            lines.append(f"  - Job {f.get('job_id', '?')}: {f.get('error', 'unknown')}")

    return "\n".join(lines)
