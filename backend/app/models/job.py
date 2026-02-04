from datetime import datetime
from typing import Optional

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class JobListing(Base):
    __tablename__ = "job_listings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("user_profiles.id"))

    # Source info
    source: Mapped[str] = mapped_column(String(20))  # "indeed" or "linkedin"
    source_url: Mapped[str] = mapped_column(String(1000))
    source_job_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    # Job details
    title: Mapped[str] = mapped_column(String(500))
    company: Mapped[str] = mapped_column(String(255))
    location: Mapped[str] = mapped_column(String(255))
    description: Mapped[str] = mapped_column(Text)
    salary_info: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    job_type: Mapped[Optional[str]] = mapped_column(
        String(50), nullable=True
    )  # full-time, part-time, contract
    posted_date: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    is_easy_apply: Mapped[bool] = mapped_column(Boolean, default=False)

    # AI scoring
    fit_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    fit_reasoning: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Status tracking
    status: Mapped[str] = mapped_column(String(30), default="discovered")
    # discovered -> scored -> approved -> applying -> applied -> rejected -> skipped

    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now()
    )

    # Relationships
    user: Mapped["UserProfile"] = relationship(back_populates="jobs")
    application: Mapped[Optional["Application"]] = relationship(
        back_populates="job", uselist=False
    )
