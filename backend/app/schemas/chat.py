from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel


class ChatMessageResponse(BaseModel):
    id: int
    role: str
    content: str
    message_type: str = "text"
    metadata_json: dict | None = None
    created_at: datetime

    class Config:
        from_attributes = True


class WSMessage(BaseModel):
    type: str  # chat_response, status_update, job_found, application_update, error
    payload: dict[str, Any]
    timestamp: datetime


class WSCommand(BaseModel):
    type: str  # chat_message, start_search, approve_job, pause, resume
    payload: dict[str, Any] = {}
