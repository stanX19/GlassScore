import asyncio
import sys
import os

# Add backend to sys.path to allow imports from src
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../")))

from src.services.session import session_service
from src.models.session import TextContent, UserProfile
from src.services.evaluation.web_evaluator import generate_web_tasks

async def main():
    print("Starting Web Search Verification...")

    # 1. Create a session
    print("Creating session...")
    session = await session_service.create_session(
        user_profile=UserProfile(
            name="Jermaine Cheah",
            age=30,
            gender="Male",
            income=50000,
            loan_amount=1000,
            loan_term=12
        )
    )
    session_id = session.session_id
    print(f"Session created with ID: {session_id}")

    # 2. Add text content
    print("Adding text content...")
    await session_service.add_text_content(
        session_id,
        TextContent(
            text="I am hereby applying for a loan to renovate the office. I am the CTO of mindhive and i have stable income. I wish to repay all in 1 year within 12 installments. total RM10000000",
            key="intro.txt",
            source="user_upload"
        )
    )

    # 3. Generate web tasks
    print("Generating web tasks...")
    tasks = await generate_web_tasks(session_id)
    
    if not tasks:
        print("No tasks generated. Check LLM or logic.")
        return

    print(f"Generated {len(tasks)} tasks. Waiting for completion...")
    
    # 4. Run tasks
    results = await asyncio.gather(*tasks)
    
    # 5. Print results
    print("\nVerification Results:")
    total_evidence = 0
    for i, evidence_list in enumerate(results):
        print(f"\nTask {i+1} Results:")
        if not evidence_list:
            print("  No evidence found.")
        for evidence in evidence_list:
            total_evidence += 1
            print(f"  - Score: {evidence.score}")
            print(f"    Description: {evidence.description}")
            print(f"    Citation: {evidence.citation[:100]}...") # Truncate for display
            print(f"    Source: {evidence.source}")

    print(f"\nTotal Evidence Items: {total_evidence}")
    print("Verification Complete.")

if __name__ == "__main__":
    if sys.platform.startswith("win"):
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(main())
