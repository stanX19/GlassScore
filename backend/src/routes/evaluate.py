from fastapi import APIRouter, HTTPException, status
from fastapi.responses import StreamingResponse
from src.models.evaluate import EvaluationRequest, EvaluationEvidence
from src.models.session import TextContent, AppSession
from src.services.evaluation.main_evaluator import evaluate_loan_stream
from src.services.session import session_service
from sse_starlette.sse import EventSourceResponse
import json

router = APIRouter()


@router.post("/stream")
async def evaluate_loan_sse_robust(request: EvaluationRequest):
    session: AppSession = await session_service.get_session(request.session_id)
    async def event_generator():
        async for evidence in evaluate_loan_stream(request):
            await session_service.add_evidence(session.session_id, evidence)
            yield {"data": evidence.model_dump_json()}

    return EventSourceResponse(event_generator())
