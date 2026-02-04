from datetime import datetime
from typing import Optional

from pydantic import BaseModel

from app.schemas.job import JobListingResponse


class ApplicationResponse(BaseModel):
    id: int
    job_id: int
    user_id: int
    tailored_resume_path: str | None = None
    cover_letter_path: str | None = None
    cover_letter_text: str | None = None
    status: str
    form_data_json: dict | None = None
    error_message: str | None = None
    submitted_at: datetime | None = None
    created_at: datetime
    updated_at: datetime
    job: JobListingResponse | None = None

    class Config:
        from_attributes = True


class ApplicationListResponse(BaseModel):
    applications: list[ApplicationResponse]
    total: int
