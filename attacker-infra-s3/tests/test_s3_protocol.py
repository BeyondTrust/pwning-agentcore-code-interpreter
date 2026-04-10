#!/usr/bin/env python3
"""
Unit tests for S3 protocol functions.

Run with: uv run pytest tests/test_s3_protocol.py -v
"""

import json
import unittest
from unittest.mock import MagicMock, patch

from botocore.exceptions import ClientError

from c2.core.s3_protocol import (
    generate_poll_url,
    generate_response_url,
    write_command,
    write_idle,
    read_output,
    poll_for_output,
)


def _make_client_error(code: str) -> ClientError:
    """Helper: build a botocore ClientError with the given error code."""
    return ClientError(
        {"Error": {"Code": code, "Message": "test error"}}, "operation"
    )


class TestGeneratePollUrl(unittest.TestCase):
    """Test presigned GET URL generation for command polling."""

    @patch("c2.core.s3_protocol._s3_client")
    def test_returns_presigned_url(self, mock_s3_client):
        mock_client = MagicMock()
        mock_s3_client.return_value = mock_client
        mock_client.generate_presigned_url.return_value = "https://s3.example.com/presigned"

        url = generate_poll_url("my-bucket", "sess_abc12345")

        self.assertEqual(url, "https://s3.example.com/presigned")

    @patch("c2.core.s3_protocol._s3_client")
    def test_uses_get_object_operation(self, mock_s3_client):
        mock_client = MagicMock()
        mock_s3_client.return_value = mock_client
        mock_client.generate_presigned_url.return_value = "https://..."

        generate_poll_url("my-bucket", "sess_abc12345")

        args, _ = mock_client.generate_presigned_url.call_args
        self.assertEqual(args[0], "get_object")

    @patch("c2.core.s3_protocol._s3_client")
    def test_uses_correct_s3_key(self, mock_s3_client):
        mock_client = MagicMock()
        mock_s3_client.return_value = mock_client
        mock_client.generate_presigned_url.return_value = "https://..."

        generate_poll_url("my-bucket", "sess_abc12345")

        _, kwargs = mock_client.generate_presigned_url.call_args
        self.assertEqual(kwargs["Params"]["Key"], "sessions/sess_abc12345/cmd")
        self.assertEqual(kwargs["Params"]["Bucket"], "my-bucket")

    @patch("c2.core.s3_protocol._s3_client")
    def test_default_expiry_is_seven_days(self, mock_s3_client):
        mock_client = MagicMock()
        mock_s3_client.return_value = mock_client
        mock_client.generate_presigned_url.return_value = "https://..."

        generate_poll_url("my-bucket", "sess_abc12345")

        _, kwargs = mock_client.generate_presigned_url.call_args
        self.assertEqual(kwargs["ExpiresIn"], 604800)

    @patch("c2.core.s3_protocol._s3_client")
    def test_custom_expiry_is_forwarded(self, mock_s3_client):
        mock_client = MagicMock()
        mock_s3_client.return_value = mock_client
        mock_client.generate_presigned_url.return_value = "https://..."

        generate_poll_url("my-bucket", "sess_abc12345", expiry_seconds=3600)

        _, kwargs = mock_client.generate_presigned_url.call_args
        self.assertEqual(kwargs["ExpiresIn"], 3600)

    @patch("c2.core.s3_protocol._s3_client")
    def test_uses_specified_region(self, mock_s3_client):
        mock_client = MagicMock()
        mock_s3_client.return_value = mock_client
        mock_client.generate_presigned_url.return_value = "https://..."

        generate_poll_url("my-bucket", "sess_abc12345", region="eu-west-1")

        mock_s3_client.assert_called_once_with("eu-west-1")


