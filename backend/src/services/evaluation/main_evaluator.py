from src.models.evaluate import EvaluationRequest, EvaluationEvidence
from src.services.session import session_service
from src.services.evaluation.ml_evaluator import ml_evaluate_loan
from src.services.evaluation.llm_evaluator import llm_evaluate_loan
from src.services.evaluation.web_evaluator import generate_web_tasks
import asyncio


async def start_evaluation(session_id: int) -> None:
    """
    Triggers evaluation process in background without streaming.
    Results are pushed to session's evidence queue for later streaming.
    """
    session = await session_service.get_session(session_id)
    if not session:
        raise ValueError(f"Session {session_id} not found")

    # Initialize evaluation
    await session_service.start_evaluation(session_id)

    # Send start event
    start_event = EvaluationEvidence(
        score=0,
        description="Evaluation started",
        citation="",
        source="System",
        event_type="evaluation_start"
    )
    await session_service.push_evidence_to_stream(session_id, start_event)

    # 1. ML Evaluation
    ml_task = asyncio.create_task(ml_evaluate_loan(session.user_profile))

    # 2. Web Evaluation Tasks
    web_tasks = await generate_web_tasks(session_id)

    # 3. LLM Evaluation Tasks for all text content
    llm_tasks = []
    if session.text_content_dict:
        for content in session.text_content_dict.values():
            llm_tasks.append(asyncio.create_task(llm_evaluate_loan(content, [ml_task])))

    # Combine all tasks
    all_tasks = [ml_task] + web_tasks + llm_tasks
    session.pending_tasks = len(all_tasks)

    # Background task to process results and push to queue
    async def process_tasks():
        for future in asyncio.as_completed(all_tasks):
            try:
                result = await future
                
                # Result can be a single Evidence or a list of Evidence
                if isinstance(result, list):
                    for item in result:
                        await session_service.push_evidence_to_stream(session_id, item)
                elif isinstance(result, EvaluationEvidence):
                    await session_service.push_evidence_to_stream(session_id, result)
                    
            except Exception as e:
                error_evidence = EvaluationEvidence(
                    score=0,
                    description=f"Error in evaluation task: {str(e)}",
                    source="System Error"
                )
                await session_service.push_evidence_to_stream(session_id, error_evidence)
        
        # Send completion event
        completion_event = EvaluationEvidence(
            score=0,
            description="Initial evaluation completed",
            citation="",
            source="System",
            event_type="evaluation_complete"
        )
        await session_service.push_evidence_to_stream(session_id, completion_event)
        await session_service.finish_evaluation(session_id)

    # Start background processing
    asyncio.create_task(process_tasks())

if __name__ == "__main__":
    from src.models.session import UserProfile, TextContent
    
    async def main():
        # 1. Create a session
        user_profile = UserProfile(
            name="Joemer Ramos",
            age=30,
            gender="Male",
            income=100000,
            loan_amount=20000,
            loan_term=12
        )
        session = await session_service.create_session(user_profile)
        print(f"Created session {session.session_id}")

        # 2. Add text content
        content1 = TextContent(
            text="I am a software engineer at Google. I have been working there for 2 years. I am looking for a loan to buy a house.",
            key="intro.txt",
            source="user_upload"
        )
        await session_service.add_text_content(session.session_id, content1)
        
        content2 = TextContent(
            text="I also have a side hustle as a tech influencer. I make YouTube videos about coding and productivity.",
            key="side_hustle.txt",
            source="user_upload"
        )
        await session_service.add_text_content(session.session_id, content2)
        
        content3 = TextContent(
            text="I sometimes gamble on sports, but it's just for fun. I don't have any addiction.",
            key="gambling.txt",
            source="user_upload"
        )
        await session_service.add_text_content(session.session_id, content3)
        
        print("Added 3 text content items")

        # 3. Start evaluation (non-blocking)
        print("Starting evaluation...")
        await start_evaluation(session.session_id)
        
        # 4. Stream results from queue
        print("Streaming results...")
        while True:
            evidence = await session.evidence_queue.get()
            print(f"\nReceived Evidence:")
            print(f"  Score: {evidence.score}")
            print(f"  Description: {evidence.description}")
            print(f"  Source: {evidence.source}")
            if evidence.citation:
                print(f"  Citation: {evidence.citation}")
            if evidence.event_type == "evaluation_complete":
                break

    import sys
    if sys.platform.startswith("win"):
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(main())