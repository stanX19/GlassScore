from typing import Any

from pydantic import BaseModel, Field, ConfigDict
from src.models.session import TextContent, UserProfile, EvaluationEvidence


class EvaluationRequest(BaseModel):
    session_id: int
    user_profile: UserProfile
    loan_text: str

class LLMEvaluationParams(BaseModel):
    text_content: TextContent

class WebEvaluationParams(BaseModel):
    llm_params: LLMEvaluationParams
    web_query: str
    query_limit: int = 5

class FileAttachParams(BaseModel):
    session_id: int
    text_content: TextContent

