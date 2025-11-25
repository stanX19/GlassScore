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
    score: int
    description: str
    source: str

class AppSession(BaseModel):
    session_id: int
    text_content_list: list[TextContent] = []
    evidence_list: list[EvaluationEvidence] = []
    user_profile: UserProfile | None = None

class AttachContentRequest(BaseModel):
    session_id: int
    text_content: TextContent
