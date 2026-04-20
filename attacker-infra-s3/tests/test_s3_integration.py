#!/usr/bin/env python3
"""
Integration tests for the S3 C2 channel.

Uses MockS3C2Server to simulate the full operator → payload → operator
command lifecycle without any real AWS calls.

Run with: uv run pytest tests/test_s3_integration.py -v
"""

import json
import unittest

from tests.mock_s3_server import MockS3C2Server


class TestCommandLifecycle(unittest.TestCase):
    """Test the end-to-end command execution lifecycle."""

    def setUp(self):
        self.server = MockS3C2Server()

    def test_output_unavailable_before_payload_executes(self):
        """Operator should get None if the payload hasn't run yet."""
        self.server.write_command("sess_aabbccdd", seq=1, cmd="whoami")

        result = self.server.read_output("sess_aabbccdd", seq=1)

        self.assertIsNone(result)

    def test_operator_reads_output_after_payload_executes(self):
        """Full cycle: write command → payload runs → operator reads output."""
        self.server.write_command("sess_aabbccdd", seq=1, cmd="whoami")
        self.server.simulate_payload_loop_once("sess_aabbccdd")

        result = self.server.read_output("sess_aabbccdd", seq=1)

        self.assertIsNotNone(result)
        self.assertIn("whoami", result)

    def test_output_reflects_issued_command(self):
        """Output string should reference the command that was run."""
        cmd = "cat /etc/passwd"
        self.server.write_command("sess_aabbccdd", seq=1, cmd=cmd)
        self.server.simulate_payload_loop_once("sess_aabbccdd")

        result = self.server.read_output("sess_aabbccdd", seq=1)

        self.assertIn(cmd, result)

    def test_sequential_commands_execute_in_order(self):
        """Three commands issued sequentially should all produce output."""
        commands = ["whoami", "pwd", "id"]
        last_seq = 0

        for i, cmd in enumerate(commands, start=1):
            self.server.write_command("sess_aabbccdd", seq=i, cmd=cmd)
            last_seq = self.server.simulate_payload_loop_once("sess_aabbccdd", last_seq)
            result = self.server.read_output("sess_aabbccdd", seq=i)
            self.assertIsNotNone(result, f"No output for seq={i} cmd={cmd!r}")
            self.assertIn(cmd, result)

    def test_idle_state_produces_no_output(self):
        """When the session is idle (cmd=None), the payload does nothing."""
        self.server.write_idle("sess_aabbccdd")
        self.server.simulate_payload_loop_once("sess_aabbccdd")

        # No output should have been uploaded
        state = self.server.get_state()
        self.assertEqual(state["outputs"], {})

    def test_reset_to_idle_after_command(self):
        """Operator can reset to idle after a command completes."""
        self.server.write_command("sess_aabbccdd", seq=1, cmd="ls")
        self.server.simulate_payload_loop_once("sess_aabbccdd")

        # Reset
        self.server.write_idle("sess_aabbccdd")

        cmd_obj = self.server.poll_command("sess_aabbccdd")
        self.assertIsNone(cmd_obj["cmd"])

    def test_output_persists_after_session_reset(self):
        """Previous output should still be readable after idle reset."""
        self.server.write_command("sess_aabbccdd", seq=1, cmd="whoami")
        self.server.simulate_payload_loop_once("sess_aabbccdd")
        self.server.write_idle("sess_aabbccdd")

        result = self.server.read_output("sess_aabbccdd", seq=1)

        self.assertIsNotNone(result)

    def test_subsequent_command_after_reset(self):
        """After idle reset, a new command should execute normally."""
        self.server.write_command("sess_aabbccdd", seq=1, cmd="whoami")
        last_seq = self.server.simulate_payload_loop_once("sess_aabbccdd")

        self.server.write_idle("sess_aabbccdd")

        self.server.write_command("sess_aabbccdd", seq=2, cmd="id")
        last_seq = self.server.simulate_payload_loop_once("sess_aabbccdd", last_seq)

        result = self.server.read_output("sess_aabbccdd", seq=2)
        self.assertIsNotNone(result)
        self.assertIn("id", result)


