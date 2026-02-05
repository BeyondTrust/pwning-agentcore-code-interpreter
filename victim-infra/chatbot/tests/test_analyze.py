"""Tests for CSV analysis endpoint."""

import pytest
from io import BytesIO


class TestCSVUpload:
    """Tests for /analyze/csv endpoint."""

    def test_csv_upload_success(self, client, sample_csv_bytes, mock_agentcore_service):
        """Successful CSV upload returns analysis."""
        response = client.post(
            "/analyze/csv",
            files={"file": ("test.csv", BytesIO(sample_csv_bytes), "text/csv")},
            data={"message": "Analyze this data"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "response" in data
        assert "session_id" in data
        assert data["analysis_complete"] is True

    def test_csv_upload_wrong_file_type(self, client):
        """Non-CSV file is rejected."""
        response = client.post(
            "/analyze/csv",
            files={"file": ("test.txt", BytesIO(b"hello world"), "text/plain")},
            data={"message": "Analyze this"}
        )
        assert response.status_code == 400
        assert "CSV" in response.json()["detail"]

    def test_csv_upload_no_file(self, client):
        """Missing file returns error."""
        response = client.post(
            "/analyze/csv",
            data={"message": "Analyze this"}
        )
        assert response.status_code == 422

    def test_csv_upload_empty_file(self, client, mock_agentcore_service):
        """Empty CSV file is processed."""
        response = client.post(
            "/analyze/csv",
            files={"file": ("empty.csv", BytesIO(b""), "text/csv")},
            data={"message": "Analyze this"}
        )
        # Empty file should still be accepted
        assert response.status_code == 200

    def test_csv_upload_too_large(self, client, large_csv_content):
        """File exceeding 50MB limit is rejected."""
        large_bytes = large_csv_content.encode("utf-8")
        response = client.post(
            "/analyze/csv",
            files={"file": ("large.csv", BytesIO(large_bytes), "text/csv")},
            data={"message": "Analyze this"}
        )
        assert response.status_code == 413
        assert "too large" in response.json()["detail"].lower()

    def test_csv_upload_utf8_encoding(self, client, mock_agentcore_service):
        """UTF-8 encoded CSV is processed correctly."""
        utf8_csv = "name,city\nAlice,日本\nBob,München".encode("utf-8")
        response = client.post(
            "/analyze/csv",
            files={"file": ("utf8.csv", BytesIO(utf8_csv), "text/csv")},
            data={"message": "Analyze cities"}
        )
        assert response.status_code == 200

    def test_csv_upload_latin1_fallback(self, client, mock_agentcore_service):
        """Latin-1 encoded CSV falls back correctly."""
        latin1_csv = "name,city\nAlice,München".encode("latin-1")
        response = client.post(
            "/analyze/csv",
            files={"file": ("latin1.csv", BytesIO(latin1_csv), "text/csv")},
            data={"message": "Analyze cities"}
        )
        assert response.status_code == 200

    def test_csv_row_counting(self, client, sample_csv_bytes, mock_agentcore_service):
        """Response includes correct row count."""
        response = client.post(
            "/analyze/csv",
            files={"file": ("test.csv", BytesIO(sample_csv_bytes), "text/csv")},
            data={"message": "Count rows"}
        )
        assert response.status_code == 200
        data = response.json()
        # sample_csv has header + 3 data rows, so rows_processed = 3
        assert data["rows_processed"] == 3

    def test_csv_upload_with_session_id(self, client, sample_csv_bytes, mock_agentcore_service):
        """Session ID is passed through."""
        response = client.post(
            "/analyze/csv",
            files={"file": ("test.csv", BytesIO(sample_csv_bytes), "text/csv")},
            data={"message": "Analyze", "session_id": "sess_custom123"}
        )
        assert response.status_code == 200


class TestTextAnalysis:
    """Tests for /analyze/text endpoint."""

    def test_text_analysis_success(self, client, sample_csv_content, mock_agentcore_service):
        """Successful text analysis."""
        response = client.post(
            "/analyze/text",
            data={"data": sample_csv_content, "message": "Analyze this"}
        )
        assert response.status_code == 200

    def test_text_analysis_empty(self, client, mock_agentcore_service):
        """Empty data still processes."""
        response = client.post(
            "/analyze/text",
            data={"data": "", "message": "Analyze empty"}
        )
        assert response.status_code == 200

    def test_text_analysis_missing_data(self, client):
        """Missing data returns validation error."""
        response = client.post(
            "/analyze/text",
            data={"message": "Analyze this"}
        )
        assert response.status_code == 422

    def test_text_analysis_missing_message(self, client):
        """Missing message returns validation error."""
        response = client.post(
            "/analyze/text",
            data={"data": "a,b\n1,2"}
        )
        assert response.status_code == 422

    def test_text_analysis_with_session(self, client, mock_agentcore_service):
        """Text analysis with session ID."""
        response = client.post(
            "/analyze/text",
            data={
                "data": "a,b\n1,2",
                "message": "Analyze",
                "session_id": "sess_text123"
            }
        )
        assert response.status_code == 200
