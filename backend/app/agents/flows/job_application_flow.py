"""
Main orchestration module for the job application pipeline.

This module provides standalone async functions that orchestrate the
multi-agent job application workflow. Each function handles one phase
of the pipeline and can be called independently from API endpoints
or chat commands.

Pipeline phases:
1. Job Search — Search Indeed/LinkedIn for matching jobs
2. Job Scoring — Score each job against the candidate's resume + portfolio (RAG)
3. Document Preparation — Tailor resume + write cover letter per job (RAG-enhanced)
4. Form Filling — Fill application forms in browser (Playwright)

Features:
- RAG integration for better context from resume + portfolio documents
- Recursive job status tracking through the pipeline
- Real-time WebSocket updates at each step
"""

import asyncio
import json
import os
import uuid
from datetime import datetime, timezone
from typing import Optional

from openai import OpenAI
from sqlalchemy import select, and_
from sqlalchemy.orm import joinedload

from app.config import settings
from app.database import async_session
from app.models.application import Application
from app.models.job import JobListing
from app.models.user import UserProfile
from app.services.browser_manager import get_browser_manager
from app.services.cover_letter_writer import CoverLetterWriter
from app.services.form_filler import get_form_filler
from app.services.job_search import IndeedSearcher, LinkedInSearcher
from app.services.rag_service import get_rag_service
from app.services.resume_tailor import ResumeTailorService
from app.services.websocket_manager import get_ws_manager


# ============================================================================
# Pipeline Status Tracking
# ============================================================================

class PipelineTracker:
    """Tracks job application pipeline status recursively."""

    STATUS_FLOW = {
        "discovered": "scored",
        "scored": "approved",
        "approved": "documents_ready",
        "documents_ready": "form_filled",
        "form_filled": "awaiting_review",
        "awaiting_review": "submitted",
    }

    TERMINAL_STATES = {"submitted", "skipped", "failed"}

    def __init__(self, user_id: int):
        self.user_id = user_id
        self.ws = get_ws_manager()

    async def get_pipeline_status(self) -> dict:
        """Get complete pipeline status for all jobs."""
        async with async_session() as db:
            result = await db.execute(
                select(JobListing).where(JobListing.user_id == self.user_id)
            )
            jobs = result.scalars().all()

            status_counts = {}
            for job in jobs:
                status_counts[job.status] = status_counts.get(job.status, 0) + 1

            # Get applications
            app_result = await db.execute(
                select(Application).where(Application.user_id == self.user_id)
            )
            apps = app_result.scalars().all()
            app_status_counts = {}
            for app in apps:
                app_status_counts[app.status] = app_status_counts.get(app.status, 0) + 1

            return {
                "total_jobs": len(jobs),
                "job_statuses": status_counts,
                "total_applications": len(apps),
                "application_statuses": app_status_counts,
                "next_actions": self._get_next_actions(status_counts, app_status_counts),
            }

    def _get_next_actions(self, job_status: dict, app_status: dict) -> list[str]:
        """Determine what actions should be taken next."""
        actions = []

        if job_status.get("scored", 0) > 0:
            actions.append(f"Review and approve {job_status['scored']} scored jobs")

        if app_status.get("pending", 0) > 0:
            actions.append(f"Prepare documents for {app_status['pending']} approved jobs")

        if app_status.get("documents_ready", 0) > 0:
            actions.append(f"Fill forms for {app_status['documents_ready']} ready applications")

        if app_status.get("form_filled", 0) > 0:
            actions.append(f"Review and submit {app_status['form_filled']} filled applications")

        return actions

    async def advance_job_status(self, job_id: int, new_status: str):
        """Advance a job to a new status with validation."""
        async with async_session() as db:
            result = await db.execute(
                select(JobListing).where(JobListing.id == job_id)
            )
            job = result.scalar_one_or_none()
            if not job:
                return False

            # Validate status transition
            current = job.status
            expected_next = self.STATUS_FLOW.get(current)

            if new_status in self.TERMINAL_STATES or new_status == expected_next:
                job.status = new_status
                await db.commit()
                return True

            return False

    async def notify_status(self, message: str, data: dict = None):
        """Send status update via WebSocket."""
        await self.ws.send_status(
            self.user_id,
            "pipeline_update",
            {"message": message, "data": data or {}, "timestamp": datetime.now(timezone.utc).isoformat()},
        )


