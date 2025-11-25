from fastapi import APIRouter, HTTPException, status
from src.models.chatbot import ChatResponse, SendMessage, AttachContent, ConfirmAction, ClearMemory, ContinueWithToolResult
from src.llm.chatbot import Chatbot

router = APIRouter()


def get_chatbot(current_user: int, thread_id: str) -> Chatbot:
    return Chatbot(
        thread_id=thread_id,
        current_user=current_user
    )


@router.post("/message", response_model=ChatResponse, status_code=status.HTTP_200_OK)
async def send_message(
    payload: SendMessage,
):
    """
    Send a user message to the chatbot and return the model's reply.
    """
    bot = get_chatbot(payload.current_user, payload.thread_id)
    await bot.initialize()

    try:
        response = await bot.send_message(payload.text)
        return response
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/confirm", response_model=ChatResponse, status_code=status.HTTP_200_OK)
async def confirm_action(
    payload: ConfirmAction,
):
    """
    Confirm or reject a pending action from the chatbot.
    """
    bot = get_chatbot(payload.current_user, payload.thread_id)
    await bot.initialize()

    try:
        response = await bot.confirm_action(payload.approved)
        return response
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/attach", status_code=status.HTTP_200_OK)
async def attach_content(
    payload: AttachContent,
):
    """
    Attach content (text, base64 image, or base64 file) to be included in the next message.
    For files, text will be automatically extracted from supported formats.
    """
    bot = get_chatbot(payload.current_user, payload.thread_id)

    try:
        await bot.attach_content(
            content=payload.content,
            content_type=payload.content_type,
            mime_type=payload.mime_type,
        )
        return {
            "success": True,
            "message": f"Cached {payload.content_type} attachment for next message"
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/clear", response_model=bool, status_code=status.HTTP_200_OK)
async def clear_memory(
    payload: ClearMemory,
):
    """
    Clear all chat history and memory for the specified thread.
    """
    bot = get_chatbot(payload.current_user, payload.thread_id)

    try:
        await bot.clear_memory()
        return True
    except Exception:
        return False


@router.post("/tool_result", response_model=ChatResponse, status_code=status.HTTP_200_OK)
async def continue_with_tool_result(
    payload: ContinueWithToolResult,
):
    """
    Continue conversation after frontend executes a tool and provides the result.
    """
    bot = get_chatbot(payload.current_user, payload.thread_id)
    await bot.initialize()

    try:
        response = await bot.continue_with_tool_result(payload.text)
        return response
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
