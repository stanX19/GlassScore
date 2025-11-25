# src/agent_main.py
import asyncio
from datetime import datetime
from typing import Any, Dict

from langchain.agents import create_agent
from langchain.agents.middleware import SummarizationMiddleware
from langchain_core.messages import ToolMessage, BaseMessage
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from langgraph.graph.state import CompiledStateGraph
from langgraph.types import StateSnapshot

from src.llm.chatbot.memory import get_chat_postgres_saver_async
from src.llm.rotating_llm import rotating_llm, MessagesType
from src.llm.chatbot import tools
from src.llm.chatbot.load_utils import load_prompt
from src.llm.chatbot.tools import ToolContextHandler, ToolReg
from src.services.file_parser import prepare_image_message, prepare_file_message
from src.models.chatbot import ChatResponse, Action

# Global attachment cache: {thread_id: [attachment_dicts]}
_attachment_cache: dict[str, list[dict[str, Any]]] = {}


class Chatbot:
    """
    Async chatbot agent with interruptable tool handling and persistent memory.
    """

    def __init__(self, thread_id: str = "chat-1", current_user: int | None = None):
        self.thread_id = thread_id
        self.prev_result: dict[str, Any] = {}
        self.agent_graph: CompiledStateGraph | None = None
        self.initialized: bool = False
        self.current_user: int | None = current_user
        self.handler: ToolContextHandler | None = None

        if self.current_user is None:
            print("⚠️ current_user is None; disabling user-related tools")

    async def initialize(self):
        """Initialize agent and supporting components."""
        if self.initialized:
            return

        # Load rotating model
        model = await rotating_llm.get_runnable()

        # Persistent memory
        checkpointer: AsyncPostgresSaver = await get_chat_postgres_saver_async()

        # Middleware: summarize older messages
        summarization = SummarizationMiddleware(model=model, max_tokens_before_summary=3000, messages_to_keep=5)

        # Setup tools and handler
        available_tools = [
            tools.calc, 
        ]
        if self.current_user:
            available_tools.extend([
                tools.perform_adr,
                tools.create_add_medicine_tool(self.current_user),
            ])
        # Filter out None values (when current_user is None)
        available_tools = [t for t in available_tools if t is not None]
        self.handler = ToolContextHandler(available_tools)

        current_date = datetime.now().strftime("%Y-%m-%d (%A)")
        base_prompt = load_prompt("chatbot_system.txt")
        system_prompt_with_date = f"{base_prompt}\n\nCurrent date: {current_date}"

        # Create interruptable agent
        self.agent_graph = create_agent(
            model=model,
            tools=available_tools,
            checkpointer=checkpointer,
            system_prompt=system_prompt_with_date,
            middleware=[summarization],
            interrupt_before=["tools"],   # ✅ Pause before tools
            debug=False,
        )

        self.initialized = True
        print(f"✅ Chatbot initialized for thread_id={self.thread_id}")

    async def _create_tool_message(self, text: str) -> ToolMessage:
        """
        Adds a tool message in place if applicable
        :return: the list passed in
        """
        # User rejected - inject a tool response indicating the tool was declined
        config = {"configurable": {"thread_id": self.thread_id}}

        state: StateSnapshot = await self.agent_graph.aget_state(config)
        last_message = state.values.get("messages", [])[-1]

        if hasattr(last_message, "tool_calls") and last_message.tool_calls:
            tool_call = last_message.tool_calls[0]
            return ToolMessage(
                content=text,
                tool_call_id=tool_call["id"]
            )
        else:
            raise AssertionError("No previous tool call to insert message")

    def _prepend_cached_attachments(self, _messages: list | None) -> list:
        """Prepend cached attachments to messages and clear cache."""
        if self.thread_id in _attachment_cache and _attachment_cache[self.thread_id]:
            attachments = _attachment_cache[self.thread_id]
            if _messages:
                # Insert attachments before user messages
                for attachment in attachments:
                    _messages.insert(0, attachment)
            else:
                _messages = attachments.copy()
            # Clear cache after using
            _attachment_cache[self.thread_id] = []
        return _messages

    async def send_message(self, _messages: MessagesType) -> ChatResponse:
        """Send user text to the agent and handle interruptions."""
        if not self.initialized:
            await self.initialize()

        config = {"configurable": {"thread_id": self.thread_id}}

        _messages = rotating_llm.format_messages(_messages)
        _messages = self._prepend_cached_attachments(_messages)
        
        passed_in = {"messages": _messages} if _messages else None
        # Invoke model
        result = await self.agent_graph.ainvoke(
            passed_in,
            config=config,
            verbose=True
        )
        self.prev_result = result
        state = await self.agent_graph.aget_state(config)

        # Handle interruptions before tool calls
        while state.next:
            print(f"\n🔄 Agent interrupted. Next: {state.next}")

            last_message = state.values.get("messages", [])[-1]

            # Handle tool calls (if any)
            if hasattr(last_message, "tool_calls") and last_message.tool_calls:
                # LangGraph only allows one tool call per iteration
                call = last_message.tool_calls[0]
                name, args = call["name"], call["args"]

                needs_confirm = self.handler.has_decorator(name, ToolReg.need_confirmation)
                needs_personal_data_confirm = self.handler.has_decorator(name, ToolReg.need_personal_data_confirmation)
                frontend_exec = self.handler.has_decorator(name, ToolReg.frontend_execution)

                if needs_confirm or needs_personal_data_confirm or frontend_exec:
                    # Store pending action and return control to frontend
                    pending_action = Action(
                        name=name,
                        args=args,
                        needs_confirmation=needs_confirm or needs_personal_data_confirm,  # TODO: Remove this
                        needs_personal_data_confirmation=needs_personal_data_confirm,
                        frontend_execution=frontend_exec
                    )

                    return ChatResponse(
                        thread_id=self.thread_id,
                        text="",
                        status="pending_confirmation",
                        action=pending_action,
                        meta={"awaiting_confirmation": True}
                    )
                else:
                    # Safe tool - execute immediately
                    print(f"⚙️ Executing {name} safely...")

            # Resume
            print("▶️ Resuming agent...")
            result = await self.agent_graph.ainvoke(None, config=config)
            self.prev_result = result
            state = await self.agent_graph.aget_state(config)

        message = Chatbot.extract_message(result)
        return ChatResponse(
            thread_id=self.thread_id,
            text=message,
            status="Success",
            meta={"input": _messages, "result": self.prev_result}
        )

    async def continue_with_tool_result(self, tool_result: str):
        try:
            return await self.send_message(await self._create_tool_message(tool_result))
        except AssertionError:
            return await self.send_message(tool_result)

    async def send_message_auto_decline(self, _messages: MessagesType) -> ChatResponse:
        if not self.initialized:
            await self.initialize()

        if not await self.has_pending_action():
            return await self.send_message(_messages)
        decline_message = await self._create_tool_message("User didn't choose confirm")
        messages = rotating_llm.format_messages(_messages)
        messages.insert(0, decline_message)
        return await self.send_message(messages)


    async def confirm_action(self, approved: bool) -> ChatResponse:
        """Resume agent execution after user confirms/rejects pending action."""
        if not self.initialized:
            await self.initialize()

        if not await self.has_pending_action():
            raise ValueError("No pending action to confirm")

        if not approved:
            decline_message = await self._create_tool_message("User declined this action.")
            return await self.send_message(decline_message)
        else:
            return await self.send_message(None)

    async def has_pending_action(self):
        try:
            config = {"configurable": {"thread_id": self.thread_id}}

            state = await self.agent_graph.aget_state(config)

            last_message = state.values.get("messages", [])[-1]
            return hasattr(last_message, "tool_calls") and last_message.tool_calls
        except (IndexError, KeyError, ValueError, AttributeError):
            return False


    @staticmethod
    def extract_message(result: Dict[str, Any]) -> str:
        """Extract text content from a LangChain result."""
        try:
            messages = result.get("messages", [])
            if not messages:
                return "⚠️ No response."
            content = messages[-1].content
            if isinstance(content, list):
                return content[0].get("text", str(content))
            return str(content)
        except Exception as e:
            return f"⚠️ Error extracting message: {e}"

    async def attach_content(self, content: Any, content_type: str = "text", mime_type: str | None = None):
        """Attach content (text, base64 image, or base64 file) to be prepended in next message."""
        if self.thread_id not in _attachment_cache:
            _attachment_cache[self.thread_id] = []
        
        if content_type == "image":
            # Use file_parser service to prepare image message
            mime = mime_type or "image/jpeg"
            try:
                message_entry = prepare_image_message(content, mime)
            except ValueError as e:
                raise ValueError(str(e))
        elif content_type == "file":
            # Use file_parser service to prepare file message
            if not mime_type:
                raise ValueError("mime_type is required for file attachments")
            
            try:
                message_entry = prepare_file_message(content, mime_type)
            except Exception as e:
                raise ValueError(f"Failed to extract text from file: {str(e)}")
        else:
            # Store text content
            message_entry = {
                "role": "user",
                "content": content
            }
        
        _attachment_cache[self.thread_id].append(message_entry)
        print(f"📎 Cached {content_type} attachment for {self.thread_id}")

    async def clear_memory(self):
        """Clear all chat history and checkpoints for the current thread."""
        if not self.initialized:
            await self.initialize()

        checkpointer = self.agent_graph.checkpointer
        if not checkpointer:
            print("⚠️ No checkpointer available.")
            return

        await checkpointer.adelete_thread(self.thread_id)
        
        # Also clear attachment cache
        if self.thread_id in _attachment_cache:
            _attachment_cache[self.thread_id] = []
        
        print(f"🗑️ Cleared memory for thread_id={self.thread_id}")


# ---------------------- Example CLI runner ----------------------
if __name__ == "__main__":
    async def main():
        bot = Chatbot(thread_id="chat-2", current_user=101)  # Shan Chien, marcus is 79
        await bot.initialize()

        print("🤖 Chatbot ready. Type 'exit' to quit, 'clear' to clear memory.\n")
        while True:
            user_input = input("> ").strip()
            if user_input.lower() in ("exit", "quit"):
                break
            if user_input.lower() == "clear":
                await bot.clear_memory()
                continue
            response: ChatResponse = await bot.send_message_auto_decline(user_input)
            while response.action:
                if response.action.needs_confirmation:
                    print(response.action.name)
                    print(response.action.args)
                    response: ChatResponse = await bot.confirm_action(input("confirm? [y/n]") in ["y", "Y", "yes"])
            print(*bot.prev_result["messages"], sep='\n')
            print(response.text)

    import sys
    if sys.platform.startswith("win"):
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

    asyncio.run(main())
