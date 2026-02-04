from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class JobSearchRequest(BaseModel):
    job_titles: list[str] | None = None
    locations: list[str] | None = None
    remote_preference: str | None = None
    experience_level: str | None = None
    max_results: int = 25
    platforms: list[str] = ["indeed", "linkedin"]


class JobListingResponse(BaseModel):
    id: int
    source: str
    source_url: str
    source_job_id: str | None = None
    title: str
    company: str
    location: str
    description: str
    salary_info: str | None = None
    job_type: str | None = None
    posted_date: str | None = None
    is_easy_apply: bool = False
    fit_score: float | None = None
    fit_reasoning: str | None = None
    status: str
    created_at: datetime

    class Config:
        from_attributes = True


class JobListResponse(BaseModel):
    jobs: list[JobListingResponse]
    total: int
    page: int = 1
    per_page: int = 20


class JobApproveRequest(BaseModel):
    job_ids: list[int]
