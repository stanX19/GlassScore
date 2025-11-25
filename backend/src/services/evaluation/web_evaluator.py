from src.models.evaluate import EvaluationRequest, EvaluationEvidence
import asyncio

async def web_evaluate(request: EvaluationRequest, query: str) -> EvaluationEvidence:
    # Mock web search delay
    await asyncio.sleep(6)
    
    # Mock result
    return EvaluationEvidence(
        score=-10,
        description=f"Web search for '{query}' found concerning reports on gambling forums.",
        source="linkedin.com"
    )