class TestGenerateResponseUrl(unittest.TestCase):
    """Test presigned PUT URL generation for output upload."""

    @patch("c2.core.s3_protocol._s3_client")
    def test_returns_presigned_url(self, mock_s3_client):
        mock_client = MagicMock()
        mock_s3_client.return_value = mock_client
        mock_client.generate_presigned_url.return_value = "https://s3.example.com/presigned-put"

        url = generate_response_url("my-bucket", "sess_abc12345", seq=1)

        self.assertEqual(url, "https://s3.example.com/presigned-put")

    @patch("c2.core.s3_protocol._s3_client")
    def test_uses_put_object_operation(self, mock_s3_client):
        mock_client = MagicMock()
        mock_s3_client.return_value = mock_client
        mock_client.generate_presigned_url.return_value = "https://..."

        generate_response_url("my-bucket", "sess_abc12345", seq=1)

        args, _ = mock_client.generate_presigned_url.call_args
        self.assertEqual(args[0], "put_object")

    @patch("c2.core.s3_protocol._s3_client")
    def test_uses_correct_s3_key_with_seq(self, mock_s3_client):
        mock_client = MagicMock()
        mock_s3_client.return_value = mock_client
        mock_client.generate_presigned_url.return_value = "https://..."

        generate_response_url("my-bucket", "sess_abc12345", seq=3)

        _, kwargs = mock_client.generate_presigned_url.call_args
        self.assertEqual(kwargs["Params"]["Key"], "sessions/sess_abc12345/out/3")

    @patch("c2.core.s3_protocol._s3_client")
    def test_content_type_is_text_plain(self, mock_s3_client):
        mock_client = MagicMock()
        mock_s3_client.return_value = mock_client
        mock_client.generate_presigned_url.return_value = "https://..."

        generate_response_url("my-bucket", "sess_abc12345", seq=1)

        _, kwargs = mock_client.generate_presigned_url.call_args
        self.assertEqual(kwargs["Params"]["ContentType"], "text/plain")

    @patch("c2.core.s3_protocol._s3_client")
    def test_default_expiry_is_one_hour(self, mock_s3_client):
        mock_client = MagicMock()
        mock_s3_client.return_value = mock_client
        mock_client.generate_presigned_url.return_value = "https://..."

        generate_response_url("my-bucket", "sess_abc12345", seq=1)

        _, kwargs = mock_client.generate_presigned_url.call_args
        self.assertEqual(kwargs["ExpiresIn"], 3600)

    @patch("c2.core.s3_protocol._s3_client")
    def test_seq_zero_produces_correct_key(self, mock_s3_client):
        mock_client = MagicMock()
        mock_s3_client.return_value = mock_client
        mock_client.generate_presigned_url.return_value = "https://..."

        generate_response_url("my-bucket", "sess_abc12345", seq=0)

        _, kwargs = mock_client.generate_presigned_url.call_args
        self.assertEqual(kwargs["Params"]["Key"], "sessions/sess_abc12345/out/0")

    @patch("c2.core.s3_protocol._s3_client")
    def test_large_seq_number(self, mock_s3_client):
        mock_client = MagicMock()
        mock_s3_client.return_value = mock_client
        mock_client.generate_presigned_url.return_value = "https://..."

        generate_response_url("my-bucket", "sess_abc12345", seq=999)

        _, kwargs = mock_client.generate_presigned_url.call_args
        self.assertEqual(kwargs["Params"]["Key"], "sessions/sess_abc12345/out/999")


class TestWriteCommand(unittest.TestCase):
    """Test writing commands to S3."""

    @patch("c2.core.s3_protocol._s3_client")
    def test_writes_to_correct_bucket_and_key(self, mock_s3_client):
        mock_client = MagicMock()
        mock_s3_client.return_value = mock_client

        write_command("my-bucket", "sess_abc12345", seq=1, cmd="whoami",
                      response_put_url="https://put.example.com")

        call_kwargs = mock_client.put_object.call_args[1]
        self.assertEqual(call_kwargs["Bucket"], "my-bucket")
        self.assertEqual(call_kwargs["Key"], "sessions/sess_abc12345/cmd")

    @patch("c2.core.s3_protocol._s3_client")
    def test_body_is_valid_json(self, mock_s3_client):
        mock_client = MagicMock()
        mock_s3_client.return_value = mock_client

        write_command("my-bucket", "sess_abc12345", seq=2, cmd="ls -la",
                      response_put_url="https://put.example.com")

        call_kwargs = mock_client.put_object.call_args[1]
        body = json.loads(call_kwargs["Body"].decode())
        self.assertEqual(body["seq"], 2)
        self.assertEqual(body["cmd"], "ls -la")
        self.assertEqual(body["response_put_url"], "https://put.example.com")

    @patch("c2.core.s3_protocol._s3_client")
    def test_content_type_is_application_json(self, mock_s3_client):
        mock_client = MagicMock()
        mock_s3_client.return_value = mock_client

        write_command("my-bucket", "sess_abc12345", seq=1, cmd="ls",
                      response_put_url="https://...")

        call_kwargs = mock_client.put_object.call_args[1]
        self.assertEqual(call_kwargs["ContentType"], "application/json")

    @patch("c2.core.s3_protocol._s3_client")
    def test_body_is_bytes(self, mock_s3_client):
        mock_client = MagicMock()
        mock_s3_client.return_value = mock_client

        write_command("my-bucket", "sess_abc12345", seq=1, cmd="pwd",
                      response_put_url="https://...")

        call_kwargs = mock_client.put_object.call_args[1]
        self.assertIsInstance(call_kwargs["Body"], bytes)

    @patch("c2.core.s3_protocol._s3_client")
    def test_various_commands_encode_correctly(self, mock_s3_client):
        mock_client = MagicMock()
        mock_s3_client.return_value = mock_client

        commands = [
            "whoami",
            "ls -la /tmp",
            "aws sts get-caller-identity",
            "cat /etc/passwd | head -5",
        ]
        for i, cmd in enumerate(commands, start=1):
            write_command("bucket", "sess_test1234", seq=i, cmd=cmd,
                          response_put_url="https://...")
            call_kwargs = mock_client.put_object.call_args[1]
            body = json.loads(call_kwargs["Body"].decode())
            self.assertEqual(body["cmd"], cmd)
            self.assertEqual(body["seq"], i)


