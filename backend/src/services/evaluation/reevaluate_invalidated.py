"""
Re-evaluation service for invalidated evidence.
Handles LLM-based re-assessment of evidence marked invalid by users.
"""
import json

from langchain_core.messages import SystemMessage, HumanMessage, AIMessage

from src.models.session import EvaluationEvidence, TextContent, AppSession
from src.llm.rotating_llm import rotating_llm


async def reevaluate_invalidated_evidence(
    session: AppSession,
    original_evidence: EvaluationEvidence
) -> list[EvaluationEvidence]:
    """
    Re-evaluate invalidated evidence using conversational LLM format.
    
    Uses the conversation format:
    - System: Original evaluation prompt with full text
    - Assistant: Original LLM response (score, citation, description)
    - Human: User's invalidation reason
    
    The LLM can then:
    1. Accept the invalidation and provide corrected assessment (typically 0 or +2)
    2. Reject the invalidation if the user's reason is unreasonable (rare)
    
    Args:
        session: The session containing text content and evidence
        original_evidence: The evidence that was invalidated
        
    Returns:
        List containing exactly one EvaluationEvidence item (single-item list for consistency)
    """
    
    # Retrieve original text content if available
    original_text = None
    if original_evidence.text_content_key:
        text_content = session.text_content_dict.get(original_evidence.text_content_key)
        if text_content:
            original_text = text_content.text
    
    # If no original text found, we can't properly re-evaluate
    if not original_text:
        return [EvaluationEvidence(
            score=0,
            description=f"Cannot re-evaluate Evidence #{original_evidence.id}: Original text not found",
            citation="",
            source="Re-evaluation Error",
            text_content_key=None
        )]
    
    # Build conversation messages
    system_prompt = f"""You are a credit score evaluator for a bank. Your task is to analyze text from a loan applicant and evaluate their behavior.

Analyze the text for behavioral signals and assign a score based on the following criteria:
- GOOD: 2 (Verified with evidence, logical behavior, stable employment)
- NORMAL: 0 (Neutral, standard behavior)
- MINOR ISSUE: -5 (Slight concerns, illogical description, suspicious writings)
- WARNING: -10 (Red flags, gambling, instability, high risk, major inconsistencies)
"""

    assistant_response = json.dumps({
		"score": original_evidence.score,
		"citation": original_evidence.citation,
		"description": original_evidence.description
	})
    system_prompt2 = """Please re-evaluate the original text considering this feedback. You have two options:

1. **Accept the invalidation**: If the reviewer's concern is valid, provide a corrected assessment. Typically this would be:
   - Score 0 (neutral/no evidence) if the original interpretation was wrong
   - Score +2 if there's actually positive information that was missed
   - Only use negative scores if there's genuinely concerning information

2. **Reject the invalidation**: If the reviewer's reason is unreasonable or contradicts clear evidence in the text, you may maintain the original assessment. However, this should be RARE and only when the original evaluation was clearly correct.

Return a JSON object with:
- "action": Either "accept" or "reject"
- "reasoning": Brief explanation of your decision (max 20 words)
- "evidence": If action is "accept", provide a list of new evidence items (same format as before). If "reject", return empty list.

Each evidence item should have:
- "score": The integer score (2, 0, -5, or -10)
- "citation": Exact excerpt supporting this evaluation (max 10 words)
- "description": Brief explanation (max 15 words)
"""

    # Build messages list for LLM
    messages = [
        SystemMessage(system_prompt),
        HumanMessage(f"Original Text to Evaluate: {original_text}"),
        AIMessage(assistant_response),
        SystemMessage("User marked this evidence as INVALID"),
        SystemMessage(system_prompt2),
        HumanMessage(original_evidence.invalidate_reason.split("Reason: ")[1]),
    ]
    print(f"Invalidation reevaluate started {original_evidence.invalidate_reason}")

    try:
        response = await rotating_llm.send_message_get_json(
            messages=messages,
            temperature=0.3
        )
        print(f"Invalidation reevaluate ended {response.get('json', '')}")
        
        if response["status"] == "ok" and "json" in response:
            data = response["json"]
            action = data.get("action", "accept")
            reasoning = data.get("reasoning", "No reasoning provided")
            evidence_list = data.get("evidence", [])
            
            if action == "reject":
                # LLM rejected the invalidation - keep original score
                return [EvaluationEvidence(
                    score=original_evidence.score,
                    description=f"Re-evaluation upheld original assessment: {original_evidence.description} With reason: {reasoning}",
                    citation=original_evidence.citation,
                    source=original_evidence.source,
                    text_content_key=original_evidence.text_content_key
                )]
            else:
                # LLM accepted invalidation - return first corrected evidence or default
                if evidence_list:
                    item = evidence_list[0]  # Take only the first evidence
                    return [EvaluationEvidence(
                        score=item.get("score", 0),
                        description=item.get("description", "No description provided."),
                        citation=item.get("citation", ""),
                        source=original_evidence.source,
                        text_content_key=original_evidence.text_content_key
                    )]
                else:
                    return [EvaluationEvidence(
                        score=0,
                        description=f"Re-evaluation accepted invalidation: {reasoning}",
                        citation="",
                        source=original_evidence.source,
                        text_content_key=original_evidence.text_content_key
                    )]

        return [EvaluationEvidence(
            score=0,
            description=f"Failed to re-evaluate: {response.get('text', 'Unknown error')}",
            citation="",
            source="Re-evaluation Error",
            text_content_key=None
        )]
    except Exception as e:
        return [EvaluationEvidence(
            score=0,
            description=f"Error during re-evaluation: {str(e)}",
            citation="",
            source="Re-evaluation Error",
            text_content_key=None
        )]


if __name__ == "__main__":
    import asyncio
    
    # Create test session with sample data
    test_text = "I work at a stable company for 5 years and have consistent income. I gamble occasionally on weekends."
    
    test_session = AppSession(
        session_id=1,
        text_content_dict={
            "test.txt": TextContent(
                text=test_text,
                key="test.txt",
                source="Test File"
            )
        }
    )
    
    # Create original evidence that will be invalidated
    original_evidence = EvaluationEvidence(
        id=1,
        score=2,
        description="Stable employment for 5 years shows reliability",
        citation="work at a stable company for 5 years",
        source="original evaluation",
        valid=False,
        invalidate_reason="User feedback: Reason: This doesn't account for the gambling behavior mentioned",
        text_content_key="test.txt"
    )
    
    # Run re-evaluation
    async def test_reevaluation():
        print("Original Evidence:")
        print(f"  Score: {original_evidence.score}")
        print(f"  Description: {original_evidence.description}")
        print(f"  Citation: {original_evidence.citation}")
        print(f"  Invalidation: {original_evidence.invalidate_reason}")
        print("\nRe-evaluating...\n")
        
        new_evidence_list = await reevaluate_invalidated_evidence(
            session=test_session,
            original_evidence=original_evidence
        )
        
        print("Re-evaluation Results:")
        for i, evidence in enumerate(new_evidence_list, 1):
            print(f"\nEvidence {i}:")
            print(f"  Score: {evidence.score}")
            print(f"  Description: {evidence.description}")
            print(f"  Citation: {evidence.citation}")
            print(f"  Source: {evidence.source}")
    
    asyncio.run(test_reevaluation())
