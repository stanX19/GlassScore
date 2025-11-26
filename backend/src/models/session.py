from pydantic import BaseModel
from pydantic.fields import FieldInfo

class TextContent(BaseModel):
    text: str
    key: str  #filename
    source: str

class UserProfile(BaseModel):
    name: str
    age: int
    gender: str
    income: int
    loan_amount: int
    loan_term: int

class EvaluationEvidence(BaseModel):
    id: int = 0
    score: int
    description: str
    citation:  str
    source: str
    valid: bool = True
    invalidate_reason: str = ""

class AppSession(BaseModel):
    session_id: int
    text_content_list: list[TextContent] = []
    evidence_list: list[EvaluationEvidence] = []
    user_profile: UserProfile | None = None

class AttachContentRequest(BaseModel):
    session_id: int
    text_content: TextContent

class UpdateProfileRequest(BaseModel):
    session_id: int
    user_profile: UserProfile

class UpdateEvidenceRequest(BaseModel):
    session_id: int
    evidence_id: int
    valid: bool
    invalidate_reason: str = ""
