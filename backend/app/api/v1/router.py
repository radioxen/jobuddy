from fastapi import APIRouter

from app.api.v1 import users, jobs, applications, browser, chat

api_v1_router = APIRouter()

api_v1_router.include_router(users.router, prefix="/users", tags=["users"])
api_v1_router.include_router(jobs.router, prefix="/jobs", tags=["jobs"])
api_v1_router.include_router(
    applications.router, prefix="/applications", tags=["applications"]
)
api_v1_router.include_router(browser.router, prefix="/browser", tags=["browser"])
api_v1_router.include_router(chat.router, tags=["chat"])
