import asyncio
import json
import os
import re
from asyncio import Task

from langchain_community.utilities import GoogleSearchAPIWrapper
from langchain_community.tools.tavily_search import TavilySearchResults
from langchain_core.tools import Tool

from src.models.evaluate import EvaluationEvidence
from src.models.session import UserProfile
from src.services.session import session_service
from src.llm.rotating_llm import rotating_llm
from src.services.evaluation.llm_evaluator import llm_evaluate_loan
from src.models.session import TextContent


async def _verify_search_results(
    search_results: list[dict],
    user_profile: UserProfile,
    query_objective: str
) -> list[int]:
    """
    Verify which search results are relevant and accurate for the search objective.
    For identity searches: verifies results match the applicant.
    For factual searches: verifies results are relevant and credible.
    Returns list of valid indexes (e.g., [0, 2] means results 0 and 2 are valid).
    """
    if not search_results:
        return []
    
    # Format indexed results for LLM
    indexed_results = ""
    for i, result in enumerate(search_results):
        indexed_results += f"\n--- Result Index {i} ---\n"
        indexed_results += f"Title: {result.get('title', 'Unknown')}\n"
        indexed_results += f"URL: {result.get('url', 'Unknown')}\n"
        indexed_results += f"Content: {result['content'][:500]}...\n"  # Limit content length
    
    prompt = f"""
    You are a search result verification specialist. Your task is to determine which web search results are relevant and useful for the given objective.
    
    Applicant Profile:
    {user_profile.model_dump_json(indent=2)}
    
    Search Objective:
    {query_objective}
    
    Search Results (indexed):
    {indexed_results}
    
    Instructions:
    Determine if this is an IDENTITY SEARCH or FACTUAL SEARCH:
    
    **IDENTITY SEARCH** (searching for a specific person):
    - Only mark results as valid if they refer to the SAME person as the applicant
    - Look for matching: exact name, employment, location, age, business specifics
    - Be STRICT: Similar names or professions are NOT enough - need concrete matching evidence
    - Reject results about different people with similar names
    
    **FACTUAL SEARCH** (checking facts, prices, general information):
    - Mark results as valid if they contain relevant, credible information for the objective
    - Accept authoritative sources, industry data, market information
    - Reject irrelevant, off-topic, or unreliable sources
    - Don't require identity matching - just topical relevance
    
    Return a JSON object with:
    - "search_type": Either "identity" or "factual"
    - "valid_indexes": A list of integer indexes for relevant results (e.g., [0, 2])
    - "reasoning": Brief explanation for each valid index
    
    If NO results are relevant, return an empty list for "valid_indexes".
    """
    
    try:
        response = await rotating_llm.send_message_get_json(
            messages=prompt,
            temperature=0.2  # Low temperature for strict verification
        )
        
        if response["status"] == "ok" and "json" in response:
            data = response["json"]
            search_type = data.get("search_type", "unknown")
            valid_indexes = data.get("valid_indexes", [])
            reasoning = data.get("reasoning", "No reasoning provided")
            
            print(f"Search verification ({search_type}): {len(valid_indexes)} valid out of {len(search_results)}")
            print(f"Valid indexes: {valid_indexes}")
            print(f"Reasoning: {reasoning}")
            
            return valid_indexes
        else:
            print(f"Failed to verify search results: {response.get('text')}")
            return []  # Conservative: reject all if verification fails
            
    except Exception as e:
        print(f"Error during identity verification: {e}")
        return []  # Conservative: reject all on error


async def _generate_queries(session_id: int) -> list[dict]:
    session = await session_service.get_session(session_id)
    if not session or not session.text_content_dict:
        return []

    # Combine all text content for context
    context_text = session.user_profile.model_dump_json(indent=2) + "\n\n"
    context_text += "\n\n".join([
        f"Source: {c.source}\nContent: {c.text}" for c in session.text_content_dict.values()
    ])

    prompt = f"""
    You are a background check specialist. Your goal is to verify the claims made by a loan applicant and check for any risk factors (gambling, fraud, negative news).

    Based on the following applicant information, generate 3 to 5 targeted web search queries.
    Focus on:
    1. Verifying their employment or business claims.
    2. Checking for negative news, lawsuits, or financial scandals.
    3. Identifying social media presence that might contradict their claims.
    4. Verifying their requested loan amount matches their purpose.

    Applicant Information:
    {context_text}

    Return a JSON object with a "queries" field, which is a list of objects. Each object should have:
    - "query": The search query string (natural language).
    - "objective": A brief explanation of what this query aims to find.
    """

    try:
        response = await rotating_llm.send_message_get_json(
            messages=prompt,
            temperature=0.3
        )
        
        if response["status"] == "ok" and "json" in response:
            queries = response["json"].get("queries", [])
            # Prepend applicant info to the objective for better context in later evaluation
            applicant_summary = f"Applicant: {session.user_profile.model_dump_json(indent=2)}"
            for q in queries:
                if "objective" in q:
                    q["objective"] = f"{applicant_summary}. Objective: {q['objective']}"
            # input(json.dumps(queries, indent=2))
            return queries
        else:
            print(f"Failed to generate web queries: {response.get('text')}")
            return []
            
    except Exception as e:
        print(f"Error generating web tasks: {e}")
        return []


