import asyncio
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.job import JobListing
from app.models.user import UserProfile
from app.models.application import Application
from app.schemas.job import (
    JobListingResponse,
    JobListResponse,
    JobApproveRequest,
    JobSearchRequest,
)
from app.services.websocket_manager import get_ws_manager

router = APIRouter()


@router.post("/search")
async def search_jobs(
    request: JobSearchRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    """Trigger a job search across Indeed and LinkedIn."""
    from app.agents.flows.job_application_flow import run_job_search

    # Get user
    result = await db.execute(select(UserProfile).limit(1))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=400, detail="Please upload your resume first")
    if not user.parsed_resume_json:
        raise HTTPException(status_code=400, detail="Please upload your resume first")

    # Use request params or fall back to user preferences
    job_titles = request.job_titles or user.target_job_titles or []
    locations = request.locations or user.target_locations or []

    if not job_titles:
        raise HTTPException(
            status_code=400,
            detail="Please specify job titles in preferences or search request",
        )

    # Run search in background
    background_tasks.add_task(
        run_job_search,
        user_id=user.id,
        job_titles=job_titles,
        locations=locations,
        remote_preference=request.remote_preference or user.remote_preference,
        platforms=request.platforms,
        max_results=request.max_results,
    )

    return {
        "message": "Job search started",
        "job_titles": job_titles,
        "locations": locations,
        "platforms": request.platforms,
    }


@router.get("", response_model=JobListResponse)
async def list_jobs(
    status: Optional[str] = Query(None),
    min_score: Optional[float] = Query(None),
    source: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    """List discovered jobs with optional filters."""
    query = select(JobListing).order_by(JobListing.fit_score.desc().nullslast())

    if status:
        query = query.where(JobListing.status == status)
    if min_score is not None:
        query = query.where(JobListing.fit_score >= min_score)
    if source:
        query = query.where(JobListing.source == source)

    # Count total
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar()

    # Paginate
    query = query.offset((page - 1) * per_page).limit(per_page)
    result = await db.execute(query)
    jobs = result.scalars().all()

    return JobListResponse(
        jobs=[JobListingResponse.model_validate(j) for j in jobs],
        total=total,
        page=page,
        per_page=per_page,
    )


@router.get("/{job_id}", response_model=JobListingResponse)
async def get_job(job_id: int, db: AsyncSession = Depends(get_db)):
    """Get a single job listing with full details."""
    result = await db.execute(select(JobListing).where(JobListing.id == job_id))
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return JobListingResponse.model_validate(job)


@router.post("/{job_id}/approve")
async def approve_job(job_id: int, db: AsyncSession = Depends(get_db)):
    """Approve a job for application."""
    result = await db.execute(select(JobListing).where(JobListing.id == job_id))
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    job.status = "approved"

    # Create application record if not exists
    app_result = await db.execute(
        select(Application).where(Application.job_id == job_id)
    )
    if not app_result.scalar_one_or_none():
        application = Application(job_id=job.id, user_id=job.user_id, status="pending")
        db.add(application)

    await db.commit()
    return {"message": f"Job '{job.title}' approved", "job_id": job_id}


@router.post("/{job_id}/reject")
async def reject_job(job_id: int, db: AsyncSession = Depends(get_db)):
    """Reject/skip a job."""
    result = await db.execute(select(JobListing).where(JobListing.id == job_id))
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    job.status = "skipped"
    await db.commit()
    return {"message": f"Job '{job.title}' skipped", "job_id": job_id}


@router.post("/approve-batch")
async def approve_batch(
    request: JobApproveRequest,
    db: AsyncSession = Depends(get_db),
):
    """Approve multiple jobs for application."""
    approved = []
    for job_id in request.job_ids:
        result = await db.execute(select(JobListing).where(JobListing.id == job_id))
        job = result.scalar_one_or_none()
        if job:
            job.status = "approved"
            # Create application record
            app_result = await db.execute(
                select(Application).where(Application.job_id == job_id)
            )
            if not app_result.scalar_one_or_none():
                application = Application(
                    job_id=job.id, user_id=job.user_id, status="pending"
                )
                db.add(application)
            approved.append(job_id)

    await db.commit()
    return {"message": f"Approved {len(approved)} jobs", "approved_ids": approved}
