#!/usr/bin/env python3
"""
Integration tests for DNS C2 system.

Tests client/server interaction, state management, and retry behavior.
These catch bugs that unit tests miss.

Run with: python3 -m pytest tests/test_dns_integration.py -v
Or:       python3 tests/test_dns_integration.py
"""

import unittest
import sys
from pathlib import Path

# Add tests to path for mock server
sys.path.insert(0, str(Path(__file__).parent))

from mock_dns_server import MockC2Server


class TestDNSRetryBehavior(unittest.TestCase):
    """Test DNS retry handling and client resilience."""
    
    def setUp(self):
        """Set up mock server for each test."""
        self.server = MockC2Server()
    
    def test_single_client_complete_command(self):
        """Test client successfully fetches a complete command."""
        self.server.queue_command("whoami")
        
        command, chunks, success = self.server.get_command_from_chunks("session_a")
        
        self.assertTrue(success)
        self.assertEqual(command, "whoami")
        self.assertEqual(len(chunks), 3)  # "d2hvYW1p" = 3 chunks
    
    def test_retry_last_chunk(self):
        """
        The bug: When client retries the last chunk, server returns 0.0.0.0.
        
        This test reproduces the exact bug from production logs:
        - Chunk 0: 10.100.50.104 ✓
        - Chunk 1: 10.118.89.87 ✓
        - Chunk 2: should be 11.49.112.0 (last), not 0.0.0.0
        """
        self.server.queue_command("whoami")
        
        # Simulate normal client fetch
        chunk_0 = self.server.query_chunk("session_a", 0)
        chunk_1 = self.server.query_chunk("session_a", 1)
        chunk_2 = self.server.query_chunk("session_a", 2)
        
        # These should all be valid
        self.assertNotEqual(chunk_0, "0.0.0.0")
        self.assertNotEqual(chunk_1, "0.0.0.0")
        self.assertNotEqual(chunk_2, "0.0.0.0")
        
        # Last chunk should have 11. prefix
        self.assertTrue(chunk_2.startswith("11."))
        
        # NOW retry chunk 2 (simulating DNS retry)
        chunk_2_retry = self.server.query_chunk("session_a", 2)
        
        # THE BUG: this would return 0.0.0.0
        # THE FIX: this should still return the same chunk
        self.assertEqual(chunk_2_retry, chunk_2)
        self.assertNotEqual(chunk_2_retry, "0.0.0.0")
    
    def test_multiple_chunks_with_retries(self):
        """Test client retrying multiple chunks doesn't break command."""
        self.server.queue_command("whoami")
        
        # Get all chunks with simulated retries
        chunks = []
        for i in range(5):  # Try to get 5 (command only has 3)
            response = self.server.query_chunk("session_a", i)
            
            # Retry once if we get 0.0.0.0 (simulating client retry logic)
            if response == "0.0.0.0":
                response = self.server.query_chunk("session_a", i)
            
            chunks.append(response)
            
            if response == "0.0.0.0":
                break
        
        # Should have exactly 3 chunks
        self.assertEqual(len([c for c in chunks if c != "0.0.0.0"]), 3)
        
        # Reconstruct command
        command, _, success = self.server.get_command_from_chunks("session_a")
        self.assertTrue(success)
        self.assertEqual(command, "whoami")


