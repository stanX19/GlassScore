from fastapi import APIRouter, HTTPException, status
from src.models.session import AttachContentRequest, UpdateProfileRequest
from src.services.session import session_service

router = APIRouter()

@router.post("/create")
async def create_session():
    session = await session_service.create_session()
    return session

@router.get("/get")
async def get_session(session_id: int):
    session = await session_service.get_session(session_id)
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")
    return session

@router.post("/attach")
async def add_text_content(content: AttachContentRequest):
    session = await session_service.add_text_content(content.session_id, content.text_content)
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")
    return session

@router.post("/update")
async def update_session(request: UpdateProfileRequest):
    session = await session_service.get_session(request.session_id)
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")
    session.user_profile = request.user_profile
    session.text_content_dict.clear()
    session.evidence_list = []
    return session

@router.post("/reset")
async def reset_session(session_id: int):
    session = await session_service.get_session(session_id)
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")
    session.text_content_dict.clear()
    session.evidence_list = []
    return session