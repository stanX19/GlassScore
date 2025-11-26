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


async def _generate_queries(session_id: int) -> list[dict]:
    session = await session_service.get_session(session_id)
    if not session or not session.text_content_list:
        return []

    # Combine all text content for context
    context_text = session.user_profile.model_dump_json(indent=2) + "\n\n"
    context_text += "\n\n".join([
        f"Source: {c.source}\nContent: {c.text}" for c in session.text_content_list
    ])

    prompt = f"""
    You are a background check specialist. Your goal is to verify the claims made by a loan applicant and check for any risk factors (gambling, fraud, negative news).

    Based on the following applicant information, generate 3 to 5 targeted web search queries.
    Focus on:
    1. Verifying their employment or business claims.
    2. Checking for negative news, lawsuits, or financial scandals.
    3. Identifying social media presence that might contradict their claims.

    IMPORTANT:
    - Do NOT use search operators like "site:", "OR", "AND", or quotes for exact match.
    - Use natural language queries optimized for semantic search.

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
            return queries
        else:
            print(f"Failed to generate web queries: {response.get('text')}")
            return []
            
    except Exception as e:
        print(f"Error generating web tasks: {e}")
        return []


async def _execute_web_task(query_task: Task, index: int) -> list[EvaluationEvidence]:
    try:
        queries = await query_task
        if index < len(queries):
            item = queries[index]
            query = item.get("query")
            objective = item.get("objective")
            if query:
                return await web_evaluate(query, objective)
    except Exception as e:
        print(f"Error in web task {index}: {e}")
    return []


async def generate_web_tasks(session_id: int) -> list[Task]:
    query_task = asyncio.create_task(_generate_queries(session_id))
    
    tasks = []
    for i in range(5):
        tasks.append(asyncio.create_task(_execute_web_task(query_task, i)))
    return tasks


async def web_evaluate(query: str, objective: str) -> list[EvaluationEvidence]:
    print(f"Executing web search: {query}\n    Objective: {objective})")
    
    search_results = []

    if not os.environ.get("TAVILY_API_KEY"):
        await asyncio.sleep(2)  # Simulate delay
        return [EvaluationEvidence(
            score=0,
            description=f"TAVILY_API_KEY not found. Web search unavailable for '{query}'",
            citation="",
            source="web_search"
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

    # Combine all results into one text for the LLM
    combined_text = ""
    for i, result in enumerate(search_results):
        combined_text += f"--- Result {i+1} ---\n"
        combined_text += f"Title: {result.get('title', 'Unknown')}\n"
        combined_text += f"Content: {result['content']}\n\n"

    content = TextContent(
        text=combined_text,
        key=f"web_search_{query[:10]}",
        source="web_search_aggregated"
    )
    
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

