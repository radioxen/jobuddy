from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class UserProfileCreate(BaseModel):
    full_name: str = ""
    email: str = ""
    phone: Optional[str] = None
    linkedin_url: Optional[str] = None


class UserPreferencesUpdate(BaseModel):
    target_job_titles: Optional[list[str]] = None
    target_locations: Optional[list[str]] = None
    remote_preference: Optional[str] = None  # remote, hybrid, onsite, any
    min_salary: Optional[int] = None
    max_salary: Optional[int] = None
    experience_level: Optional[str] = None  # entry, mid, senior, executive
    industries: Optional[list[str]] = None


class UserPreferencesResponse(BaseModel):
    target_job_titles: list[str] | None = None
    target_locations: list[str] | None = None
    remote_preference: str = "any"
    min_salary: int | None = None
    max_salary: int | None = None
    experience_level: str = "mid"
    industries: list[str] | None = None

    class Config:
        from_attributes = True


class UserProfileResponse(BaseModel):
    id: int
    full_name: str
    email: str
    phone: str | None = None
    linkedin_url: str | None = None
    original_resume_path: str | None = None
    parsed_resume_json: dict | None = None
    target_job_titles: list[str] | None = None
    target_locations: list[str] | None = None
    remote_preference: str = "any"
    min_salary: int | None = None
    max_salary: int | None = None
    experience_level: str = "mid"
    industries: list[str] | None = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