class TestWriteIdle(unittest.TestCase):
    """Test writing idle state to S3."""

    @patch("c2.core.s3_protocol._s3_client")
    def test_writes_to_correct_key(self, mock_s3_client):
        mock_client = MagicMock()
        mock_s3_client.return_value = mock_client

        write_idle("my-bucket", "sess_abc12345")

        call_kwargs = mock_client.put_object.call_args[1]
        self.assertEqual(call_kwargs["Key"], "sessions/sess_abc12345/cmd")

    @patch("c2.core.s3_protocol._s3_client")
    def test_idle_json_has_seq_zero(self, mock_s3_client):
        mock_client = MagicMock()
        mock_s3_client.return_value = mock_client

        write_idle("my-bucket", "sess_abc12345")

        call_kwargs = mock_client.put_object.call_args[1]
        body = json.loads(call_kwargs["Body"].decode())
        self.assertEqual(body["seq"], 0)

    @patch("c2.core.s3_protocol._s3_client")
    def test_idle_json_cmd_is_null(self, mock_s3_client):
        mock_client = MagicMock()
        mock_s3_client.return_value = mock_client

        write_idle("my-bucket", "sess_abc12345")

        call_kwargs = mock_client.put_object.call_args[1]
        body = json.loads(call_kwargs["Body"].decode())
        self.assertIsNone(body["cmd"])

    @patch("c2.core.s3_protocol._s3_client")
    def test_idle_has_no_response_put_url(self, mock_s3_client):
        mock_client = MagicMock()
        mock_s3_client.return_value = mock_client

        write_idle("my-bucket", "sess_abc12345")

        call_kwargs = mock_client.put_object.call_args[1]
        body = json.loads(call_kwargs["Body"].decode())
        self.assertNotIn("response_put_url", body)

    @patch("c2.core.s3_protocol._s3_client")
    def test_idle_body_is_bytes(self, mock_s3_client):
        mock_client = MagicMock()
        mock_s3_client.return_value = mock_client

        write_idle("my-bucket", "sess_abc12345")

        call_kwargs = mock_client.put_object.call_args[1]
        self.assertIsInstance(call_kwargs["Body"], bytes)


