from fastapi import APIRouter

router = APIRouter()

from .chatbot import router as chatbot_router

router.include_router(chatbot_router, prefix="/chat", tags=["chatbot"])