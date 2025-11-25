from typing import Any

from pydantic import BaseModel, Field, ConfigDict


class Action(BaseModel):
    name: str
    args: dict
    needs_confirmation: bool = False
    needs_personal_data_confirmation: bool = False
    frontend_execution: bool = False


class ChatResponse(BaseModel):
    thread_id: str
    text: str
    meta: dict[str, Any] = {}
    action: Action | None = None       # Optional action prompt
    error: str | None = None           # Optional error message
    status: str = "Success"            # "Success", "pending_confirmation", "Error"


class SendMessage(BaseModel):
    thread_id: str
    text: str
    current_user: int


class ConfirmAction(BaseModel):
    thread_id: str
    approved: bool

class AttachContent(BaseModel):
    thread_id: str
    content: str                     # Base64 content for images/files, or plain text
    content_type: str = "image"      # 'file', 'image', or 'text'
    mime_type: str | None = None     # Required for 'file' type (e.g., 'application/pdf')


class ClearMemory(BaseModel):
    thread_id: str


class ContinueWithToolResult(BaseModel):
    thread_id: str
    text: str
