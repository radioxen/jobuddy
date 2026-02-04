import json
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import async_session
from app.models.chat import ChatMessage
from app.models.job import JobListing
from app.models.application import Application
from app.models.user import UserProfile
from app.services.chat_service import ChatService
from app.services.websocket_manager import get_ws_manager

router = APIRouter()


async def load_chat_history(db: AsyncSession, user_id: int, limit: int = 20) -> list[dict]:
    """Load recent chat messages from DB."""
    result = await db.execute(
        select(ChatMessage)
        .where(ChatMessage.user_id == user_id)
        .order_by(ChatMessage.created_at.desc())
        .limit(limit)
    )
    messages = result.scalars().all()
    messages.reverse()  # Chronological order
    return [{"role": m.role, "content": m.content} for m in messages]


async def save_message(
    db: AsyncSession,
    user_id: int,
    role: str,
    content: str,
    message_type: str = "text",
    metadata: dict = None,
):
    """Save a chat message to DB."""
    msg = ChatMessage(
        user_id=user_id,
        role=role,
        content=content,
        message_type=message_type,
        metadata_json=metadata,
    )
    db.add(msg)
    await db.commit()


async def build_context(db: AsyncSession, user_id: int) -> dict:
    """Build context object with current system state for the chat agent."""
    # User profile
    user_result = await db.execute(
        select(UserProfile).where(UserProfile.id == user_id)
    )
    user = user_result.scalar_one_or_none()

    # Job counts by status
    jobs_result = await db.execute(
        select(JobListing.status, JobListing.id)
        .where(JobListing.user_id == user_id)
    )
    jobs = jobs_result.all()
    job_counts = {}
    for status, _ in jobs:
        job_counts[status] = job_counts.get(status, 0) + 1

    # Recent top jobs
    top_jobs_result = await db.execute(
        select(JobListing)
        .where(JobListing.user_id == user_id)
        .where(JobListing.fit_score.isnot(None))
        .order_by(JobListing.fit_score.desc())
        .limit(10)
    )
    top_jobs = [
        {
            "id": j.id,
            "title": j.title,
            "company": j.company,
            "score": j.fit_score,
            "status": j.status,
        }
        for j in top_jobs_result.scalars().all()
    ]

    # Application counts
    apps_result = await db.execute(
        select(Application.status, Application.id)
        .where(Application.user_id == user_id)
    )
    apps = apps_result.all()
    app_counts = {}
    for status, _ in apps:
        app_counts[status] = app_counts.get(status, 0) + 1

    return {
        "user_name": user.full_name if user else "Unknown",
        "has_resume": bool(user and user.parsed_resume_json),
        "preferences": {
            "job_titles": user.target_job_titles if user else [],
            "locations": user.target_locations if user else [],
            "remote": user.remote_preference if user else "any",
            "experience_level": user.experience_level if user else "mid",
        }
        if user
        else {},
        "job_counts": job_counts,
        "top_jobs": top_jobs,
        "application_counts": app_counts,
        "total_jobs": len(jobs),
        "total_applications": len(apps),
    }


