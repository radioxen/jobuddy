from datetime import datetime
from typing import Optional

from sqlalchemy import JSON, DateTime, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class UserProfile(Base):
    __tablename__ = "user_profiles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    full_name: Mapped[str] = mapped_column(String(255), default="")
    email: Mapped[str] = mapped_column(String(255), default="")
    phone: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    linkedin_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    # Resume
    original_resume_path: Mapped[Optional[str]] = mapped_column(
        String(500), nullable=True
    )
    parsed_resume_json: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    # Job preferences
    target_job_titles: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)
    target_locations: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)
    remote_preference: Mapped[str] = mapped_column(
        String(20), default="any"
    )  # remote, hybrid, onsite, any
    min_salary: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    max_salary: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    experience_level: Mapped[str] = mapped_column(
        String(20), default="mid"
    )  # entry, mid, senior, executive
    industries: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    jobs: Mapped[list["JobListing"]] = relationship(back_populates="user")
    applications: Mapped[list["Application"]] = relationship(back_populates="user")
    chat_messages: Mapped[list["ChatMessage"]] = relationship(back_populates="user")
