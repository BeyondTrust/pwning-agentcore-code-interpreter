"""
Chat Router - General conversation endpoint

This router handles basic chat interactions with the AI assistant.
"""

import logging
import uuid
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.services.agentcore import AgentCoreService

router = APIRouter(prefix="/chat", tags=["chat"])
logger = logging.getLogger(__name__)

# Initialize service
agentcore_service = AgentCoreService()


class ChatRequest(BaseModel):
    """Request model for chat endpoint."""
    message: str
    session_id: Optional[str] = None


class ChatResponse(BaseModel):
    """Response model for chat endpoint."""
    response: str
    session_id: str


@router.post("/", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    General chat endpoint for conversation.

    This endpoint handles basic chat messages and returns AI responses.
    For CSV analysis, use the /analyze/csv endpoint instead.
    """
    try:
        logger.info(f"Chat request received: {request.message[:100]}...")

        result = agentcore_service.chat(
            message=request.message,
            session_id=request.session_id
        )

        return ChatResponse(
            response=result["response"],
            session_id=result["session_id"]
        )

    except Exception as e:
        logger.error(f"Chat error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/sessions/{session_id}")
async def get_session(session_id: str):
    """Get information about a chat session."""
    return {
        "session_id": session_id,
        "status": "active",
        "message": "Session tracking not fully implemented in demo"
    }