# ============================================================================
# Notification Helper
# ============================================================================

async def _notify(user_id: int, message: str, status_type: str = "flow_update"):
    """Send a real-time status update via WebSocket."""
    ws = get_ws_manager()
    await ws.send_status(user_id, status_type, {"message": message})


# ============================================================================
# Phase 1: Job Search
# ============================================================================

async def run_job_search(
    user_id: int,
    job_titles: list[str],
    locations: list[str],
    remote_preference: str = "any",
    platforms: list[str] = None,
    max_results: int = 25,
):
    """
    Phase 1: Search for jobs across platforms and score them.

    This function:
    1. Loads RAG context from documents (resume + portfolio)
    2. Searches Indeed and/or LinkedIn for jobs
    3. Saves discovered jobs to the database
    4. Scores each job against the candidate's resume (RAG-enhanced)
    5. Notifies the user via WebSocket
    """
    if platforms is None:
        platforms = ["indeed", "linkedin"]

    tracker = PipelineTracker(user_id)
    await _notify(user_id, "Starting job search pipeline...")

    # Initialize RAG service and load documents
    rag = get_rag_service()
    doc_count = rag.load_documents()
    if doc_count > 0:
        await _notify(user_id, f"Loaded {doc_count} documents for RAG context")

    bm = get_browser_manager()
    await bm.ensure_initialized()

    all_jobs = []

    # Search each platform
    for title in job_titles:
        for location in locations:
            if "indeed" in platforms:
                await _notify(
                    user_id, f"Searching Indeed for '{title}' in '{location}'..."
                )
                try:
                    searcher = IndeedSearcher(bm)
                    indeed_jobs = await searcher.search(
                        query=title,
                        location=location,
                        remote=(remote_preference == "remote"),
                        max_results=max_results,
                    )
                    all_jobs.extend(indeed_jobs)
                    await _notify(
                        user_id,
                        f"Found {len(indeed_jobs)} jobs on Indeed for '{title}'",
                    )
                except Exception as e:
                    await _notify(user_id, f"Indeed search error: {str(e)}")

            if "linkedin" in platforms:
                await _notify(
                    user_id, f"Searching LinkedIn for '{title}' in '{location}'..."
                )
                try:
                    searcher = LinkedInSearcher(bm)
                    linkedin_jobs = await searcher.search(
                        query=title,
                        location=location,
                        remote=(remote_preference == "remote"),
                        max_results=max_results,
                    )
                    all_jobs.extend(linkedin_jobs)
                    await _notify(
                        user_id,
                        f"Found {len(linkedin_jobs)} jobs on LinkedIn for '{title}'",
                    )
                except Exception as e:
                    await _notify(user_id, f"LinkedIn search error: {str(e)}")

    # Deduplicate by title + company
    seen = set()
    unique_jobs = []
    for job in all_jobs:
        key = f"{job['title'].lower()}|{job['company'].lower()}"
        if key not in seen:
            seen.add(key)
            unique_jobs.append(job)

    await _notify(
        user_id, f"Found {len(unique_jobs)} unique jobs total. Saving to database..."
    )

    # Save to database
    async with async_session() as db:
        saved_jobs = []
        for job_data in unique_jobs:
            job = JobListing(
                user_id=user_id,
                source=job_data["source"],
                source_url=job_data["source_url"],
                source_job_id=job_data.get("source_job_id", ""),
                title=job_data["title"],
                company=job_data["company"],
                location=job_data["location"],
                description=job_data["description"],
                salary_info=job_data.get("salary_info"),
                job_type=job_data.get("job_type"),
                posted_date=job_data.get("posted_date"),
                is_easy_apply=job_data.get("is_easy_apply", False),
                status="discovered",
            )
            db.add(job)
            saved_jobs.append(job)

        await db.commit()
        for j in saved_jobs:
            await db.refresh(j)

        # Now score them with RAG context
        await _score_jobs_with_rag(user_id, saved_jobs, db, rag)

    # Report pipeline status
    status = await tracker.get_pipeline_status()
    await tracker.notify_status("Job search complete", status)


