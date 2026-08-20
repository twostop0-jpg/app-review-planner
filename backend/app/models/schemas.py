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
    import_path: str | None = Field(
        default=None,
        description="Path to JSON/CSV when source=import (repo-relative or absolute)",
    )
    max_pages: int = Field(default=5, ge=1, le=10)


class Review(BaseModel):
    id: str
    app_id: str
    rating: int | None = None
    title: str = ""
    content: str = ""
    author: str = ""
    date: str | None = None
    version: str | None = None
    country: str = "us"
    source: Literal["live", "sample", "import"] = "live"


class Finding(BaseModel):
    finding_id: str
    title: str
    summary: str = ""
    severity: Literal["high", "medium", "low"] = "medium"
    evidence_review_ids: list[str] = Field(default_factory=list)
    evidence_excerpts: list[str] = Field(default_factory=list)
    support_count: int = 0
    confidence: float = 0.0
    conflicts: list[str] = Field(default_factory=list)
    uncertainty_notes: str = ""
    assumption: bool = False
    origin: Literal["model", "stat", "rule"] = "model"


class Requirement(BaseModel):
    req_id: str
    title: str
    description: str = ""
    user_problem: str = ""
    priority: Literal["P0", "P1", "P2"] = "P1"
    version: str = "vNext-1"
    linked_finding_ids: list[str] = Field(default_factory=list)
    linked_review_ids: list[str] = Field(default_factory=list)
    acceptance_criteria: list[str] = Field(default_factory=list)
    non_goals: list[str] = Field(default_factory=list)
    origin: Literal["model", "rule"] = "model"


class TestCase(BaseModel):
    tc_id: str
    title: str
    objective: str = ""
    steps: list[str] = Field(default_factory=list)
    expected_result: str = ""
    linked_req_ids: list[str] = Field(default_factory=list)
    linked_review_ids: list[str] = Field(default_factory=list)
    priority: Literal["P0", "P1", "P2"] = "P1"
    assumption: bool = False
    origin: Literal["model", "rule"] = "model"


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
    import_path: str | None = None
    max_pages: int = 5
    stages: list[JobStage]
    artifacts: dict[str, Any] = Field(default_factory=dict)
    error: str | None = None
    created_at: datetime
    updated_at: datetime


class CollectPreviewRequest(BaseModel):
    app_url: str
    source: Literal["live", "sample", "import"] = "live"
    import_path: str | None = None
    max_pages: int = Field(default=3, ge=1, le=10)


class CollectPreviewResponse(BaseModel):
    app_id: str
    count: int
    collection_meta: dict[str, Any]
    reviews: list[Review]
