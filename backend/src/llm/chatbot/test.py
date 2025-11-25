import asyncio
from functools import wraps
from typing import Callable, Any, Dict, List
from langchain_core.tools import tool
from langchain.agents import create_agent
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.types import Command


# ============================================================================
# DECORATORS
# ============================================================================

def need_confirmation(func: Callable) -> Callable:
    """
    Decorator to mark a tool as requiring user confirmation before execution.
    """

    @wraps(func)
    def wrapper(*args, **kwargs):
        return func(*args, **kwargs)

    wrapper._needs_confirmation = True
    return wrapper


def frontend_execution(func: Callable) -> Callable:
    """
    Decorator to mark a tool as being executed on the frontend.
    Frontend tools require confirmation and are sent to the client for execution.
    """

    @wraps(func)
    def wrapper(*args, **kwargs):
        return func(*args, **kwargs)

    wrapper._is_frontend = True
    return wrapper



@tool
def say_hello() -> str:
    """Says hello"""
    print(f"Hello!")
    return f"Success"


@tool
@need_confirmation
def delete_report() -> str:
    """Deletes the generated report"""
    print(f"Dangerous tool executing: delete report")
    return f"Success"


@tool
@frontend_execution
@need_confirmation
def open_report_page() -> str:
    """opens report page to display report"""
    print(f"UI tool (would be sent to frontend) called")
    return f"Success"


class ToolExecutionHandler:
    """
    Handles tool execution based on decorator metadata.
    - Frontend tools: Send to client for execution
    - Confirmation tools: Require user approval
    - Regular tools: Execute immediately
    """

    def __init__(self, tools: List[Callable]):
        self.tools_map = {t.name: t for t in tools}
        self.tool_metadata = self._extract_metadata(tools)

    def _extract_metadata(self, tools: List[Callable]) -> Dict[str, Dict[str, bool]]:
        """Extract decorator metadata from tools."""
        metadata = {}
        for tool_func in tools:
            # Access the underlying function if it's wrapped by @tool
            actual_func = tool_func.func if hasattr(tool_func, 'func') else tool_func

            metadata[tool_func.name] = {
                'needs_confirmation': getattr(actual_func, '_needs_confirmation', False),
                'is_frontend': getattr(actual_func, '_is_frontend', False)
            }
        return metadata

    def get_tool_info(self, tool_name: str) -> Dict[str, Any]:
        """Get metadata for a specific tool."""
        return self.tool_metadata.get(tool_name, {
            'needs_confirmation': False,
            'is_frontend': False
        })

    def requires_confirmation(self, tool_name: str) -> bool:
        """Check if tool needs confirmation."""
        return self.tool_metadata.get(tool_name, {}).get('needs_confirmation', False)

    def is_frontend_tool(self, tool_name: str) -> bool:
        """Check if tool should be executed on frontend."""
        return self.tool_metadata.get(tool_name, {}).get('is_frontend', False)


# ============================================================================
# AGENT WITH TOOL HANDLER
# ============================================================================

async def main():
    # Setup tools
    tools = [say_hello, delete_report, open_report_page]
    handler = ToolExecutionHandler(tools)

    print("=== Tool Metadata ===")
    for tool_name, metadata in handler.tool_metadata.items():
        print(f"{tool_name}: {metadata}")
    print()

    # Create agent with interrupt before tools
    from src.llm.rotating_llm import rotating_llm
    model = await rotating_llm.get_runnable()

    agent = create_agent(
        model=model,
        tools=tools,
        checkpointer=InMemorySaver(),
        system_prompt="You are a helpful assistant. Use tools when needed.",
        interrupt_before=["tools"]  # Pause before tool execution
    )

    thread_id = "test-thread"
    config = {"configurable": {"thread_id": thread_id}}

    # Run agent
    print("\n=== Starting Agent ===")
    while True:
        result = await agent.ainvoke(
            {"messages": [{"role": "user", "content": input(": ")}]},
            config=config,
        )
        # Check for interruption
        state = await agent.aget_state(config)

        while state.next:  # While there are pending nodes
            print(f"\n🔄 Agent interrupted. Next nodes: {state.next}")

            # Get tool calls from the last message
            last_message = state.values.get("messages", [])[-1]

            if hasattr(last_message, "tool_calls") and last_message.tool_calls:
                for tool_call in last_message.tool_calls:
                    tool_name = tool_call["name"]
                    tool_args = tool_call["args"]

                    if handler.is_frontend_tool(tool_name) and handler.requires_confirmation(tool_name):
                        input("is frontend and need confirm, press enter")
                    elif handler.is_frontend_tool(tool_name):
                        input("frontend execution....")
                    elif handler.requires_confirmation(tool_name):
                        input("need confirmation, press enter to continue")
                    else:
                        print("safe")

            # Resume execution
            print("\n▶️ Resuming agent...")
            result = await agent.ainvoke(None, config=config)
            state = await agent.aget_state(config)

        print(result["messages"][-1].content)


if __name__ == "__main__":
    import sys

    if sys.platform.startswith("win"):
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

    # Run full agent
    asyncio.run(main())