class TestReadOutput(unittest.TestCase):
    """Test reading command output from S3."""

    @patch("c2.core.s3_protocol._s3_client")
    def test_returns_decoded_content_when_available(self, mock_s3_client):
        mock_client = MagicMock()
        mock_s3_client.return_value = mock_client
        mock_body = MagicMock()
        mock_body.read.return_value = b"root\n"
        mock_client.get_object.return_value = {"Body": mock_body}

        result = read_output("my-bucket", "sess_abc12345", seq=1)

        self.assertEqual(result, "root\n")

    @patch("c2.core.s3_protocol._s3_client")
    def test_returns_none_on_no_such_key(self, mock_s3_client):
        mock_client = MagicMock()
        mock_s3_client.return_value = mock_client
        mock_client.get_object.side_effect = _make_client_error("NoSuchKey")

        result = read_output("my-bucket", "sess_abc12345", seq=1)

        self.assertIsNone(result)

    @patch("c2.core.s3_protocol._s3_client")
    def test_returns_none_on_404(self, mock_s3_client):
        mock_client = MagicMock()
        mock_s3_client.return_value = mock_client
        mock_client.get_object.side_effect = _make_client_error("404")

        result = read_output("my-bucket", "sess_abc12345", seq=1)

        self.assertIsNone(result)

    @patch("c2.core.s3_protocol._s3_client")
    def test_raises_on_access_denied(self, mock_s3_client):
        mock_client = MagicMock()
        mock_s3_client.return_value = mock_client
        mock_client.get_object.side_effect = _make_client_error("AccessDenied")

        with self.assertRaises(ClientError):
            read_output("my-bucket", "sess_abc12345", seq=1)

    @patch("c2.core.s3_protocol._s3_client")
    def test_raises_on_other_client_errors(self, mock_s3_client):
        mock_client = MagicMock()
        mock_s3_client.return_value = mock_client
        mock_client.get_object.side_effect = _make_client_error("InternalError")

        with self.assertRaises(ClientError):
            read_output("my-bucket", "sess_abc12345", seq=1)

    @patch("c2.core.s3_protocol._s3_client")
    def test_reads_from_correct_key(self, mock_s3_client):
        mock_client = MagicMock()
        mock_s3_client.return_value = mock_client
        mock_body = MagicMock()
        mock_body.read.return_value = b"output"
        mock_client.get_object.return_value = {"Body": mock_body}

        read_output("my-bucket", "sess_abc12345", seq=7)

        mock_client.get_object.assert_called_once_with(
            Bucket="my-bucket",
            Key="sessions/sess_abc12345/out/7",
        )

    @patch("c2.core.s3_protocol._s3_client")
    def test_result_is_string_not_bytes(self, mock_s3_client):
        mock_client = MagicMock()
        mock_s3_client.return_value = mock_client
        mock_body = MagicMock()
        mock_body.read.return_value = b"uid=0(root)"
        mock_client.get_object.return_value = {"Body": mock_body}

        result = read_output("my-bucket", "sess_abc12345", seq=1)

        self.assertIsInstance(result, str)

    @patch("c2.core.s3_protocol._s3_client")
    def test_multiline_output(self, mock_s3_client):
        mock_client = MagicMock()
        mock_s3_client.return_value = mock_client
        mock_body = MagicMock()
        mock_body.read.return_value = "line1\nline2\nline3\n".encode()
        mock_client.get_object.return_value = {"Body": mock_body}

        result = read_output("my-bucket", "sess_abc12345", seq=1)

        self.assertEqual(result, "line1\nline2\nline3\n")


