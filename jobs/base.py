"""Abstract base class for job runners.

Implement this interface to plug in any execution backend:
ThreadPool, Celery, Redis Queue, Temporal, etc.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Callable
from typing import Any

from jobs.models import Job


class BaseJobRunner(ABC):
    """Abstract interface for async job execution."""

    @abstractmethod
    def submit(self, job: Job, run_fn: Callable[..., dict], **kwargs: Any) -> str:
        """Submit a job for async execution.

        Args:
            job: The Job object with metadata.
            run_fn: The function to execute (e.g., run_research_job).
            **kwargs: Arguments passed to run_fn.

        Returns:
            The job ID.
        """

    @abstractmethod
    def get_job(self, job_id: str) -> Job | None:
        """Get current job state by ID."""

    @abstractmethod
    def list_jobs(self, user_id: str | None = None, limit: int = 50, offset: int = 0) -> list[Job]:
        """List jobs, optionally filtered by user."""

    @abstractmethod
    def cancel(self, job_id: str) -> bool:
        """Cancel a running or pending job. Returns True if cancelled."""

    @abstractmethod
    def update_progress(self, job_id: str, stage: str, pct: float, message: str) -> None:
        """Update job progress (called from within the job execution)."""