class TestSequenceNumberDeduplication(unittest.TestCase):
    """
    Test that the payload's sequence-number guard prevents re-execution.

    The mini client uses `if q > n` (current seq > last seen seq) to skip
    commands it has already executed.  This avoids re-running a command when
    the operator polls the same command object multiple times.
    """

    def setUp(self):
        self.server = MockS3C2Server()

    def test_same_seq_not_re_executed(self):
        """Running the payload loop twice with the same seq should produce only one output."""
        self.server.write_command("sess_aabbccdd", seq=1, cmd="whoami")

        last_seq = self.server.simulate_payload_loop_once("sess_aabbccdd", last_seq=0)
        # Output uploaded once
        first_output = self.server.read_output("sess_aabbccdd", seq=1)

        # Overwrite with same seq (operator hasn't incremented yet) - simulates retry
        self.server.write_command("sess_aabbccdd", seq=1, cmd="whoami")
        self.server.simulate_payload_loop_once("sess_aabbccdd", last_seq=last_seq)

        # Output object should still be the same (no second PUT)
        second_output = self.server.read_output("sess_aabbccdd", seq=1)
        self.assertEqual(first_output, second_output)

    def test_lower_seq_not_re_executed(self):
        """A command with seq < last-seen seq must not produce new output."""
        self.server.write_command("sess_aabbccdd", seq=5, cmd="ls")
        last_seq = self.server.simulate_payload_loop_once("sess_aabbccdd", last_seq=0)
        self.assertEqual(last_seq, 5)

        # Replay seq=3 (lower)
        self.server.write_command("sess_aabbccdd", seq=3, cmd="rerun")
        self.server.simulate_payload_loop_once("sess_aabbccdd", last_seq=last_seq)

        result = self.server.read_output("sess_aabbccdd", seq=3)
        self.assertIsNone(result)

    def test_higher_seq_does_execute(self):
        """A command with seq > last-seen seq must execute."""
        self.server.write_command("sess_aabbccdd", seq=1, cmd="first")
        last_seq = self.server.simulate_payload_loop_once("sess_aabbccdd", last_seq=0)

        self.server.write_command("sess_aabbccdd", seq=2, cmd="second")
        self.server.simulate_payload_loop_once("sess_aabbccdd", last_seq=last_seq)

        result = self.server.read_output("sess_aabbccdd", seq=2)
        self.assertIsNotNone(result)
        self.assertIn("second", result)

    def test_seq_counter_advances_correctly(self):
        """simulate_payload_loop_once must return the new last_seq."""
        self.server.write_command("sess_aabbccdd", seq=7, cmd="cmd")
        last_seq = self.server.simulate_payload_loop_once("sess_aabbccdd", last_seq=0)
        self.assertEqual(last_seq, 7)

    def test_idle_does_not_advance_seq_counter(self):
        """Processing an idle state should leave last_seq unchanged."""
        self.server.write_idle("sess_aabbccdd")
        last_seq = self.server.simulate_payload_loop_once("sess_aabbccdd", last_seq=3)
        self.assertEqual(last_seq, 3)


class TestMultipleSessionIsolation(unittest.TestCase):
    """Test that multiple concurrent sessions don't interfere with each other."""

    def setUp(self):
        self.server = MockS3C2Server()

    def test_commands_scoped_to_session(self):
        """Each session must see only its own command."""
        self.server.write_command("sess_session1a", seq=1, cmd="cmd_for_1")
        self.server.write_command("sess_session2b", seq=1, cmd="cmd_for_2")

        obj1 = self.server.poll_command("sess_session1a")
        obj2 = self.server.poll_command("sess_session2b")

        self.assertEqual(obj1["cmd"], "cmd_for_1")
        self.assertEqual(obj2["cmd"], "cmd_for_2")

    def test_output_scoped_to_session(self):
        """Each session must read only its own output."""
        self.server.write_command("sess_session1a", seq=1, cmd="cmd_for_1")
        self.server.write_command("sess_session2b", seq=1, cmd="cmd_for_2")

        self.server.simulate_payload_loop_once("sess_session1a")
        self.server.simulate_payload_loop_once("sess_session2b")

        out1 = self.server.read_output("sess_session1a", seq=1)
        out2 = self.server.read_output("sess_session2b", seq=1)

        self.assertIn("cmd_for_1", out1)
        self.assertIn("cmd_for_2", out2)
        self.assertNotIn("cmd_for_2", out1)
        self.assertNotIn("cmd_for_1", out2)

    def test_resetting_one_session_does_not_affect_another(self):
        """Resetting session 1 must not change session 2's command."""
        self.server.write_command("sess_session1a", seq=1, cmd="cmd1")
        self.server.write_command("sess_session2b", seq=1, cmd="cmd2")

        self.server.write_idle("sess_session1a")

        obj2 = self.server.poll_command("sess_session2b")
        self.assertEqual(obj2["cmd"], "cmd2")

    def test_sessions_can_have_independent_seq_counters(self):
        """Sessions advance their own seq counters independently."""
        self.server.write_command("sess_session1a", seq=1, cmd="a1")
        self.server.write_command("sess_session2b", seq=5, cmd="b5")

        last1 = self.server.simulate_payload_loop_once("sess_session1a", last_seq=0)
        last2 = self.server.simulate_payload_loop_once("sess_session2b", last_seq=0)

        self.assertEqual(last1, 1)
        self.assertEqual(last2, 5)

    def test_missing_session_returns_none(self):
        """Polling a session that has never been written returns None."""
        result = self.server.poll_command("sess_nonexistent")
        self.assertIsNone(result)

    def test_output_not_cross_contaminated_across_many_sessions(self):
        """Five independent sessions should each see only their own output."""
        sessions = [f"sess_{i:08x}" for i in range(5)]
        cmds = [f"echo session_{i}" for i in range(5)]

        for sess, cmd in zip(sessions, cmds):
            self.server.write_command(sess, seq=1, cmd=cmd)
            self.server.simulate_payload_loop_once(sess)

        for i, (sess, cmd) in enumerate(zip(sessions, cmds)):
            out = self.server.read_output(sess, seq=1)
            self.assertIsNotNone(out)
            self.assertIn(cmd, out)
            # Ensure no bleed-through from other sessions
            for j, other_cmd in enumerate(cmds):
                if j != i:
                    self.assertNotIn(other_cmd, out)


