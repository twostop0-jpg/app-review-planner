from __future__ import annotations

import time
import uuid
from datetime import datetime, timezone
from threading import Thread

from app.models.schemas import (
    AnalyzeRequest,
    JobStage,
    JobStatus,
    JobStatusResponse,
    StageStatus,
)
from app.services import store

STAGE_DEFS: list[tuple[str, str]] = [
    ("scope", "Determine analysis scope"),
    ("collect", "Collect reviews"),
    ("clean", "Clean and structure reviews"),
    ("analyze", "Classify and analyze"),
    ("plan", "Create PRD and version plan"),
    ("testcases", "Generate test cases"),
    ("validate", "Validate traceability"),
]


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def build_initial_stages() -> list[JobStage]:
    return [
        JobStage(key=key, name=name, status=StageStatus.pending)
        for key, name in STAGE_DEFS
    ]


def _fake_artifacts(app_url: str, goal: str | None) -> dict:
    return {
        "scope": {
            "focus": goal or "general",
            "note": "Day1 fake scope — replace with real scoping on later days",
        },
        "reviews_raw": [
            {
                "id": "r1",
                "rating": 1,
                "title": "Fake review",
                "content": "Placeholder raw review for UI wiring",
            }
        ],
        "reviews_cleaned": [
            {
                "id": "r1",
                "rating": 1,
                "title": "Fake review",
                "content": "Placeholder cleaned review for UI wiring",
            }
        ],
        "findings": [],
        "prd": {},
        "testcases": [],
        "validation": {
            "ok": True,
            "notes": ["Day1 placeholder validation"],
        },
        "meta": {
            "app_url": app_url,
            "pipeline": "fake",
        },
    }


def run_fake_pipeline(job_id: str) -> None:
    try:
        job = store.get_job(job_id)
        if job is None:
            return

        store.update_job(job_id, status=JobStatus.running, updated_at=_utcnow())
        stages = [stage.model_copy(deep=True) for stage in job.stages]

        for index, stage in enumerate(stages):
            stage.status = StageStatus.running
            stage.message = f"Running {stage.name.lower()}..."
            stage.started_at = _utcnow()
            stages[index] = stage
            store.update_job(job_id, stages=stages, updated_at=_utcnow())

            time.sleep(0.9)

            stage.status = StageStatus.done
            stage.message = f"Completed {stage.name.lower()} (fake)"
            stage.finished_at = _utcnow()
            stages[index] = stage
            store.update_job(job_id, stages=stages, updated_at=_utcnow())

        artifacts = _fake_artifacts(job.app_url, job.goal)
        store.update_job(
            job_id,
            status=JobStatus.succeeded,
            stages=stages,
            artifacts=artifacts,
            error=None,
            updated_at=_utcnow(),
        )
    except Exception as exc:  # noqa: BLE001 - surface any pipeline failure to job state
        job = store.get_job(job_id)
        stages = []
        if job is not None:
            stages = [stage.model_copy(deep=True) for stage in job.stages]
            for stage in stages:
                if stage.status == StageStatus.running:
                    stage.status = StageStatus.error
                    stage.message = str(exc)
                    stage.finished_at = _utcnow()
                    break
        store.update_job(
            job_id,
            status=JobStatus.failed,
            stages=stages,
            error=str(exc),
            updated_at=_utcnow(),
        )


def create_and_start_job(req: AnalyzeRequest) -> str:
    now = _utcnow()
    job_id = str(uuid.uuid4())
    job = JobStatusResponse(
        job_id=job_id,
        status=JobStatus.queued,
        app_url=req.app_url,
        goal=req.goal,
        source=req.source,
        stages=build_initial_stages(),
        artifacts={},
        error=None,
        created_at=now,
        updated_at=now,
    )
    store.create_job(job)

    worker = Thread(target=run_fake_pipeline, args=(job_id,), daemon=True)
    worker.start()
    return job_id