async def _execute_web_task(query_task: Task, index: int, session_id: int, user_profile: UserProfile = None) -> list[EvaluationEvidence]:
    try:
        queries = await query_task
        if index < len(queries):
            item = queries[index]
            query = item.get("query")
            objective = item.get("objective")
            if query:
                return await web_evaluate(query, objective, session_id, user_profile)
    except Exception as e:
        print(f"Error in web task {index}: {e}")
    return []


async def generate_web_tasks(session_id: int) -> list[Task]:
    query_task = asyncio.create_task(_generate_queries(session_id))
    
    # Get user profile for identity verification
    session = await session_service.get_session(session_id)
    user_profile = session.user_profile if session else None
    
    tasks = []
    for i in range(5):
        tasks.append(asyncio.create_task(_execute_web_task(query_task, i, session_id, user_profile)))
    return tasks


async def web_evaluate(query: str, objective: str, session_id: int, user_profile: UserProfile = None) -> list[EvaluationEvidence]:
    print(f"Executing web search: {query}\n    Objective: {objective})")
    
    search_results = []

    if not os.environ.get("TAVILY_API_KEY"):
        await asyncio.sleep(2)  # Simulate delay
        return [EvaluationEvidence(
            score=0,
            description=f"TAVILY_API_KEY not found. Web search unavailable for '{query}'",
            citation="",
            source="web_search",
            text_content_key=None
        )]
    try:
        tool = TavilySearchResults(max_results=5)
        # Tavily returns a list of dicts with 'url', 'content'
        results = await tool.ainvoke(query)
        for r in results:
            result = {
                "content": r.get("content", ""),
                "url": r.get("url", "tavily_search"),
                "title": r.get("title", "") # Tavily might not always have title in simple invoke
            }
            print(json.dumps(result, indent=2))
            search_results.append(result)

    except Exception as e:
        print(f"Search failed for '{query}': {e}")
        return []

    if not search_results:
        return []
    
    # STAGE 1: Verify which results actually match the applicant
    if user_profile:
        valid_indexes = await _verify_search_results(search_results, user_profile, objective)
        if not valid_indexes:
            print(f"No search results matched the applicant's identity. Returning neutral evidence.")
            return [EvaluationEvidence(
                score=0,
                description=f"No exact match of '{query}' found on web",
                citation="",
                source="web_search",
                text_content_key=None
            )]
        
        # Filter to only valid results
        search_results = [search_results[i] for i in valid_indexes if i < len(search_results)]
        print(f"Proceeding with {len(search_results)} verified result(s)")
    else:
        print("Warning: No user profile provided for identity verification. Proceeding with all results.")

    # Combine all results into one text for the LLM
    combined_text = ""
    for i, result in enumerate(search_results):
        combined_text += f"--- Result {i+1} ---\n"
        combined_text += f"Title: {result.get('title', 'Unknown')}\n"
        combined_text += f"Content: {result['content']}\n\n"

    content = TextContent(
        text=combined_text,
        key=f"web_search_{query[:30]}",  # Use query prefix as base key
        source="web_search"
    )
    
    # Save TextContent to session so it can be retrieved during re-evaluation
    final_key = await session_service.save_text_content(session_id, content)
    
    evidences = await llm_evaluate_loan(content, objective=objective)
    valid_evidences = []
    # Post-process evidences to assign correct source URL and clean citations
    for evidence in evidences:
        # Clean citation
        if not evidence.citation:
            continue

        matcher1 = re.sub(r'[^a-zA-Z0-9]', '', evidence.citation).lower()
        
        # Find source
        # We look for the citation in the original content
        for result in search_results:
            matcher2 = re.sub(r'[^a-zA-Z0-9]', '', result['content']).lower()
            if matcher1 not in matcher2:
                continue
            evidence.source = result['url']
            valid_evidences.append(evidence)
            break
    
    return valid_evidences


if __name__ == '__main__':
    async def main():
        results = await web_evaluate("Joemer R.", "To verify the applicant's claim of being a software engineer at Google and confirm the duration of employment.")
        print(results)
    import sys
    if sys.platform.startswith("win"):
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(main())