async def _score_jobs_with_rag(user_id: int, jobs: list[JobListing], db, rag):
    """Score jobs against the candidate's resume using GPT with RAG context."""
    await _notify(user_id, "Scoring jobs against your resume and portfolio...")

    # Get user resume
    result = await db.execute(
        select(UserProfile).where(UserProfile.id == user_id)
    )
    user = result.scalar_one_or_none()
    if not user or not user.parsed_resume_json:
        await _notify(user_id, "Error: Resume not found. Please upload your resume.")
        return

    client = OpenAI(api_key=settings.OPENAI_API_KEY)

    # Get portfolio highlights for context
    portfolio_projects = rag.get_portfolio_highlights()
    portfolio_context = ""
    if portfolio_projects:
        portfolio_context = f"\n\nCandidate's Company Portfolio Projects:\n{json.dumps(portfolio_projects, indent=2)}"

    # Score in batches of 5
    batch_size = 5
    for i in range(0, len(jobs), batch_size):
        batch = jobs[i : i + batch_size]
        jobs_for_scoring = [
            {
                "id": j.id,
                "title": j.title,
                "company": j.company,
                "location": j.location,
                "description": j.description[:2000],
            }
            for j in batch
        ]

        await _notify(user_id, f"Scoring batch {i//batch_size + 1}/{(len(jobs) + batch_size - 1)//batch_size}...")

        try:
            response = client.chat.completions.create(
                model=settings.OPENAI_MODEL,
                response_format={"type": "json_object"},
                messages=[
                    {
                        "role": "system",
                        "content": f"""You are a resume-job fit scoring expert with access to the candidate's full background.
Score each job for how well it matches the candidate's resume AND their company portfolio.

Consider:
1. Direct skills match from resume
2. Relevant project experience from portfolio
3. Industry alignment
4. Seniority/experience level match
5. Location compatibility

Return JSON: {{"scores": [{{"id": N, "score": 0-100, "reasoning": "...", "portfolio_relevance": "which portfolio projects are relevant"}}]}}

Scoring guide:
- 90-100: Excellent match, candidate is highly qualified
- 70-89: Good match, most requirements met
- 50-69: Moderate match, some relevant experience
- 30-49: Weak match, limited relevance
- 0-29: Poor match, significantly misaligned

Be honest and calibrated.{portfolio_context}""",
                    },
                    {
                        "role": "user",
                        "content": f"""Candidate resume:
{json.dumps(user.parsed_resume_json, indent=2)}

Jobs to score:
{json.dumps(jobs_for_scoring, indent=2)}""",
                    },
                ],
            )

            scores = json.loads(response.choices[0].message.content)
            for score_data in scores.get("scores", []):
                job_id = score_data.get("id")
                for job in batch:
                    if job.id == job_id:
                        job.fit_score = score_data.get("score", 0)
                        reasoning = score_data.get("reasoning", "")
                        portfolio_rel = score_data.get("portfolio_relevance", "")
                        if portfolio_rel:
                            reasoning += f"\n\nPortfolio relevance: {portfolio_rel}"
                        job.fit_reasoning = reasoning
                        job.status = "scored"
                        break

        except Exception as e:
            await _notify(user_id, f"Scoring error for batch: {str(e)}")

    await db.commit()

    # Count results
    scored_count = sum(1 for j in jobs if j.fit_score is not None)
    good_matches = sum(
        1
        for j in jobs
        if j.fit_score is not None
        and j.fit_score >= settings.JOB_FIT_SCORE_THRESHOLD
    )

    await _notify(
        user_id,
        f"Scored {scored_count} jobs. {good_matches} match above threshold "
        f"({settings.JOB_FIT_SCORE_THRESHOLD}). "
        "Review them in the Jobs tab and approve the ones you'd like to apply to.",
    )

    # Send jobs via WebSocket
    ws = get_ws_manager()
    await ws.send_message(
        user_id,
        "jobs_scored",
        {
            "total": len(jobs),
            "scored": scored_count,
            "good_matches": good_matches,
        },
    )


