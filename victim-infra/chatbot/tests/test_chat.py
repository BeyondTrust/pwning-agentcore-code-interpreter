"""Tests for chat endpoint."""

import pytest


class TestChatEndpoint:
    """Tests for /chat/ endpoint."""

    def test_chat_success(self, client, mock_agentcore_service):
        """Successful chat returns response."""
        response = client.post(
            "/chat/",
            json={"message": "Hello"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "response" in data
        assert "session_id" in data

    def test_chat_with_session_id(self, client, mock_agentcore_service):
        """Chat with existing session ID."""
        response = client.post(
            "/chat/",
            json={"message": "Hello", "session_id": "sess_existing"}
        )
        assert response.status_code == 200

    def test_chat_generates_session_id(self, client, mock_agentcore_service):
        """Chat without session ID generates one."""
        response = client.post(
            "/chat/",
            json={"message": "Hello"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["session_id"] is not None
        assert len(data["session_id"]) > 0

    def test_chat_empty_message(self, client, mock_agentcore_service):
        """Empty message is processed."""
        response = client.post(
            "/chat/",
            json={"message": ""}
        )
        # Empty message should still be accepted
        assert response.status_code == 200

    def test_chat_long_message(self, client, mock_agentcore_service):
        """Long message is processed."""
        long_message = "Hello " * 1000
        response = client.post(
            "/chat/",
            json={"message": long_message}
        )
        assert response.status_code == 200

    def test_chat_missing_message(self, client):
        """Missing message returns validation error."""
        response = client.post("/chat/", json={})
        assert response.status_code == 422

    def test_chat_invalid_json(self, client):
        """Invalid JSON returns error."""
        response = client.post(
            "/chat/",
            content="not json",
            headers={"content-type": "application/json"}
        )
        assert response.status_code == 422

    def test_chat_response_format(self, client, mock_agentcore_service):
        """Chat response has correct format."""
        response = client.post(
            "/chat/",
            json={"message": "Hello"}
        )
        data = response.json()
        assert isinstance(data["response"], str)
        assert isinstance(data["session_id"], str)


class TestSessionEndpoint:
    """Tests for /chat/sessions/{session_id} endpoint."""

    def test_session_info_returns_ok(self, client):
        """Session info endpoint returns 200."""
        response = client.get("/chat/sessions/sess_test123")
        assert response.status_code == 200

    def test_session_info_contains_id(self, client):
        """Session info contains the requested session ID."""
        response = client.get("/chat/sessions/sess_abc")
        data = response.json()
        assert data["session_id"] == "sess_abc"

    def test_session_info_contains_status(self, client):
        """Session info contains status."""
        response = client.get("/chat/sessions/sess_test")
        data = response.json()
        assert "status" in data
