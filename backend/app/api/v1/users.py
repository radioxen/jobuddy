import os
import uuid

from fastapi import APIRouter, Depends, File, UploadFile, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db
from app.models.user import UserProfile
from app.schemas.user import (
    UserProfileResponse,
    UserPreferencesUpdate,
    UserPreferencesResponse,
)
from app.services.resume_parser import ResumeParser

router = APIRouter()


async def get_or_create_user(db: AsyncSession) -> UserProfile:
    """Get the single user or create one."""
    result = await db.execute(select(UserProfile).limit(1))
    user = result.scalar_one_or_none()
    if not user:
        user = UserProfile(full_name="", email="")
        db.add(user)
        await db.commit()
        await db.refresh(user)
    return user


@router.post("/upload-resume", response_model=UserProfileResponse)
async def upload_resume(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
):
    """Upload a DOCX resume, parse it, and create/update user profile."""
    if not file.filename.endswith(".docx"):
        raise HTTPException(
            status_code=400,
            detail="Only .docx files are supported",
        )

    if file.size and file.size > 10 * 1024 * 1024:  # 10MB limit
        raise HTTPException(status_code=400, detail="File too large (max 10MB)")

    # Save file with UUID name
    file_ext = os.path.splitext(file.filename)[1]
    safe_filename = f"{uuid.uuid4()}{file_ext}"
    file_path = os.path.join(settings.UPLOAD_DIR, safe_filename)

    content = await file.read()
    with open(file_path, "wb") as f:
        f.write(content)

    # Parse resume with GPT
    parser = ResumeParser()
    parsed_data = parser.parse(file_path)

    # Get or create user and update
    user = await get_or_create_user(db)
    user.original_resume_path = file_path
    user.parsed_resume_json = parsed_data
    user.full_name = parsed_data.get("full_name", user.full_name)
    user.email = parsed_data.get("email", user.email)
    user.phone = parsed_data.get("phone", user.phone)
    user.linkedin_url = parsed_data.get("linkedin_url", user.linkedin_url)

    await db.commit()
    await db.refresh(user)

    return user


@router.get("/profile", response_model=UserProfileResponse)
async def get_profile(db: AsyncSession = Depends(get_db)):
    """Get the current user profile."""
    user = await get_or_create_user(db)
    return user


@router.put("/preferences", response_model=UserPreferencesResponse)
async def update_preferences(
    prefs: UserPreferencesUpdate,
    db: AsyncSession = Depends(get_db),
):
    """Update job search preferences."""
    user = await get_or_create_user(db)

    update_data = prefs.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(user, field, value)

    await db.commit()
    await db.refresh(user)

    return UserPreferencesResponse.model_validate(user)


@router.get("/preferences", response_model=UserPreferencesResponse)
async def get_preferences(db: AsyncSession = Depends(get_db)):
    """Get current job search preferences."""
    user = await get_or_create_user(db)
    return UserPreferencesResponse.model_validate(user)
