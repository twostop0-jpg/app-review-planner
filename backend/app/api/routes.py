from fastapi import APIRouter, HTTPException

from app.models.schemas import AnalyzeRequest, JobCreateResponse, JobStatusResponse
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
