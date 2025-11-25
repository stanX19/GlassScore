from fastapi import APIRouter

router = APIRouter()

from .chatbot import router as chatbot_router
from .evaluate import router as evaluate_router
from .session import router as session_router

router.include_router(chatbot_router, prefix="/chat", tags=["chatbot"])
router.include_router(evaluate_router, prefix="/evaluate", tags=["evaluate"])
router.include_router(session_router, prefix="/session", tags=["session"])