from fastapi import APIRouter, HTTPException, status
from fastapi.responses import StreamingResponse
from src.models.evaluate import EvaluationRequest, EvaluationEvidence
from src.models.session import TextContent, AttachContentRequest
from src.services.evaluation.main_evaluator import evaluate_loan_stream
from src.services.session import session_service
from sse_starlette.sse import EventSourceResponse
import json

router = APIRouter()

@router.post("/create")
async def create_session():
    session = await session_service.create_session()
    return session

@router.get("/get")
async def get_session(session_id: int):
    session = await session_service.get_session(session_id)
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")
    return session

@router.post("/attach")
async def add_text_content(content: AttachContentRequest):
    session = await session_service.add_text_content(content.session_id, content.text_content)
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")
    return session