from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, Field


class AnalyzeRequest(BaseModel):
    app_url: str = Field(
        ...,
        description="U.S. App Store app URL",
        examples=[
            "https://apps.apple.com/us/app/workout-for-women-home-gym/id839285684"
        ],
    )
    goal: str | None = Field(
        default=None,
        description="Optional analysis goal or constraint",
        examples=["subscription conversion"],
    )
    source: Literal["live", "sample", "import"] = "live"


class StageStatus(str, Enum):
    pending = "pending"
    running = "running"
    done = "done"
    error = "error"
    skipped = "skipped"


class JobStage(BaseModel):
    key: str
    name: str
    status: StageStatus = StageStatus.pending
    message: str = ""
    started_at: datetime | None = None
    finished_at: datetime | None = None


class JobStatus(str, Enum):
    queued = "queued"
    running = "running"
    succeeded = "succeeded"
    failed = "failed"


class JobCreateResponse(BaseModel):
    job_id: str


class JobStatusResponse(BaseModel):
    job_id: str
    status: JobStatus
    app_url: str
    goal: str | None = None
    source: Literal["live", "sample", "import"] = "live"
    stages: list[JobStage]
    artifacts: dict[str, Any] = Field(default_factory=dict)
    error: str | None = None
    created_at: datetime
    updated_at: datetime
