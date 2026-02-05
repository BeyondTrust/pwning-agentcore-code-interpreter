"""Tests for AgentCoreService."""

import pytest
from unittest.mock import MagicMock, patch


class TestAgentCoreServiceInit:
    """Tests for AgentCoreService initialization."""

    def test_service_initialization(self):
        """Service initializes with settings."""
        with patch("app.services.agentcore.boto3") as mock_boto3, \
             patch("app.services.agentcore.get_settings") as mock_settings:
            mock_settings.return_value = MagicMock(
                aws_region="us-east-1",
                code_interpreter_id="test-id",
                code_interpreter_arn="arn:aws:test"
            )
            from app.services.agentcore import AgentCoreService
            service = AgentCoreService()
            assert service.region == "us-east-1"
            assert service.code_interpreter_id == "test-id"

    def test_service_no_code_interpreter(self):
        """Service handles missing code interpreter config."""
        with patch("app.services.agentcore.boto3") as mock_boto3, \
             patch("app.services.agentcore.get_settings") as mock_settings:
            mock_settings.return_value = MagicMock(
                aws_region="us-east-1",
                code_interpreter_id=None,
                code_interpreter_arn=None
            )
            from app.services.agentcore import AgentCoreService
            service = AgentCoreService()
            assert service.code_interpreter_id is None


class TestAgentCoreServiceChat:
    """Tests for AgentCoreService.chat method."""

    def test_chat_returns_response(self):
        """Chat method returns expected structure."""
        with patch("app.services.agentcore.boto3"), \
             patch("app.services.agentcore.get_settings") as mock_settings:
            mock_settings.return_value = MagicMock(
                aws_region="us-east-1",
                code_interpreter_id=None,
                code_interpreter_arn=None
            )
            from app.services.agentcore import AgentCoreService
            service = AgentCoreService()
            result = service.chat("Hello")
            assert "response" in result
            assert "session_id" in result

    def test_chat_generates_session_id(self):
        """Chat generates session ID if not provided."""
        with patch("app.services.agentcore.boto3"), \
             patch("app.services.agentcore.get_settings") as mock_settings:
            mock_settings.return_value = MagicMock(
                aws_region="us-east-1",
                code_interpreter_id=None,
                code_interpreter_arn=None
            )
            from app.services.agentcore import AgentCoreService
            service = AgentCoreService()
            result = service.chat("Hello")
            assert result["session_id"].startswith("sess_")

    def test_chat_uses_provided_session_id(self):
        """Chat uses provided session ID."""
        with patch("app.services.agentcore.boto3"), \
             patch("app.services.agentcore.get_settings") as mock_settings:
            mock_settings.return_value = MagicMock(
                aws_region="us-east-1",
                code_interpreter_id=None,
                code_interpreter_arn=None
            )
            from app.services.agentcore import AgentCoreService
            service = AgentCoreService()
            result = service.chat("Hello", session_id="sess_custom")
            assert result["session_id"] == "sess_custom"


class TestAgentCoreServiceAnalyze:
    """Tests for AgentCoreService.analyze_csv method."""

    def test_mock_analysis_format(self):
        """Mock analysis returns expected format."""
        with patch("app.services.agentcore.boto3"), \
             patch("app.services.agentcore.get_settings") as mock_settings:
            mock_settings.return_value = MagicMock(
                aws_region="us-east-1",
                code_interpreter_id=None,
                code_interpreter_arn=None
            )
            from app.services.agentcore import AgentCoreService
            service = AgentCoreService()
            result = service._mock_analysis(
                csv_content="a,b\n1,2",
                user_message="Analyze",
                session_id="sess_test"
            )
            assert "response" in result
            assert "session_id" in result

    def test_mock_analysis_includes_csv_info(self):
        """Mock analysis includes CSV information."""
        with patch("app.services.agentcore.boto3"), \
             patch("app.services.agentcore.get_settings") as mock_settings:
            mock_settings.return_value = MagicMock(
                aws_region="us-east-1",
                code_interpreter_id=None,
                code_interpreter_arn=None
            )
            from app.services.agentcore import AgentCoreService
            service = AgentCoreService()
            result = service._mock_analysis(
                csv_content="name,value\nAlice,100\nBob,200",
                user_message="Analyze this",
                session_id="sess_test"
            )
            # Mock response should mention columns
            assert "name" in result["response"] or "Columns" in result["response"]


class TestAgentCoreServiceSession:
    """Tests for session management."""

    def test_active_sessions_tracking(self):
        """Service tracks active sessions."""
        with patch("app.services.agentcore.boto3"), \
             patch("app.services.agentcore.get_settings") as mock_settings:
            mock_settings.return_value = MagicMock(
                aws_region="us-east-1",
                code_interpreter_id=None,
                code_interpreter_arn=None
            )
            from app.services.agentcore import AgentCoreService
            service = AgentCoreService()
            assert hasattr(service, "active_sessions")
            assert isinstance(service.active_sessions, dict)

    def test_end_session_unknown(self):
        """End session returns False for unknown session."""
        with patch("app.services.agentcore.boto3"), \
             patch("app.services.agentcore.get_settings") as mock_settings:
            mock_settings.return_value = MagicMock(
                aws_region="us-east-1",
                code_interpreter_id=None,
                code_interpreter_arn=None
            )
            from app.services.agentcore import AgentCoreService
            service = AgentCoreService()
            result = service.end_session("nonexistent_session")
            assert result is False
