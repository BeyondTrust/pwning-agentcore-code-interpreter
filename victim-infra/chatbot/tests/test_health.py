"""Tests for health and info endpoints."""

import pytest


class TestHealthEndpoint:
    """Tests for /health endpoint."""

    def test_health_returns_ok(self, client):
        """Health endpoint returns 200 status."""
        response = client.get("/health")
        assert response.status_code == 200

    def test_health_response_format(self, client):
        """Health response contains expected fields."""
        response = client.get("/health")
        data = response.json()
        assert "status" in data
        assert "service" in data
        assert "code_interpreter" in data

    def test_health_status_healthy(self, client):
        """Health status should be 'healthy'."""
        response = client.get("/health")
        data = response.json()
        assert data["status"] == "healthy"

    def test_health_service_name(self, client):
        """Health response shows correct service name."""
        response = client.get("/health")
        data = response.json()
        assert data["service"] == "victim-chatbot"


class TestInfoEndpoint:
    """Tests for /info endpoint."""

    def test_info_returns_ok(self, client):
        """Info endpoint returns 200 status."""
        response = client.get("/info")
        assert response.status_code == 200

    def test_info_returns_expected_fields(self, client):
        """Info response contains all expected fields."""
        response = client.get("/info")
        data = response.json()
        assert "application" in data
        assert "version" in data
        assert "backend" in data
        assert "features" in data
        assert "endpoints" in data

    def test_info_features_is_list(self, client):
        """Info features should be a list."""
        response = client.get("/info")
        data = response.json()
        assert isinstance(data["features"], list)

    def test_info_endpoints_documented(self, client):
        """Info documents key endpoints."""
        response = client.get("/info")
        data = response.json()
        endpoints = data["endpoints"]
        assert "chat" in endpoints
        assert "analyze_csv" in endpoints


class TestRootEndpoint:
    """Tests for / root endpoint."""

    def test_root_returns_html(self, client):
        """Root endpoint returns HTML content."""
        response = client.get("/")
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]

    def test_root_contains_title(self, client):
        """Root HTML contains page title."""
        response = client.get("/")
        assert b"AI Data Analyst" in response.content or b"<title>" in response.content
