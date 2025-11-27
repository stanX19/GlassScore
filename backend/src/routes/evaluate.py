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


@router.post("/summarise_everything")
async def summarise_everything(request: EvaluationRequest):
    """
    Generates a comprehensive summary of all evaluation evidence using LLM.
    Returns a natural language summary of the loan evaluation results.
    """
    from src.llm.rotating_llm import rotating_llm
    
    session = await session_service.get_session(request.session_id)
    if session is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")
    
    if not session.evidence_list:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail="No evidence found. Please run evaluation first."
        )
    
    # Prepare evidence data for summarization
    evidence_data = []
    total_score = 0
    valid_count = 0
    
    for evidence in session.evidence_list:
        if evidence.event_type == "evidence" and evidence.valid:
            evidence_data.append({
                "score": evidence.score,
                "description": evidence.description,
                "source": evidence.source,
                "citation": evidence.citation
            })
            total_score += evidence.score
            valid_count += 1

    total_score = min(100, max(0, total_score))

    if valid_count == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No valid evidence found to summarize."
        )
    
    # Prepare user context
    user_context = ""
    if session.user_profile:
        user_context = f"Applicant Profile: Name: {session.user_profile.name}, Age: {session.user_profile.age}, Gender: {session.user_profile.gender}\n"
    
    if session.loan_application:
        user_context += f"Loan Application: Amount: ${session.loan_application.loan_amnt}, Income: ${session.loan_application.person_income}, Grade: {session.loan_application.loan_grade}\n"
    
    # Create prompt for LLM
    prompt = f"""You are a loan evaluation analyst. Generate a comprehensive summary of the loan evaluation results.

{user_context}

Total Score: {total_score:.1f}/100
Total Evidence Reviewed: {valid_count}

Evidence Details:
{json.dumps(evidence_data, indent=2)}

Please provide:
1. An overall assessment of the loan application (2-3 sentences)
2. Key positive factors (bullet points)
3. Key risk factors or concerns (bullet points)
4. Final recommendation (Approve/Conditional Approve/Deny with reasoning)

Keep the summary professional, concise, and actionable."""

    try:
        # Get summary from LLM
        result = await rotating_llm.send_message(prompt, temperature=0.3)
        
        if result["status"] != "ok":
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to generate summary: {result['text']}"
            )
        
        return {
            "session_id": request.session_id,
            "average_score": round(total_score, 1),
            "total_evidence": valid_count,
            "summary": result["text"],
            "model_used": result["model"]
        }
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error generating summary: {str(e)}"
        )