# ============================================================================
# Phase 2: Document Preparation (RAG-Enhanced)
# ============================================================================

async def run_document_preparation(application_id: int, user_id: int):
    """
    Phase 2: Generate tailored resume and cover letter for an application.

    Uses RAG to incorporate relevant context from:
    - The candidate's full resume
    - Portfolio case studies that match the job
    """
    rag = get_rag_service()
    if not rag._loaded:
        rag.load_documents()

    async with async_session() as db:
        # Load application with job
        result = await db.execute(
            select(Application)
            .options(joinedload(Application.job))
            .where(Application.id == application_id)
        )
        app = result.unique().scalar_one_or_none()
        if not app:
            await _notify(user_id, f"Application {application_id} not found")
            return

        # Load user
        user_result = await db.execute(
            select(UserProfile).where(UserProfile.id == user_id)
        )
        user = user_result.scalar_one_or_none()
        if not user or not user.parsed_resume_json:
            await _notify(user_id, "Resume not found")
            return

        job = app.job
        await _notify(
            user_id,
            f"Preparing documents for: {job.title} at {job.company}",
        )

        # Get RAG context for this specific job
        await _notify(user_id, "Analyzing relevant experience from your documents...")
        rag_context = rag.get_context_for_job(
            job_description=job.description,
            job_title=job.title,
            company=job.company,
        )

        # Tailor resume with RAG context
        try:
            tailor = ResumeTailorService()
            tailored_data = tailor.tailor(
                resume_data=user.parsed_resume_json,
                job_description=job.description,
                job_title=job.title,
                company=job.company,
                additional_context=rag_context,  # Pass RAG context
            )

            # Generate DOCX
            resume_filename = f"resume_{app.id}_{uuid.uuid4().hex[:8]}.docx"
            resume_path = os.path.join(settings.GENERATED_DIR, resume_filename)
            tailor.generate_docx(tailored_data, resume_path)

            app.tailored_resume_path = resume_path
            app.tailored_resume_json = tailored_data

            await _notify(user_id, f"Resume tailored for {job.title}")
        except Exception as e:
            await _notify(user_id, f"Resume tailoring error: {str(e)}")
            app.error_message = f"Resume tailoring failed: {str(e)}"

        # Write cover letter with RAG context
        try:
            writer = CoverLetterWriter()
            letter_text = writer.write(
                resume_data=user.parsed_resume_json,
                job_title=job.title,
                company=job.company,
                job_description=job.description,
                additional_context=rag_context,  # Pass RAG context
            )

            # Generate DOCX
            cl_filename = f"cover_letter_{app.id}_{uuid.uuid4().hex[:8]}.docx"
            cl_path = os.path.join(settings.GENERATED_DIR, cl_filename)
            writer.generate_docx(
                letter_text=letter_text,
                candidate_name=user.full_name,
                candidate_email=user.email,
                candidate_phone=user.phone or "",
                output_path=cl_path,
            )

            app.cover_letter_path = cl_path
            app.cover_letter_text = letter_text

            await _notify(user_id, f"Cover letter written for {job.title}")
        except Exception as e:
            await _notify(user_id, f"Cover letter error: {str(e)}")
            app.error_message = (app.error_message or "") + f" Cover letter failed: {str(e)}"

        # Update status
        if app.tailored_resume_path and app.cover_letter_path:
            app.status = "documents_ready"
            job.status = "documents_ready"  # Update job status too
            await _notify(
                user_id,
                f"Documents ready for {job.title} at {job.company}. "
                "You can now fill the application form.",
            )
        else:
            app.status = "failed"

        await db.commit()

        # Send update
        ws = get_ws_manager()
        await ws.send_message(
            user_id,
            "application_update",
            {
                "application_id": app.id,
                "job_id": job.id,
                "job_title": job.title,
                "company": job.company,
                "status": app.status,
            },
        )


