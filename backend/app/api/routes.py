from fastapi import APIRouter, HTTPException

from app.models.schemas import (
    AnalyzeRequest,
    CollectPreviewRequest,
    CollectPreviewResponse,
    JobCreateResponse,
    JobStatusResponse,
    Review,
)
from app.services.collect import CollectError, collect_reviews
from app.services.pipeline import create_and_start_job
from app.services.store import get_job

router = APIRouter()


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@router.post("/api/jobs", response_model=JobCreateResponse)
def create_job(req: AnalyzeRequest) -> JobCreateResponse:
    job_id = create_and_start_job(req)
    return JobCreateResponse(job_id=job_id)


@router.get("/api/jobs/{job_id}", response_model=JobStatusResponse)
def get_job_status(job_id: str) -> JobStatusResponse:
    job = get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="job not found")
    return job


@router.post("/api/collect/preview", response_model=CollectPreviewResponse)
def preview_collect(req: CollectPreviewRequest) -> CollectPreviewResponse:
    try:
        result = collect_reviews(
            app_url=req.app_url,
            source=req.source,
            import_path=req.import_path,
            max_pages=req.max_pages,
            refresh_sample_on_live=True,
        )
    except CollectError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    reviews = [Review.model_validate(item) for item in result["reviews"]]
    return CollectPreviewResponse(
        app_id=result["app_id"],
        count=len(reviews),
        collection_meta=result["collection_meta"],
        reviews=reviews,
    )