class TestMultipleSessionHandling(unittest.TestCase):
    """Test server handling multiple concurrent clients."""
    
    def setUp(self):
        """Set up mock server for each test."""
        self.server = MockC2Server()
    
    def test_two_sessions_same_command(self):
        """Two clients should both get the complete command."""
        self.server.queue_command("whoami")
        
        # Both sessions fetch the command
        cmd_a, chunks_a, success_a = self.server.get_command_from_chunks("session_a")
        cmd_b, chunks_b, success_b = self.server.get_command_from_chunks("session_b")
        
        # Both should succeed
        self.assertTrue(success_a)
        self.assertTrue(success_b)
        
        # Both should get same command
        self.assertEqual(cmd_a, "whoami")
        self.assertEqual(cmd_b, "whoami")
        
        # Both should get same chunks
        self.assertEqual(chunks_a, chunks_b)
    
    def test_interleaved_chunk_fetching(self):
        """Sessions interleaving chunk fetches shouldn't cause issues."""
        self.server.queue_command("whoami")
        
        # Simulate interleaved fetching
        chunk_a0 = self.server.query_chunk("session_a", 0)
        chunk_b0 = self.server.query_chunk("session_b", 0)
        chunk_a1 = self.server.query_chunk("session_a", 1)
        chunk_b1 = self.server.query_chunk("session_b", 1)
        chunk_a2 = self.server.query_chunk("session_a", 2)
        chunk_b2 = self.server.query_chunk("session_b", 2)
        
        # All should be valid (not 0.0.0.0)
        for chunk in [chunk_a0, chunk_b0, chunk_a1, chunk_b1, chunk_a2, chunk_b2]:
            self.assertNotEqual(chunk, "0.0.0.0")
        
        # Last chunks should have 11. prefix
        self.assertTrue(chunk_a2.startswith("11."))
        self.assertTrue(chunk_b2.startswith("11."))
        
        # Both should successfully decode
        cmd_a, _, success_a = self.server.get_command_from_chunks("session_a")
        cmd_b, _, success_b = self.server.get_command_from_chunks("session_b")
        
        self.assertTrue(success_a)
        self.assertTrue(success_b)
        self.assertEqual(cmd_a, "whoami")
        self.assertEqual(cmd_b, "whoami")


class TestCommandLifecycle(unittest.TestCase):
    """Test command queue lifecycle: queue → deliver → cleanup → next."""
    
    def setUp(self):
        """Set up mock server for each test."""
        self.server = MockC2Server()
    
    def test_command_lifecycle(self):
        """Test: queue → deliver all chunks → queue new → get new chunks."""
        # Queue first command
        self.server.queue_command("whoami")
        
        # Client fetches all chunks of command 1
        cmd_1, _, success_1 = self.server.get_command_from_chunks("session_a")
        self.assertTrue(success_1)
        self.assertEqual(cmd_1, "whoami")
        
        # Queue second command
        self.server.queue_command("ls")
        
        # Client should get new command, not old chunks
        cmd_2, _, success_2 = self.server.get_command_from_chunks("session_a")
        self.assertTrue(success_2)
        self.assertEqual(cmd_2, "ls")
        
        # Commands should be different
        self.assertNotEqual(cmd_1, cmd_2)
    
    def test_pending_commands_per_session(self):
        """Different sessions can have different pending commands."""
        self.server.queue_command("whoami", session_id="session_a")
        self.server.queue_command("ls", session_id="session_b")
        
        # Each session gets its own command
        cmd_a, _, success_a = self.server.get_command_from_chunks("session_a")
        cmd_b, _, success_b = self.server.get_command_from_chunks("session_b")
        
        self.assertTrue(success_a)
        self.assertTrue(success_b)
        self.assertEqual(cmd_a, "whoami")
        self.assertEqual(cmd_b, "ls")


