from __future__ import annotations

from threading import Lock

from app.models.schemas import JobStatusResponse

_JOBS: dict[str, JobStatusResponse] = {}
_LOCK = Lock()


def create_job(job: JobStatusResponse) -> None:
    with _LOCK:
        _JOBS[job.job_id] = job


def get_job(job_id: str) -> JobStatusResponse | None:
    with _LOCK:
        job = _JOBS.get(job_id)
        return job.model_copy(deep=True) if job else None


def update_job(job_id: str, **fields) -> JobStatusResponse:
    with _LOCK:
        current = _JOBS.get(job_id)
        if current is None:
            raise KeyError(f"job not found: {job_id}")
        updated = current.model_copy(update=fields, deep=True)
        _JOBS[job_id] = updated
        return updated.model_copy(deep=True)
