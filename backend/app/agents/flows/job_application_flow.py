"""
Main orchestration module for the job application pipeline.

This module provides standalone async functions that orchestrate the
multi-agent job application workflow. Each function handles one phase
of the pipeline and can be called independently from API endpoints
or chat commands.

Pipeline phases:
1. Job Search — Search Indeed/LinkedIn for matching jobs
2. Job Scoring — Score each job against the candidate's resume
3. Document Preparation — Tailor resume + write cover letter per job
4. Form Filling — Fill application forms in browser (Playwright)
"""

import asyncio
import json
import os
import uuid
from typing import Optional

from openai import OpenAI
from sqlalchemy import select
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
from app.services.resume_tailor import ResumeTailorService
from app.services.websocket_manager import get_ws_manager


async def _notify(user_id: int, message: str, status_type: str = "flow_update"):
    """Send a real-time status update via WebSocket."""
    ws = get_ws_manager()
    await ws.send_status(user_id, status_type, {"message": message})


async def run_job_search(
    user_id: int,
    job_titles: list[str],
    locations: list[str],
    remote_preference: str = "any",
    platforms: list[str] = None,
    max_results: int = 25,
):
    """Phase 1: Search for jobs across platforms and score them.

    This function:
    1. Searches Indeed and/or LinkedIn for jobs
    2. Saves discovered jobs to the database
    3. Scores each job against the candidate's resume
    4. Notifies the user via WebSocket
    """
    if platforms is None:
        platforms = ["indeed", "linkedin"]

    await _notify(user_id, "Starting job search...")

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
                    await _notify(
                        user_id, f"Indeed search error: {str(e)}"
                    )

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
                    await _notify(
                        user_id, f"LinkedIn search error: {str(e)}"
                    )

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

        # Now score them
        await _score_jobs(user_id, saved_jobs, db)


async def _score_jobs(user_id: int, jobs: list[JobListing], db):
    """Score jobs against the candidate's resume using GPT."""
    await _notify(user_id, "Scoring jobs against your resume...")

    # Get user resume
    result = await db.execute(
        select(UserProfile).where(UserProfile.id == user_id)
    )
    user = result.scalar_one_or_none()
    if not user or not user.parsed_resume_json:
        await _notify(user_id, "Error: Resume not found. Please upload your resume.")
        return

    client = OpenAI(api_key=settings.OPENAI_API_KEY)

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

        try:
            response = client.chat.completions.create(
                model=settings.OPENAI_MODEL,
                response_format={"type": "json_object"},
                messages=[
                    {
                        "role": "system",
                        "content": """You are a resume-job fit scoring expert.
Score each job for how well it matches the candidate's resume.
Return JSON: {"scores": [{"id": N, "score": 0-100, "reasoning": "..."}]}

Scoring guide:
- 90-100: Excellent match, candidate is highly qualified
- 70-89: Good match, most requirements met
- 50-69: Moderate match, some relevant experience
- 30-49: Weak match, limited relevance
- 0-29: Poor match, significantly misaligned

Be honest and calibrated. Consider skills, experience level, industry, and location.""",
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
                        job.fit_reasoning = score_data.get("reasoning", "")
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


async def run_document_preparation(application_id: int, user_id: int):
    """Phase 3: Generate tailored resume and cover letter for an application."""
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

        # Tailor resume
        try:
            tailor = ResumeTailorService()
            tailored_data = tailor.tailor(
                resume_data=user.parsed_resume_json,
                job_description=job.description,
                job_title=job.title,
                company=job.company,
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

        # Write cover letter
        try:
            writer = CoverLetterWriter()
            letter_text = writer.write(
                resume_data=user.parsed_resume_json,
                job_title=job.title,
                company=job.company,
                job_description=job.description,
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
                "job_title": job.title,
                "company": job.company,
                "status": app.status,
            },
        )


async def run_form_filling(application_id: int):
    """Phase 4: Fill the application form in the browser."""
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
                "job_title": job.title,
                "company": job.company,
                "status": app.status,
            },
        )
