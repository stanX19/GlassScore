from src.models.evaluate import EvaluationRequest, EvaluationEvidence, LLMEvaluationParams
from src.models.session import TextContent

from src.services.evaluation.ml_evaluator import ml_evaluate_loan
from src.services.evaluation.llm_evaluator import llm_evaluate_loan
import asyncio

from src.services.evaluation.web_evaluator import web_evaluate


async def evaluate_loan_stream(request: EvaluationRequest):
    ml_task = asyncio.create_task(ml_evaluate_loan(request.user_profile))

    pending_tasks: list[asyncio.Task] = [
        ml_task,
        asyncio.create_task(llm_evaluate_loan(
            LLMEvaluationParams(text_content=TextContent(
                text=request.loan_text,
                key="loan text",
                source="user upload"
            )),
            [ml_task])
        ),
        asyncio.create_task(web_evaluate(request, request.user_profile.name))
    ]

    while pending_tasks:
        done, pending_tasks = await asyncio.wait(pending_tasks, return_when=asyncio.FIRST_COMPLETED)
        
        for task in done:
            try:
                evidence = await task
                yield evidence
            except Exception as e:
                yield EvaluationEvidence(
                    score=0,
                    description=f"Error in evaluation: {str(e)}",
                    source="System Error"
                )