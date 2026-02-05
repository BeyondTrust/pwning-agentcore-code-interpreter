"""Tests for Pydantic schema models."""

import pytest
from pydantic import ValidationError
from app.models.schemas import (
    ChatMessage,
    ChatRequest,
    ChatResponse,
    AnalyzeRequest,
    AnalyzeResponse,
    HealthResponse
)


class TestChatMessage:
    """Tests for ChatMessage model."""

    def test_chat_message_valid(self):
        """Valid chat message creates successfully."""
        msg = ChatMessage(role="user", content="Hello")
        assert msg.role == "user"
        assert msg.content == "Hello"

    def test_chat_message_assistant_role(self):
        """Assistant role is valid."""
        msg = ChatMessage(role="assistant", content="Hi there!")
        assert msg.role == "assistant"

    def test_chat_message_empty_content_allowed(self):
        """Empty content is allowed (Pydantic doesn't enforce min_length by default)."""
        msg = ChatMessage(role="user", content="")
        assert msg.content == ""

    def test_chat_message_missing_role(self):
        """Missing role raises validation error."""
        with pytest.raises(ValidationError):
            ChatMessage(content="Hello")

    def test_chat_message_missing_content(self):
        """Missing content raises validation error."""
        with pytest.raises(ValidationError):
            ChatMessage(role="user")


class TestChatRequest:
    """Tests for ChatRequest model."""

    def test_chat_request_valid(self):
        """Valid chat request creates successfully."""
        req = ChatRequest(message="Hello")
        assert req.message == "Hello"
        assert req.session_id is None

    def test_chat_request_with_session(self):
        """Chat request with session ID."""
        req = ChatRequest(message="Hello", session_id="sess_123")
        assert req.session_id == "sess_123"

    def test_chat_request_with_history(self):
        """Chat request with conversation history."""
        history = [
            ChatMessage(role="user", content="Hi"),
            ChatMessage(role="assistant", content="Hello!")
        ]
        req = ChatRequest(message="How are you?", history=history)
        assert len(req.history) == 2

    def test_chat_request_missing_message(self):
        """Missing message raises validation error."""
        with pytest.raises(ValidationError):
            ChatRequest()


class TestChatResponse:
    """Tests for ChatResponse model."""

    def test_chat_response_valid(self):
        """Valid chat response creates successfully."""
        resp = ChatResponse(response="Hi there!", session_id="sess_123")
        assert resp.response == "Hi there!"
        assert resp.session_id == "sess_123"

    def test_chat_response_missing_fields(self):
        """Missing required fields raises error."""
        with pytest.raises(ValidationError):
            ChatResponse(response="Hi")


class TestAnalyzeRequest:
    """Tests for AnalyzeRequest model."""

    def test_analyze_request_valid(self):
        """Valid analyze request creates successfully."""
        req = AnalyzeRequest(data="a,b\n1,2", message="Analyze this")
        assert req.data == "a,b\n1,2"
        assert req.message == "Analyze this"

    def test_analyze_request_with_session(self):
        """Analyze request with session ID."""
        req = AnalyzeRequest(
            data="a,b\n1,2",
            message="Analyze",
            session_id="sess_456"
        )
        assert req.session_id == "sess_456"


class TestAnalyzeResponse:
    """Tests for AnalyzeResponse model."""

    def test_analyze_response_valid(self):
        """Valid analyze response creates successfully."""
        resp = AnalyzeResponse(
            response="Analysis complete",
            session_id="sess_123",
            analysis_complete=True
        )
        assert resp.response == "Analysis complete"
        assert resp.analysis_complete is True

    def test_analyze_response_with_rows(self):
        """Analyze response with row count."""
        resp = AnalyzeResponse(
            response="Done",
            session_id="sess_123",
            analysis_complete=True,
            rows_processed=100
        )
        assert resp.rows_processed == 100

    def test_analyze_response_with_error(self):
        """Analyze response with error message."""
        resp = AnalyzeResponse(
            response="Failed",
            session_id="sess_123",
            analysis_complete=False,
            error="Something went wrong"
        )
        assert resp.error == "Something went wrong"


class TestHealthResponse:
    """Tests for HealthResponse model."""

    def test_health_response_valid(self):
        """Valid health response creates successfully."""
        resp = HealthResponse(
            status="healthy",
            service="chatbot",
            code_interpreter="configured"
        )
        assert resp.status == "healthy"
        assert resp.service == "chatbot"
