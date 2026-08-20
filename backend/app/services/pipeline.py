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
from app.services.analyze import analyze_reviews
from app.services.clean import clean_reviews
from app.services.collect import CollectError, collect_reviews
from app.services import store
from app.services.moonshot_client import MoonshotError
from app.services.plan import plan_prd
from app.services.url_parser import InvalidAppUrlError, extract_app_id

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


def _mark_stage(
    stages: list[JobStage],
    index: int,
    *,
    status: StageStatus,
    message: str,
    started: bool = False,
    finished: bool = False,
) -> None:
    stage = stages[index].model_copy(deep=True)
    stage.status = status
    stage.message = message
    if started:
        stage.started_at = _utcnow()
    if finished:
        stage.finished_at = _utcnow()
    stages[index] = stage


def _placeholder_later_artifacts() -> dict:
    return {
        "findings": [],
        "analysis_stats": {},
        "analysis_notes": "",
        "analysis_validation": {},
        "prd": {},
        "testcases": [],
        "validation": {
            "ok": True,
            "notes": [
                "Day4: collect+clean+analyze are real; PRD/testcases still placeholders."
            ],
        },
    }


def run_pipeline(job_id: str) -> None:
    try:
        job = store.get_job(job_id)
        if job is None:
            return

        store.update_job(job_id, status=JobStatus.running, updated_at=_utcnow())
        stages = [stage.model_copy(deep=True) for stage in job.stages]
        artifacts: dict = {
            "scope": {},
            "reviews_raw": [],
            "reviews_cleaned": [],
            "collection_meta": {},
            **_placeholder_later_artifacts(),
            "meta": {
                "app_url": job.app_url,
                "pipeline": "day4-collect-clean-analyze",
            },
        }

        # 1) scope
        _mark_stage(
            stages,
            0,
            status=StageStatus.running,
            message="Determining analysis scope...",
            started=True,
        )
        store.update_job(job_id, stages=stages, updated_at=_utcnow())

        app_id = extract_app_id(job.app_url)
        artifacts["scope"] = {
            "app_id": app_id,
            "focus": job.goal or "general",
            "source": job.source,
            "storefront": "us",
            "note": "Scope derived from user goal and available collection mode.",
        }
        _mark_stage(
            stages,
            0,
            status=StageStatus.done,
            message=f"Scoped app_id={app_id}, focus={artifacts['scope']['focus']}",
            finished=True,
        )
        store.update_job(
            job_id, stages=stages, artifacts=artifacts, updated_at=_utcnow()
        )

        # 2) collect (real)
        _mark_stage(
            stages,
            1,
            status=StageStatus.running,
            message=f"Collecting reviews via source={job.source}...",
            started=True,
        )
        store.update_job(job_id, stages=stages, updated_at=_utcnow())

        collected = collect_reviews(
            app_url=job.app_url,
            source=job.source,
            import_path=job.import_path,
            max_pages=job.max_pages,
            refresh_sample_on_live=True,
        )
        artifacts["reviews_raw"] = collected["reviews"]
        artifacts["collection_meta"] = collected["collection_meta"]
        artifacts["scope"]["app_id"] = collected["app_id"]

        _mark_stage(
            stages,
            1,
            status=StageStatus.done,
            message=(
                f"Collected {collected['collection_meta'].get('count', 0)} reviews "
                f"({collected['collection_meta'].get('source')})"
            ),
            finished=True,
        )
        store.update_job(
            job_id, stages=stages, artifacts=artifacts, updated_at=_utcnow()
        )

        # 3) clean (deterministic rules)
        _mark_stage(
            stages,
            2,
            status=StageStatus.running,
            message="Cleaning, normalizing, and deduplicating reviews...",
            started=True,
        )
        store.update_job(job_id, stages=stages, updated_at=_utcnow())

        cleaned_result = clean_reviews(artifacts["reviews_raw"])
        artifacts["reviews_cleaned"] = cleaned_result["reviews_cleaned"]
        artifacts["cleaning_report"] = cleaned_result["cleaning_report"]
        report = cleaned_result["cleaning_report"]
        _mark_stage(
            stages,
            2,
            status=StageStatus.done,
            message=(
                f"Cleaned {report['input_count']} → {report['output_count']} "
                f"(dup_id={report['removed_duplicate_id']}, "
                f"dup_content={report['removed_duplicate_content']})"
            ),
            finished=True,
        )
        store.update_job(
            job_id, stages=stages, artifacts=artifacts, updated_at=_utcnow()
        )

        # 4) analyze (Moonshot + deterministic stats + evidence validation)
        _mark_stage(
            stages,
            3,
            status=StageStatus.running,
            message="Analyzing reviews with Moonshot (evidence-grounded)...",
            started=True,
        )
        store.update_job(job_id, stages=stages, updated_at=_utcnow())

        analysis = analyze_reviews(artifacts["reviews_cleaned"], goal=job.goal)
        artifacts["findings"] = analysis["findings"]
        artifacts["analysis_stats"] = analysis["stats"]
        artifacts["analysis_notes"] = analysis["analysis_notes"]
        artifacts["analysis_validation"] = analysis["validation"]
        artifacts["analysis_model"] = analysis["model"]

        _mark_stage(
            stages,
            3,
            status=StageStatus.done,
            message=(
                f"Generated {len(analysis['findings'])} findings "
                f"(rejected {analysis['validation'].get('rejected', 0)} unsupported)"
            ),
            finished=True,
        )
        store.update_job(
            job_id, stages=stages, artifacts=artifacts, updated_at=_utcnow()
        )

        # 5) plan (Moonshot PRD + version split + finding/review linking)
        _mark_stage(
            stages,
            4,
            status=StageStatus.running,
            message="Creating PRD and version plan with Moonshot...",
            started=True,
        )
        store.update_job(job_id, stages=stages, updated_at=_utcnow())

        planned = plan_prd(
            artifacts["findings"],
            goal=job.goal,
            stats=artifacts.get("analysis_stats"),
        )
        artifacts["prd"] = planned["prd"]
        artifacts["planning_notes"] = planned["planning_notes"]
        artifacts["planning_validation"] = planned["validation"]
        artifacts["planning_model"] = planned["model"]

        req_count = len(planned["prd"].get("requirements") or [])
        _mark_stage(
            stages,
            4,
            status=StageStatus.done,
            message=(
                f"Created PRD with {req_count} requirements "
                f"(rejected {planned['validation'].get('rejected', 0)} unsupported)"
            ),
            finished=True,
        )
        store.update_job(
            job_id, stages=stages, artifacts=artifacts, updated_at=_utcnow()
        )

        # 6-7 remaining stages still placeholder (Day6)
        for index in range(5, len(stages)):
            stage = stages[index]
            _mark_stage(
                stages,
                index,
                status=StageStatus.running,
                message=f"Running {stage.name.lower()} (placeholder)...",
                started=True,
            )
            store.update_job(job_id, stages=stages, updated_at=_utcnow())
            time.sleep(0.35)
            _mark_stage(
                stages,
                index,
                status=StageStatus.done,
                message=f"Completed {stage.name.lower()} (placeholder)",
                finished=True,
            )
            store.update_job(job_id, stages=stages, updated_at=_utcnow())

        store.update_job(
            job_id,
            status=JobStatus.succeeded,
            stages=stages,
            artifacts=artifacts,
            error=None,
            updated_at=_utcnow(),
        )
    except (CollectError, InvalidAppUrlError, MoonshotError, Exception) as exc:  # noqa: BLE001
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
        import_path=req.import_path,
        max_pages=req.max_pages,
        stages=build_initial_stages(),
        artifacts={},
        error=None,
        created_at=now,
        updated_at=now,
    )
    store.create_job(job)

    worker = Thread(target=run_pipeline, args=(job_id,), daemon=True)
    worker.start()
    return job_id