class TestPollForOutput(unittest.TestCase):
    """Test polling S3 for output with timeout/retry logic."""

    @patch("c2.core.s3_protocol.time.sleep")
    @patch("c2.core.s3_protocol._s3_client")
    def test_returns_immediately_when_output_available(self, mock_s3_client, mock_sleep):
        mock_client = MagicMock()
        mock_s3_client.return_value = mock_client
        mock_body = MagicMock()
        mock_body.read.return_value = b"whoami output"
        mock_client.get_object.return_value = {"Body": mock_body}

        result = poll_for_output("my-bucket", "sess_abc12345", seq=1, timeout=30)

        self.assertEqual(result, "whoami output")
        mock_sleep.assert_not_called()

    @patch("c2.core.s3_protocol.time.sleep")
    @patch("c2.core.s3_protocol.time.time")
    @patch("c2.core.s3_protocol._s3_client")
    def test_returns_none_on_timeout(self, mock_s3_client, mock_time, mock_sleep):
        mock_client = MagicMock()
        mock_s3_client.return_value = mock_client
        mock_client.get_object.side_effect = _make_client_error("NoSuchKey")

        # Simulates: start=0, first loop check=0, second loop check=61 (past deadline)
        mock_time.side_effect = [0, 0, 61]

        result = poll_for_output("my-bucket", "sess_abc12345", seq=1, timeout=60, interval=2)

        self.assertIsNone(result)

    @patch("c2.core.s3_protocol.time.sleep")
    @patch("c2.core.s3_protocol.time.time")
    @patch("c2.core.s3_protocol._s3_client")
    def test_retries_until_output_appears(self, mock_s3_client, mock_time, mock_sleep):
        mock_client = MagicMock()
        mock_s3_client.return_value = mock_client

        no_key_error = _make_client_error("NoSuchKey")
        mock_body = MagicMock()
        mock_body.read.return_value = b"result"

        # Fail twice, then succeed on third attempt
        mock_client.get_object.side_effect = [
            no_key_error,
            no_key_error,
            {"Body": mock_body},
        ]
        mock_time.side_effect = [0, 0, 5, 10, 15]

        result = poll_for_output("my-bucket", "sess_abc12345", seq=1, timeout=60, interval=2)

        self.assertEqual(result, "result")
        self.assertEqual(mock_client.get_object.call_count, 3)
        self.assertEqual(mock_sleep.call_count, 2)

    @patch("c2.core.s3_protocol.time.sleep")
    @patch("c2.core.s3_protocol.time.time")
    @patch("c2.core.s3_protocol._s3_client")
    def test_sleeps_with_correct_interval_between_polls(
        self, mock_s3_client, mock_time, mock_sleep
    ):
        mock_client = MagicMock()
        mock_s3_client.return_value = mock_client

        no_key_error = _make_client_error("NoSuchKey")
        mock_body = MagicMock()
        mock_body.read.return_value = b"ok"

        mock_client.get_object.side_effect = [no_key_error, {"Body": mock_body}]
        mock_time.side_effect = [0, 0, 5, 10]

        poll_for_output("my-bucket", "sess_abc12345", seq=1, timeout=60, interval=5)

        mock_sleep.assert_called_with(5)

    @patch("c2.core.s3_protocol.time.sleep")
    @patch("c2.core.s3_protocol.time.time")
    @patch("c2.core.s3_protocol._s3_client")
    def test_default_interval_is_two_seconds(self, mock_s3_client, mock_time, mock_sleep):
        mock_client = MagicMock()
        mock_s3_client.return_value = mock_client

        no_key_error = _make_client_error("NoSuchKey")
        mock_body = MagicMock()
        mock_body.read.return_value = b"ok"

        mock_client.get_object.side_effect = [no_key_error, {"Body": mock_body}]
        mock_time.side_effect = [0, 0, 5, 10]

        poll_for_output("my-bucket", "sess_abc12345", seq=1, timeout=60)

        mock_sleep.assert_called_with(2)


class TestS3KeyScheme(unittest.TestCase):
    """
    Cross-function tests verifying the key naming scheme is consistent.

    The payload client polls sessions/{session_id}/cmd and writes output to
    sessions/{session_id}/out/{seq}.  These tests ensure the operator-side
    functions use the same keys so the two sides interoperate.
    """

    @patch("c2.core.s3_protocol._s3_client")
    def test_poll_url_and_write_command_use_same_cmd_key(self, mock_s3_client):
        mock_client = MagicMock()
        mock_s3_client.return_value = mock_client
        mock_client.generate_presigned_url.return_value = "https://..."

        generate_poll_url("bucket", "sess_deadbeef")
        write_command("bucket", "sess_deadbeef", seq=1, cmd="id",
                      response_put_url="https://...")

        poll_key = mock_client.generate_presigned_url.call_args[1]["Params"]["Key"]
        write_key = mock_client.put_object.call_args[1]["Key"]
        self.assertEqual(poll_key, write_key)

    @patch("c2.core.s3_protocol._s3_client")
    def test_response_url_and_read_output_use_same_out_key(self, mock_s3_client):
        mock_client = MagicMock()
        mock_s3_client.return_value = mock_client
        mock_client.generate_presigned_url.return_value = "https://..."
        mock_body = MagicMock()
        mock_body.read.return_value = b"data"
        mock_client.get_object.return_value = {"Body": mock_body}

        generate_response_url("bucket", "sess_deadbeef", seq=5)
        read_output("bucket", "sess_deadbeef", seq=5)

        response_key = mock_client.generate_presigned_url.call_args[1]["Params"]["Key"]
        read_key = mock_client.get_object.call_args[1]["Key"]
        self.assertEqual(response_key, read_key)

    @patch("c2.core.s3_protocol._s3_client")
    def test_write_idle_overwrites_same_key_as_write_command(self, mock_s3_client):
        mock_client = MagicMock()
        mock_s3_client.return_value = mock_client

        write_command("bucket", "sess_deadbeef", seq=1, cmd="id",
                      response_put_url="https://...")
        cmd_key = mock_client.put_object.call_args[1]["Key"]

        write_idle("bucket", "sess_deadbeef")
        idle_key = mock_client.put_object.call_args[1]["Key"]

        self.assertEqual(cmd_key, idle_key)


if __name__ == "__main__":
    unittest.main(verbosity=2)
