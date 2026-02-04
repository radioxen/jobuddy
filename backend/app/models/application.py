from datetime import datetime
from typing import Optional

from sqlalchemy import JSON, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Application(Base):
    __tablename__ = "applications"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    job_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("job_listings.id"), unique=True
    )
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("user_profiles.id"))

    # Generated documents
    tailored_resume_path: Mapped[Optional[str]] = mapped_column(
        String(500), nullable=True
    )
    cover_letter_path: Mapped[Optional[str]] = mapped_column(
        String(500), nullable=True
    )
    cover_letter_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    tailored_resume_json: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    # Status
    status: Mapped[str] = mapped_column(String(30), default="pending")
    # pending -> documents_ready -> form_filled -> awaiting_review -> submitted -> failed

    # Form filling result
    form_data_json: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    submitted_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    job: Mapped["JobListing"] = relationship(back_populates="application")
    user: Mapped["UserProfile"] = relationship(back_populates="applications")
