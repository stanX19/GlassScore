from fastapi import APIRouter, HTTPException, status
from fastapi.responses import StreamingResponse
from src.models.evaluate import EvaluationRequest, EvaluationEvidence
from src.models.session import TextContent, AppSession, UpdateEvidenceRequest
from src.services.evaluation.main_evaluator import evaluate_loan_stream
from src.services.session import session_service
from sse_starlette.sse import EventSourceResponse
import json

router = APIRouter()


@router.post("/stream")
async def evaluate_loan_sse_robust(request: EvaluationRequest):
    session: AppSession = await session_service.get_session(request.session_id)
    async def event_generator():
        if session is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")
        async for evidence in evaluate_loan_stream(request):
            await session_service.add_evidence(session.session_id, evidence)
            yield {"data": evidence.model_dump_json()}

    return EventSourceResponse(event_generator())


@router.post("/evidence/update")
async def update_evidence(request: UpdateEvidenceRequest):
    try:
        session = await session_service.update_evidence(
            session_id=request.session_id,
            evidence_id=request.evidence_id,
            valid=request.valid,
            invalidate_reason=request.invalidate_reason
        )
        return session
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