async def execute_command(command: dict, user_id: int, db: AsyncSession):
    """Execute a chat command."""
    from app.agents.flows.job_application_flow import (
        run_job_search,
        run_document_preparation,
        run_form_filling,
    )

    action = command.get("action")
    ws = get_ws_manager()

    if action == "start_search":
        user_result = await db.execute(
            select(UserProfile).where(UserProfile.id == user_id)
        )
        user = user_result.scalar_one_or_none()
        if not user:
            await ws.send_error(user_id, "Please upload your resume first")
            return

        job_titles = command.get("job_titles") or user.target_job_titles or []
        locations = command.get("locations") or user.target_locations or []

        if not job_titles:
            await ws.send_error(user_id, "Please set job title preferences first")
            return

        import asyncio
        asyncio.create_task(
            run_job_search(
                user_id=user_id,
                job_titles=job_titles,
                locations=locations,
                remote_preference=user.remote_preference,
                platforms=["indeed", "linkedin"],
                max_results=25,
            )
        )
        await ws.send_status(user_id, "search_started", {"job_titles": job_titles})

    elif action == "approve_job":
        job_id = command.get("job_id")
        if job_id:
            result = await db.execute(
                select(JobListing).where(JobListing.id == job_id)
            )
            job = result.scalar_one_or_none()
            if job:
                job.status = "approved"
                app = Application(job_id=job.id, user_id=user_id, status="pending")
                db.add(app)
                await db.commit()
                await ws.send_status(
                    user_id, "job_approved", {"job_id": job_id, "title": job.title}
                )

    elif action == "reject_job":
        job_id = command.get("job_id")
        if job_id:
            result = await db.execute(
                select(JobListing).where(JobListing.id == job_id)
            )
            job = result.scalar_one_or_none()
            if job:
                job.status = "skipped"
                await db.commit()

    elif action == "approve_all_above_score":
        min_score = command.get("min_score", 70)
        result = await db.execute(
            select(JobListing)
            .where(JobListing.user_id == user_id)
            .where(JobListing.fit_score >= min_score)
            .where(JobListing.status == "scored")
        )
        jobs = result.scalars().all()
        count = 0
        for job in jobs:
            job.status = "approved"
            app = Application(job_id=job.id, user_id=user_id, status="pending")
            db.add(app)
            count += 1
        await db.commit()
        await ws.send_status(
            user_id,
            "batch_approved",
            {"count": count, "min_score": min_score},
        )

    elif action == "prepare_documents":
        job_id = command.get("job_id")
        if job_id:
            result = await db.execute(
                select(Application).where(Application.job_id == job_id)
            )
            app = result.scalar_one_or_none()
            if app:
                import asyncio
                asyncio.create_task(
                    run_document_preparation(
                        application_id=app.id, user_id=user_id
                    )
                )

    elif action == "prepare_all_approved":
        result = await db.execute(
            select(Application)
            .where(Application.user_id == user_id)
            .where(Application.status == "pending")
        )
        apps = result.scalars().all()
        import asyncio
        for app in apps:
            asyncio.create_task(
                run_document_preparation(
                    application_id=app.id, user_id=user_id
                )
            )
        await ws.send_status(
            user_id, "preparing_all", {"count": len(apps)}
        )

    elif action == "fill_application":
        job_id = command.get("job_id")
        if job_id:
            result = await db.execute(
                select(Application).where(Application.job_id == job_id)
            )
            app = result.scalar_one_or_none()
            if app:
                import asyncio
                asyncio.create_task(run_form_filling(application_id=app.id))

    elif action == "update_preferences":
        field = command.get("field")
        value = command.get("value")
        if field and value is not None:
            user_result = await db.execute(
                select(UserProfile).where(UserProfile.id == user_id)
            )
            user = user_result.scalar_one_or_none()
            if user and hasattr(user, field):
                setattr(user, field, value)
                await db.commit()
                await ws.send_status(
                    user_id,
                    "preferences_updated",
                    {"field": field, "value": value},
                )

    elif action == "open_browser":
        platform = command.get("platform", "linkedin")
        from app.services.browser_manager import get_browser_manager
        bm = get_browser_manager()
        await bm.open_login_page(platform)
        await ws.send_status(
            user_id,
            "browser_opened",
            {"platform": platform, "message": f"Please log in to {platform}"},
        )


@router.websocket("/ws/chat")
async def websocket_chat(websocket: WebSocket):
    """WebSocket endpoint for chat and real-time status updates."""
    user_id = 1  # Single-user app
    ws = get_ws_manager()
    await ws.connect(user_id, websocket)

    chat_service = ChatService()

    try:
        while True:
            data = await websocket.receive_json()
            msg_type = data.get("type", "chat_message")

            if msg_type == "chat_message":
                content = data.get("payload", {}).get("content", "")
                if not content:
                    continue

                async with async_session() as db:
                    # Load history
                    history = await load_chat_history(db, user_id)

                    # Build context
                    context = await build_context(db, user_id)

                    # Save user message
                    await save_message(db, user_id, "user", content)

                    # Get AI response
                    reply, command = await chat_service.process_message(
                        content, history, context
                    )

                    # Save assistant response
                    await save_message(
                        db,
                        user_id,
                        "assistant",
                        reply,
                        metadata={"command": command} if command else None,
                    )

                    # Send response
                    await ws.send_chat_response(user_id, reply)

                    # Execute command if present
                    if command:
                        await execute_command(command, user_id, db)

            elif msg_type == "ping":
                await websocket.send_json({"type": "pong"})

    except WebSocketDisconnect:
        ws.disconnect(user_id)
    except Exception as e:
        ws.disconnect(user_id)
