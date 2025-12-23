"""
Pydantic models for request/response schemas.
"""

from typing import Optional, List
from pydantic import BaseModel, Field


class ChatMessage(BaseModel):
    """A single chat message."""
    role: str = Field(..., description="Message role: 'user' or 'assistant'")
    content: str = Field(..., description="Message content")


class ChatRequest(BaseModel):
    """Request model for chat endpoint."""
    message: str = Field(..., description="User's message")
    session_id: Optional[str] = Field(None, description="Session ID for continuity")
    history: Optional[List[ChatMessage]] = Field(None, description="Conversation history")


class ChatResponse(BaseModel):
    """Response model for chat endpoint."""
    response: str = Field(..., description="Assistant's response")
    session_id: str = Field(..., description="Session ID")


class AnalyzeRequest(BaseModel):
    """Request model for analysis endpoint (JSON version)."""
    data: str = Field(..., description="Data to analyze (CSV format)")
    message: str = Field(..., description="Analysis request/question")
    session_id: Optional[str] = Field(None, description="Session ID")


class AnalyzeResponse(BaseModel):
    """Response model for analysis endpoint."""
    response: str = Field(..., description="Analysis results")
    session_id: str = Field(..., description="Session ID")
    analysis_complete: bool = Field(..., description="Whether analysis completed")
    rows_processed: Optional[int] = Field(None, description="Number of rows processed")
    error: Optional[str] = Field(None, description="Error message if failed")


class HealthResponse(BaseModel):
    """Response model for health check."""
    status: str
    service: str
    code_interpreter: str