class TestStateConsistency(unittest.TestCase):
    """Test server maintains consistent state during operations."""
    
    def setUp(self):
        """Set up mock server for each test."""
        self.server = MockC2Server()
    
    def test_pending_commands_not_deleted_early(self):
        """
        Verify pending commands persist until new command queued.
        
        Bug scenario that this catches:
        - Server sends chunk 2 (last)
        - Server deletes pending command
        - Client retries chunk 2
        - Server returns 0.0.0.0 (no command!)
        """
        self.server.queue_command("whoami")
        
        # Get all chunks
        chunk_0 = self.server.query_chunk("session_a", 0)
        chunk_1 = self.server.query_chunk("session_a", 1)
        chunk_2 = self.server.query_chunk("session_a", 2)  # Last chunk
        
        # Verify all chunks are valid
        self.assertNotEqual(chunk_0, "0.0.0.0")
        self.assertNotEqual(chunk_1, "0.0.0.0")
        self.assertNotEqual(chunk_2, "0.0.0.0")
        
        # Even after getting last chunk, can still retry
        chunk_2_again = self.server.query_chunk("session_a", 2)
        self.assertEqual(chunk_2_again, chunk_2)
        
        # And retry again
        chunk_2_third = self.server.query_chunk("session_a", 2)
        self.assertEqual(chunk_2_third, chunk_2)
        
        # But chunk 3 doesn't exist
        chunk_3 = self.server.query_chunk("session_a", 3)
        self.assertEqual(chunk_3, "0.0.0.0")
    
    def test_server_state_tracking(self):
        """Test server's internal state is consistent."""
        self.server.queue_command("whoami")
        
        # Get initial state
        state_1 = self.server.get_state()
        self.assertIn("*", state_1["pending_commands"])
        
        # Fetch chunks
        self.server.query_chunk("session_a", 0)
        self.server.query_chunk("session_a", 1)
        self.server.query_chunk("session_a", 2)
        
        # State should still have command
        state_2 = self.server.get_state()
        self.assertIn("*", state_2["pending_commands"])
        self.assertIn("session_a", state_2["completed_commands"])


class TestRealClientSimulation(unittest.TestCase):
    """Simulate real client behavior with retries and polling."""
    
    def setUp(self):
        """Set up mock server for each test."""
        self.server = MockC2Server()
    
    def test_real_client_behavior_simple(self):
        """Simulate client polling until last chunk is received."""
        self.server.queue_command("whoami")
        
        command_b64 = ""
        DNS_RETRY_ATTEMPTS = 3
        
        chunk_num = 0
        while chunk_num < 50:  # Client's max chunk loop
            got_chunk = False
            
            for attempt in range(DNS_RETRY_ATTEMPTS):
                response = self.server.query_chunk("session_a", chunk_num)
                
                if response and response != "0.0.0.0":
                    # Successfully got response
                    chunk_data, is_last = self.server.decode_chunk(response)
                    command_b64 += chunk_data
                    got_chunk = True
                    
                    if is_last:
                        break
                    
                    chunk_num += 1
                    break
                
                if attempt == DNS_RETRY_ATTEMPTS - 1:
                    # Failed to get chunk after retries
                    self.fail(f"Chunk {chunk_num}: Got 0.0.0.0 after {DNS_RETRY_ATTEMPTS} retries")
            
            if not got_chunk or is_last:
                break
        
        # Verify we got complete command
        import base64
        decoded = base64.b64decode(command_b64).decode()
        self.assertEqual(decoded, "whoami")
    
    def test_real_client_with_backoff(self):
        """Simulate client with exponential backoff retry."""
        self.server.queue_command("ls -la")
        
        command_b64 = ""
        
        chunk_num = 0
        while chunk_num < 50:
            got_chunk = False
            backoff_time = 1
            
            for attempt in range(3):
                response = self.server.query_chunk("session_a", chunk_num)
                
                if response != "0.0.0.0":
                    chunk_data, is_last = self.server.decode_chunk(response)
                    command_b64 += chunk_data
                    got_chunk = True
                    
                    if is_last:
                        break
                    
                    chunk_num += 1
                    break
                
                # Exponential backoff (in real code would sleep)
                backoff_time *= 2
                
                if attempt == 2:
                    self.fail(f"Failed to get chunk {chunk_num} after exponential backoff")
            
            if not got_chunk or is_last:
                break
        
        # Verify
        import base64
        decoded = base64.b64decode(command_b64).decode()
        self.assertEqual(decoded, "ls -la")


def run_tests():
    """Run all integration tests."""
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromModule(sys.modules[__name__])
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    return result.wasSuccessful()


if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)
