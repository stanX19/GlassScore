from pydantic import BaseModel, Field
from pydantic.fields import FieldInfo
import asyncio
from typing import Optional
from src.models.ml_model import LoanApplication

class TextContent(BaseModel):
    text: str
    key: str  #filename
    source: str

class UserProfile(BaseModel):
    name: str
    age: int
    gender: str

class EvaluationEvidence(BaseModel):
    id: int = 0
    score: int
    description: str
    citation:  str
    source: str
    valid: bool = True
    invalidate_reason: str = ""
    event_type: str = "evidence"  # "evidence" or "evaluation_complete"
    text_content_key: Optional[str] = None  # References TextContent for re-evaluation

class AppSession(BaseModel):
    model_config = {"arbitrary_types_allowed": True}
    
    session_id: int
    text_content_dict: dict[str, TextContent] = {}  # key -> TextContent for O(1) lookup
    evidence_list: list[EvaluationEvidence] = []
    user_profile: UserProfile | None = None
    loan_application: LoanApplication | None = None
    
    # Queue for streaming evidence (not serialized)
    evidence_queue: Optional[asyncio.Queue] = Field(default=None, exclude=True)
    is_evaluating: bool = False
    pending_tasks: int = 0

class AttachContentRequest(BaseModel):
    session_id: int
    text_content: TextContent

class UpdateProfileRequest(BaseModel):
    session_id: int
    user_profile: UserProfile
    loan_application: LoanApplication

class UpdateEvidenceRequest(BaseModel):
    session_id: int
    evidence_id: int
    valid: bool
    invalidate_reason: str = ""
