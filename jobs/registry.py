"""Job runner factory — configurable via JOB_RUNNER_BACKEND env var.

Default: threadpool (zero dependencies)
Optional: celery (requires redis + celery package)
Custom: implement BaseJobRunner and register here
"""

from __future__ import annotations

import os

from jobs.base import BaseJobRunner

_runner: BaseJobRunner | None = None


def get_runner() -> BaseJobRunner:
    """Get or create the singleton job runner based on configuration."""
    global _runner
    if _runner is not None:
        return _runner

    backend = os.environ.get("JOB_RUNNER_BACKEND", "threadpool")

    if backend == "threadpool":
        from jobs.threadpool_runner import ThreadPoolJobRunner
        _runner = ThreadPoolJobRunner()
    else:
        raise ValueError(
            f"Unknown job runner backend: {backend}. "
            f"Available: threadpool. "
            f"Implement BaseJobRunner for custom backends."
        )

    return _runner
