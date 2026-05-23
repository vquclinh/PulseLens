# Tests for chat RAG — citation validation, fact_id grounding, response structure
import pytest
from app.api.chat import chat
from app.schemas.models import ChatRequest, ChatResponse
