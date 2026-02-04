import os
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.config import settings
from app.database import get_db
from app.models.application import Application
from app.models.job import JobListing
from app.models.user import UserProfile
from app.schemas.application import ApplicationResponse, ApplicationListResponse

router = APIRouter()


@router.get("", response_model=ApplicationListResponse)
async def list_applications(
    status: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
):
    """List all applications with their status."""
    query = (
        select(Application)
        .options(joinedload(Application.job))
        .order_by(Application.updated_at.desc())
    )
    if status:
        query = query.where(Application.status == status)

    result = await db.execute(query)
    apps = result.unique().scalars().all()

    return ApplicationListResponse(
        applications=[ApplicationResponse.model_validate(a) for a in apps],
        total=len(apps),
    )


@router.get("/{app_id}", response_model=ApplicationResponse)
async def get_application(app_id: int, db: AsyncSession = Depends(get_db)):
    """Get a single application with details."""
    result = await db.execute(
        select(Application)
        .options(joinedload(Application.job))
        .where(Application.id == app_id)
    )
    app = result.unique().scalar_one_or_none()
    if not app:
        raise HTTPException(status_code=404, detail="Application not found")
    return ApplicationResponse.model_validate(app)


@router.post("/{app_id}/prepare")
async def prepare_documents(
    app_id: int,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    """Generate tailored resume and cover letter for an application."""
    from app.agents.flows.job_application_flow import run_document_preparation

    result = await db.execute(
        select(Application)
        .options(joinedload(Application.job))
        .where(Application.id == app_id)
    )
    app = result.unique().scalar_one_or_none()
    if not app:
        raise HTTPException(status_code=404, detail="Application not found")

    # Get user
    user_result = await db.execute(
        select(UserProfile).where(UserProfile.id == app.user_id)
    )
    user = user_result.scalar_one_or_none()
    if not user or not user.parsed_resume_json:
        raise HTTPException(status_code=400, detail="Resume not uploaded")

    background_tasks.add_task(
        run_document_preparation,
        application_id=app.id,
        user_id=user.id,
    )

    return {"message": "Document preparation started", "application_id": app.id}


@router.post("/{app_id}/fill-form")
async def fill_application_form(
    app_id: int,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    """Fill the application form in the browser using Playwright."""
    from app.agents.flows.job_application_flow import run_form_filling

    result = await db.execute(
        select(Application)
        .options(joinedload(Application.job))
        .where(Application.id == app_id)
    )
    app = result.unique().scalar_one_or_none()
    if not app:
        raise HTTPException(status_code=404, detail="Application not found")

    if not app.tailored_resume_path:
        raise HTTPException(
            status_code=400,
            detail="Documents not prepared yet. Call /prepare first.",
        )

    background_tasks.add_task(
        run_form_filling,
        application_id=app.id,
    )

    return {"message": "Form filling started", "application_id": app.id}


@router.post("/prepare-all")
async def prepare_all_approved(
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    """Prepare documents for all approved jobs."""
    from app.agents.flows.job_application_flow import run_document_preparation

    result = await db.execute(
        select(Application).where(Application.status == "pending")
    )
    apps = result.scalars().all()

    for app in apps:
        background_tasks.add_task(
            run_document_preparation,
            application_id=app.id,
            user_id=app.user_id,
        )

    return {"message": f"Preparing documents for {len(apps)} applications"}


@router.get("/{app_id}/resume/download")
async def download_tailored_resume(
    app_id: int, db: AsyncSession = Depends(get_db)
):
    """Download the tailored resume DOCX."""
    result = await db.execute(
        select(Application).where(Application.id == app_id)
    )
    app = result.scalar_one_or_none()
    if not app or not app.tailored_resume_path:
        raise HTTPException(status_code=404, detail="Tailored resume not found")

    if not os.path.exists(app.tailored_resume_path):
        raise HTTPException(status_code=404, detail="Resume file not found on disk")

    return FileResponse(
        app.tailored_resume_path,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        filename=f"resume_tailored_{app_id}.docx",
    )


@router.get("/{app_id}/cover-letter/download")
async def download_cover_letter(
    app_id: int, db: AsyncSession = Depends(get_db)
):
    """Download the cover letter DOCX."""
    result = await db.execute(
        select(Application).where(Application.id == app_id)
    )
    app = result.scalar_one_or_none()
    if not app or not app.cover_letter_path:
        raise HTTPException(status_code=404, detail="Cover letter not found")

    if not os.path.exists(app.cover_letter_path):
        raise HTTPException(
            status_code=404, detail="Cover letter file not found on disk"
        )

    return FileResponse(
        app.cover_letter_path,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        filename=f"cover_letter_{app_id}.docx",
    )
