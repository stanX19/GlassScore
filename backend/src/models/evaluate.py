from typing import Any

from pydantic import BaseModel, Field, ConfigDict
from src.models.session import TextContent, UserProfile, EvaluationEvidence


class EvaluationRequest(BaseModel):
    session_id: int
