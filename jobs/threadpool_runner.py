"""ThreadPool job runner — zero-dependency default implementation.

Uses concurrent.futures.ThreadPoolExecutor for local async execution.
Jobs are tracked in-memory while running, persisted to DB on completion.
"""

from __future__ import annotations

import logging
import os
from collections.abc import Callable
from concurrent.futures import Future, ThreadPoolExecutor
from datetime import datetime, timezone
from typing import Any

from jobs.base import BaseJobRunner
from jobs.models import Job, JobStatus, JobType

logger = logging.getLogger(__name__)


class ThreadPoolJobRunner(BaseJobRunner):
    """Default job runner using Python's ThreadPoolExecutor.

    Configuration:
        JOB_RUNNER_MAX_WORKERS env var (default: 4)
    """

    def __init__(self, max_workers: int | None = None) -> None:
        workers = max_workers or int(os.environ.get("JOB_RUNNER_MAX_WORKERS", "4"))
        self._executor = ThreadPoolExecutor(max_workers=workers, thread_name_prefix="job")
        self._jobs: dict[str, Job] = {}
        self._futures: dict[str, Future] = {}
        logger.info("ThreadPoolJobRunner initialized with %d workers", workers)

    def submit(self, job: Job, run_fn: Callable[..., dict], **kwargs: Any) -> str:
        self._jobs[job.id] = job
        future = self._executor.submit(self._execute, job, run_fn, **kwargs)
        self._futures[job.id] = future
        return job.id

    def get_job(self, job_id: str) -> Job | None:
        return self._jobs.get(job_id)

    def list_jobs(self, user_id: str | None = None, limit: int = 50, offset: int = 0) -> list[Job]:
        # Combine in-memory jobs with DB-persisted history
        jobs = list(self._jobs.values())

        # Load completed jobs from DB if we have few in-memory
        if len(jobs) < limit:
            try:
                from db.session import get_db_session
                from db.models import ResearchHistory
                db = get_db_session()
                try:
                    query = db.query(ResearchHistory).order_by(ResearchHistory.created_at.desc()).limit(limit)
                    if user_id:
                        query = query.filter_by(user_id=user_id)
                    for row in query.all():
                        # Skip if already in memory
                        if any(j.id == row.id for j in jobs):
                            continue
                        bt = (row.result_json or {}).get("backtest", {})
                        jobs.append(Job(
                            id=row.id,
                            job_type=JobType.RESEARCH,
                            status=JobStatus.COMPLETED,
                            params={"ticker": row.ticker, "strategy": row.strategy},
                            progress=1.0,
                            progress_stage="complete",
                            result=row.result_json,
                            created_at=row.created_at,
                            completed_at=row.created_at,
                            user_id=row.user_id,
                        ))
                finally:
                    db.close()
            except Exception:
                pass  # DB not available, use in-memory only

        if user_id:
            jobs = [j for j in jobs if j.user_id == user_id or j.user_id is None]
        jobs.sort(key=lambda j: j.created_at, reverse=True)
        return jobs[offset : offset + limit]

    def cancel(self, job_id: str) -> bool:
        future = self._futures.get(job_id)
        job = self._jobs.get(job_id)
        if not future or not job:
            return False

        cancelled = future.cancel()
        if cancelled:
            job.status = JobStatus.CANCELLED
            job.completed_at = datetime.now(timezone.utc)
            self._broadcast({"type": "job_cancelled", "job_id": job_id})
        return cancelled

    def update_progress(self, job_id: str, stage: str, pct: float, message: str) -> None:
        job = self._jobs.get(job_id)
        if not job:
            return
        job.progress = pct
        job.progress_stage = stage
        job.progress_message = message
        self._broadcast({
            "type": "job_progress",
            "job_id": job_id,
            "progress": pct,
            "stage": stage,
            "message": message,
        })

    def _execute(self, job: Job, run_fn: Callable[..., dict], **kwargs: Any) -> None:
        job.status = JobStatus.RUNNING
        job.started_at = datetime.now(timezone.utc)
        self._broadcast({"type": "job_started", "job_id": job.id, "params": job.params})

        # Inject progress callback
        def progress_cb(stage: str, pct: float, msg: str) -> None:
            self.update_progress(job.id, stage, pct, msg)

        kwargs["progress_cb"] = progress_cb

        try:
            result = run_fn(**kwargs)
            job.status = JobStatus.COMPLETED
            job.result = result
            job.progress = 1.0
            job.progress_stage = "complete"
            job.completed_at = datetime.now(timezone.utc)
            self._broadcast({"type": "job_completed", "job_id": job.id})
            self._persist(job)
        except Exception as exc:
            job.status = JobStatus.FAILED
            job.error = str(exc)
            job.completed_at = datetime.now(timezone.utc)
            logger.error("Job %s failed: %s", job.id, exc)
            self._broadcast({"type": "job_failed", "job_id": job.id, "error": str(exc)})

    def _broadcast(self, event: dict) -> None:
        """Push event through the WebSocket event manager (thread-safe)."""
        try:
            from api.events import event_manager
            event_manager.emit_sync(event)
        except Exception:
            pass

    def _persist(self, job: Job) -> None:
        """Persist completed job to database."""
        try:
            from db.session import get_db_session
            from db.models import ResearchHistory

            db = get_db_session()
            try:
                if job.result and job.user_id:
                    params = job.params or {}
                    db.add(ResearchHistory(
                        user_id=job.user_id,
                        ticker=params.get("ticker", ""),
                        strategy=params.get("strategy", ""),
                        result_json=job.result,
                    ))
                    db.commit()
            finally:
                db.close()
        except Exception as exc:
            logger.warning("Failed to persist job %s: %s", job.id, exc)