# ============================================================================
# Phase 3: Form Filling
# ============================================================================

async def run_form_filling(application_id: int):
    """Phase 3: Fill the application form in the browser."""
    async with async_session() as db:
        result = await db.execute(
            select(Application)
            .options(joinedload(Application.job))
            .where(Application.id == application_id)
        )
        app = result.unique().scalar_one_or_none()
        if not app:
            return

        job = app.job
        user_id = app.user_id

        # Load candidate data
        user_result = await db.execute(
            select(UserProfile).where(UserProfile.id == user_id)
        )
        user = user_result.scalar_one_or_none()
        if not user:
            return

        await _notify(
            user_id,
            f"Opening browser and filling application for {job.title} at {job.company}...",
        )

        try:
            filler = get_form_filler(job.source)
            fill_result = await filler.fill(
                url=job.source_url,
                candidate=user.parsed_resume_json,
                resume_path=app.tailored_resume_path,
                cover_letter_path=app.cover_letter_path,
            )

            app.form_data_json = fill_result
            if fill_result.get("status") == "filled":
                app.status = "form_filled"
                job.status = "form_filled"
                needs_review = fill_result.get("needs_review", [])
                msg = f"Application form filled for {job.title}."
                if needs_review:
                    msg += f" {len(needs_review)} field(s) need your review."
                msg += " Please review in the browser and submit when ready."
                await _notify(user_id, msg)
            else:
                app.status = "failed"
                app.error_message = fill_result.get("error", "Unknown form filling error")
                await _notify(
                    user_id,
                    f"Form filling failed for {job.title}: {app.error_message}",
                )

        except Exception as e:
            app.status = "failed"
            app.error_message = str(e)
            await _notify(user_id, f"Form filling error: {str(e)}")

        await db.commit()

        ws = get_ws_manager()
        await ws.send_message(
            user_id,
            "application_update",
            {
                "application_id": app.id,
                "job_id": job.id,
                "job_title": job.title,
                "company": job.company,
                "status": app.status,
            },
        )


# ============================================================================
# Pipeline Runner: Process All Jobs Recursively
# ============================================================================

async def run_pipeline_for_approved_jobs(user_id: int):
    """
    Recursively process all approved jobs through the pipeline.

    For each approved job:
    1. Create application if not exists
    2. Prepare documents
    3. Fill application form
    """
    tracker = PipelineTracker(user_id)

    async with async_session() as db:
        # Get all approved jobs without applications
        result = await db.execute(
            select(JobListing)
            .where(
                and_(
                    JobListing.user_id == user_id,
                    JobListing.status == "approved",
                )
            )
        )
        approved_jobs = result.scalars().all()

        if not approved_jobs:
            await _notify(user_id, "No approved jobs to process")
            return

        await _notify(user_id, f"Processing {len(approved_jobs)} approved jobs...")

        for job in approved_jobs:
            # Check if application exists
            app_result = await db.execute(
                select(Application).where(Application.job_id == job.id)
            )
            app = app_result.scalar_one_or_none()

            if not app:
                # Create application
                app = Application(
                    job_id=job.id,
                    user_id=user_id,
                    status="pending",
                )
                db.add(app)
                await db.commit()
                await db.refresh(app)

            # Process based on current status
            if app.status == "pending":
                await run_document_preparation(app.id, user_id)
                await db.refresh(app)

            if app.status == "documents_ready":
                await run_form_filling(app.id)
                await db.refresh(app)

        # Final status report
        status = await tracker.get_pipeline_status()
        await tracker.notify_status("Pipeline processing complete", status)


async def get_pipeline_status(user_id: int) -> dict:
    """Get the current pipeline status for a user."""
    tracker = PipelineTracker(user_id)
    return await tracker.get_pipeline_status()
