# Chat API — POST /api/chat runs RAG over stored facts and returns grounded response
from fastapi import APIRouter
from app.schemas.models import ChatRequest, ChatResponse

router = APIRouter(prefix="/api")


@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    pass
