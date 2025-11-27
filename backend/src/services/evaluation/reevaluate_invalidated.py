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
    
    The LLM accepts the invalidation and can either:
    1. Do nothing (return empty list) if the evidence should simply be removed
    2. Provide one new evidence item if there's alternative information to consider
    
    Args:
        session: The session containing text content and evidence
        original_evidence: The evidence that was invalidated
        
    Returns:
        Empty list if no new evidence, or list with one EvaluationEvidence item
    """
    
    # Retrieve original text content if available
    original_text = None
    if original_evidence.text_content_key:
        text_content = session.text_content_dict.get(original_evidence.text_content_key)
        if text_content:
            original_text = text_content.text
    if original_text is None:
        original_text = original_evidence.description
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
- GOOD: 1 (Verified with evidence, logical behavior, stable employment)
- NORMAL: 0 (Neutral, standard behavior)
- MINOR ISSUE: -5 (Slight concerns, illogical description, suspicious writings)
- WARNING: -10 (Red flags, gambling, instability, high risk, major inconsistencies)
"""

    assistant_response = json.dumps({
		"score": original_evidence.score,
		"citation": original_evidence.citation,
		"description": original_evidence.description
	})
    system_prompt2 = """You must ONLY consider feedback that contradicts the specific evidence the user invalidated.

STRICT RULES:
1. You are NOT allowed to search for or cite any part of the original text unless it directly relates to the feedback.
2. You must NOT introduce new concerns, risks, job stability claims, gambling mentions, or any new insights that the user did not bring up in their feedback.
3. Your ONLY task is to decide:
   - Should the evidence be removed? (then return an empty list)
   - Or is there a corrected version of THIS SAME evidence based ONLY on the user's reasoning?

4. You may NOT generate evidence about any topic EXCEPT the one covered by the invalidated evidence.

OUTPUT FORMAT:
Return a JSON object with:
- "reasoning": max 20 words explaining why the evidence is removed or corrected.
- "evidence": EITHER empty list or exactly one item.

Each evidence item:
- "score": one of 1, 0, -5, -10
- "citation": up to 10 words FROM TEXT, ONLY if related to feedback
- "description": max 15 words, ONLY correcting the same topic as the original evidence

If the feedback says the evidence is irrelevant, insignificant, outdated, incorrect, or should be removed, return an empty list.
If the feedback clarifies the same topic, provide a corrected single evidence item.
"""

    try:
        invalidation_reason = original_evidence.invalidate_reason.split("Reason: ")[1]
    except IndexError:
        invalidation_reason = original_evidence.invalidate_reason
    # Build messages list for LLM
    messages = [
        SystemMessage(system_prompt),
        HumanMessage(f"Original Text to Evaluate: {original_text}"),
        AIMessage(assistant_response),
        SystemMessage("User marked this evidence as INVALID"),
        SystemMessage(system_prompt2),
        HumanMessage(invalidation_reason),
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
            reasoning = data.get("reasoning", "No reasoning provided")
            evidence_list = data.get("evidence", [])
            
            # LLM accepted invalidation - return new evidence if provided, otherwise empty list
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
                # No new evidence - invalidation accepted, evidence removed
                return []

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
    test_text = "I work at a stable company for 5 years and have consistent income. I also gamble in my free time"
    
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
        score=-20,
        # description="Stable job and income",
        # citation="stable company for 5 years",
        description="Gambling is a huge red flag.",
        citation="I also gamble in my free time",
        source="original evaluation",
        valid=False,
        invalidate_reason="this is insignificant",
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
