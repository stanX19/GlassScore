from fastapi import APIRouter, HTTPException, status
from fastapi.responses import StreamingResponse
from src.models.evaluate import EvaluationRequest, EvaluationEvidence
from src.models.session import TextContent, AppSession, UpdateEvidenceRequest
from src.services.evaluation.main_evaluator import start_evaluation
from src.services.session import session_service
from sse_starlette.sse import EventSourceResponse
import json
import asyncio

router = APIRouter()


@router.post("/start")
async def start_loan_evaluation(request: EvaluationRequest):
    """
    Triggers evaluation process without streaming.
    Evaluation runs in background and pushes results to session queue.
    """
    session = await session_service.get_session(request.session_id)
    if session is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")
    
    if session.is_evaluating:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Evaluation already in progress")
    
    # Start evaluation in background
    asyncio.create_task(start_evaluation(request.session_id))
    
    return {"message": "Evaluation started", "session_id": request.session_id}


@router.post("/stream")
async def stream_evaluation_results(request: EvaluationRequest):
    """
    Streams evaluation results from session queue.
    Stream stays open indefinitely to receive re-evaluation results.
    Only closes on client disconnect.
    """
    session = await session_service.get_session(request.session_id)
    if session is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")
    
    async def event_generator():
        while True:
            try:
                # Wait for evidence from queue (blocks until available)
                evidence = await session.evidence_queue.get()
                
                # Only add to evidence_list if it's actual evidence, not system events
                if evidence.event_type == "evidence":
                    await session_service.add_evidence(session.session_id, evidence)
                
                yield {"data": evidence.model_dump_json()}
                
                # Send completion event but DON'T close stream
                # Keep listening for re-evaluation results
                    
            except Exception as e:
                error_evidence = EvaluationEvidence(
                    score=0,
                    description=f"Error streaming evidence: {str(e)}",
                    source="System Error"
                )
                yield {"data": error_evidence.model_dump_json()}
                break

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