class TestPayloadPolling(unittest.TestCase):
    """Test payload polling behaviour when no command is pending."""

    def setUp(self):
        self.server = MockS3C2Server()

    def test_poll_before_any_write_returns_none(self):
        result = self.server.poll_command("sess_fresh0000")
        self.assertIsNone(result)

    def test_poll_returns_command_after_write(self):
        self.server.write_command("sess_aabbccdd", seq=1, cmd="id")
        obj = self.server.poll_command("sess_aabbccdd")
        self.assertIsNotNone(obj)
        self.assertEqual(obj["cmd"], "id")
        self.assertEqual(obj["seq"], 1)

    def test_poll_returns_idle_state_after_reset(self):
        self.server.write_command("sess_aabbccdd", seq=1, cmd="id")
        self.server.write_idle("sess_aabbccdd")

        obj = self.server.poll_command("sess_aabbccdd")

        self.assertIsNone(obj["cmd"])
        self.assertEqual(obj["seq"], 0)

    def test_command_object_contains_response_put_url(self):
        put_url = "https://mock-s3.example.com/out/1"
        self.server.write_command("sess_aabbccdd", seq=1, cmd="id",
                                  response_put_url=put_url)
        obj = self.server.poll_command("sess_aabbccdd")
        self.assertEqual(obj["response_put_url"], put_url)

    def test_latest_write_overwrites_previous(self):
        """If operator sends two commands, the payload sees the latest one."""
        self.server.write_command("sess_aabbccdd", seq=1, cmd="first")
        self.server.write_command("sess_aabbccdd", seq=2, cmd="second")

        obj = self.server.poll_command("sess_aabbccdd")

        self.assertEqual(obj["cmd"], "second")
        self.assertEqual(obj["seq"], 2)


class TestCommandObjectFormat(unittest.TestCase):
    """
    Verify that write_command produces JSON compatible with the mini client.

    The mini client parses:
      o = json.loads(b)
      if o.get('cmd'): ...
          q, c, ru = o.get('seq', 0), o['cmd'], o.get('response_put_url')
    """

    def setUp(self):
        self.server = MockS3C2Server()

    def test_command_object_has_seq_field(self):
        self.server.write_command("sess_aabbccdd", seq=3, cmd="ls")
        obj = self.server.poll_command("sess_aabbccdd")
        self.assertIn("seq", obj)
        self.assertEqual(obj["seq"], 3)

    def test_command_object_has_cmd_field(self):
        self.server.write_command("sess_aabbccdd", seq=1, cmd="pwd")
        obj = self.server.poll_command("sess_aabbccdd")
        self.assertIn("cmd", obj)
        self.assertEqual(obj["cmd"], "pwd")

    def test_command_object_has_response_put_url_field(self):
        self.server.write_command("sess_aabbccdd", seq=1, cmd="ls",
                                  response_put_url="https://put.example.com")
        obj = self.server.poll_command("sess_aabbccdd")
        self.assertIn("response_put_url", obj)

    def test_idle_object_cmd_is_falsy(self):
        """Idle cmd=None must be falsy so the mini client skips execution."""
        self.server.write_idle("sess_aabbccdd")
        obj = self.server.poll_command("sess_aabbccdd")
        self.assertFalse(obj.get("cmd"))

    def test_command_stored_as_valid_json_string(self):
        """The raw stored value must be parseable JSON."""
        self.server.write_command("sess_aabbccdd", seq=1, cmd="whoami",
                                  response_put_url="https://put.example.com")
        raw = self.server._commands["sess_aabbccdd"]
        parsed = json.loads(raw)
        self.assertEqual(parsed["cmd"], "whoami")


class TestServerState(unittest.TestCase):
    """Test the MockS3C2Server's get_state() introspection helper."""

    def setUp(self):
        self.server = MockS3C2Server()

    def test_initial_state_is_empty(self):
        state = self.server.get_state()
        self.assertEqual(state["commands"], {})
        self.assertEqual(state["outputs"], {})

    def test_state_reflects_written_command(self):
        self.server.write_command("sess_aabbccdd", seq=1, cmd="ls")
        state = self.server.get_state()
        self.assertIn("sess_aabbccdd", state["commands"])

    def test_state_reflects_uploaded_output(self):
        self.server.write_command("sess_aabbccdd", seq=1, cmd="ls")
        self.server.simulate_payload_loop_once("sess_aabbccdd")
        state = self.server.get_state()
        self.assertTrue(len(state["outputs"]) > 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
