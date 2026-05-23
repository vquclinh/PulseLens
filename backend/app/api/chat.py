# Chat API — POST /api/chat runs RAG over stored facts and returns grounded response
from fastapi import APIRouter, HTTPException
from app.schemas.models import ChatRequest, ChatResponse
from app.db.database import get_db
from app.utils.llm_client import LLMClient

router = APIRouter(prefix="/api")


@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    pass
