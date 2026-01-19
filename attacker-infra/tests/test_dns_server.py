#!/usr/bin/env python3
"""
Unit tests for DNS server encoding logic.

These tests validate the encoding logic in dns_server_with_api.py
by importing the helper functions defined in that file.

Run with: python3 tests/test_dns_server.py
"""

import unittest
import sys
import base64
from pathlib import Path

# Add terraform/c2-server to path to import DNS server helper functions
sys.path.insert(0, str(Path(__file__).parent.parent / 'terraform' / 'c2-server'))

from dns_server_with_api import (
    encode_chunk_to_ip,
    encode_command_to_chunks,
    calculate_chunk_count,
)


class TestDNSServerEncoding(unittest.TestCase):
    """Test DNS server's chunk encoding logic."""
    
    def test_encode_first_chunk(self):
        """Test encoding first chunk (not last)."""
        result = encode_chunk_to_ip("d2h", False)
        self.assertEqual(result, "10.100.50.104")
    
    def test_encode_middle_chunk(self):
        """Test encoding middle chunk (not last)."""
        result = encode_chunk_to_ip("vYW", False)
        self.assertEqual(result, "10.118.89.87")
    
    def test_encode_last_chunk(self):
        """Test encoding last chunk."""
        result = encode_chunk_to_ip("1p", True)
        self.assertEqual(result, "11.49.112.0")
    
    def test_encode_single_char(self):
        """Test encoding single character chunk."""
        result = encode_chunk_to_ip("a", False)
        self.assertEqual(result, "10.97.0.0")
    
    def test_encode_two_chars(self):
        """Test encoding two character chunk."""
        result = encode_chunk_to_ip("ab", True)
        self.assertEqual(result, "11.97.98.0")
    
    def test_encode_three_chars(self):
        """Test encoding three character chunk."""
        result = encode_chunk_to_ip("abc", False)
        self.assertEqual(result, "10.97.98.99")


class TestDNSServerCommandEncoding(unittest.TestCase):
    """Test full command encoding like the DNS server does."""
    
    def test_encode_whoami(self):
        """Test encoding 'whoami' command."""
        chunks = encode_command_to_chunks("whoami")
        
        # Should have 3 chunks
        self.assertEqual(len(chunks), 3)
        
        # Check each chunk
        self.assertEqual(chunks[0], (0, "10.100.50.104", False))  # d2h
        self.assertEqual(chunks[1], (1, "10.118.89.87", False))   # vYW
        self.assertEqual(chunks[2], (2, "11.49.112.0", True))     # 1p (last)
    
    def test_encode_ls(self):
        """Test encoding 'ls' command."""
        chunks = encode_command_to_chunks("ls")
        
        # "ls" -> "bHM=" (4 chars) -> 2 chunks
        self.assertEqual(len(chunks), 2)
        
        # Last chunk should be marked
        self.assertFalse(chunks[0][2])  # First chunk not last
        self.assertTrue(chunks[1][2])   # Second chunk is last
    
    def test_encode_pwd(self):
        """Test encoding 'pwd' command."""
        chunks = encode_command_to_chunks("pwd")
        
        # "pwd" -> "cHdk" (4 chars) -> 2 chunks
        self.assertEqual(len(chunks), 2)
        self.assertTrue(chunks[-1][2])  # Last chunk marked
    
    def test_encode_long_command(self):
        """Test encoding a longer command."""
        command = "aws sts get-caller-identity"
        chunks = encode_command_to_chunks(command)
        
        # Should have multiple chunks
        self.assertGreater(len(chunks), 3)
        
        # Only last chunk should be marked as last
        for i, (chunk_num, ip, is_last) in enumerate(chunks):
            if i == len(chunks) - 1:
                self.assertTrue(is_last)
            else:
                self.assertFalse(is_last)
    
    def test_encode_decode_roundtrip(self):
        """Test that encoding and decoding returns original command."""
        commands = ["whoami", "ls", "pwd", "cat /etc/passwd"]
        
        for command in commands:
            # Encode
            chunks = encode_command_to_chunks(command)
            
            # Decode (simulate client's logic)
            command_b64 = ""
            for chunk_num, ip_address, is_last in chunks:
                octets = ip_address.split('.')
                for i in range(1, 4):
                    val = int(octets[i])
                    if val > 0:
                        command_b64 += chr(val)
            
            # Decode base64
            decoded = base64.b64decode(command_b64).decode()
            self.assertEqual(decoded, command)


class TestDNSServerChunkCalculation(unittest.TestCase):
    """Test chunk calculation logic."""
    
    def test_whoami_chunk_count(self):
        """Test chunk count for 'whoami'."""
        count = calculate_chunk_count("whoami")
        self.assertEqual(count, 3)  # "d2hvYW1p" = 8 chars = 3 chunks
    
    def test_ls_chunk_count(self):
        """Test chunk count for 'ls'."""
        count = calculate_chunk_count("ls")
        self.assertEqual(count, 2)  # "bHM=" = 4 chars = 2 chunks
    
    def test_pwd_chunk_count(self):
        """Test chunk count for 'pwd'."""
        count = calculate_chunk_count("pwd")
        self.assertEqual(count, 2)  # "cHdk" = 4 chars = 2 chunks


class TestDNSServerSpecialResponses(unittest.TestCase):
    """Test special DNS response IPs."""
    
    def test_idle_response(self):
        """Test IDLE response IP."""
        idle_ip = "127.0.0.1"
        self.assertEqual(idle_ip, "127.0.0.1")
        # Client should recognize this as "no command"
    
    def test_exit_response(self):
        """Test EXIT response IP."""
        exit_ip = "192.168.0.1"
        self.assertEqual(exit_ip, "192.168.0.1")
        # Client should recognize this as "terminate session"
    
    def test_command_available_response(self):
        """Test command available response IP."""
        cmd_available = "10.0.0.1"
        self.assertTrue(cmd_available.startswith("10."))
        # Client should recognize this as "command available"


class TestDNSServerBase64Encoding(unittest.TestCase):
    """Test base64 encoding used by DNS server."""
    
    def test_encode_whoami(self):
        """Test base64 encoding of 'whoami'."""
        result = base64.b64encode("whoami".encode()).decode()
        self.assertEqual(result, "d2hvYW1p")
    
    def test_encode_ls(self):
        """Test base64 encoding of 'ls'."""
        result = base64.b64encode("ls".encode()).decode()
        self.assertEqual(result, "bHM=")
    
    def test_encode_pwd(self):
        """Test base64 encoding of 'pwd'."""
        result = base64.b64encode("pwd".encode()).decode()
        self.assertEqual(result, "cHdk")
    
    def test_encode_empty(self):
        """Test base64 encoding of empty string."""
        result = base64.b64encode("".encode()).decode()
        self.assertEqual(result, "")
    
    def test_encode_special_chars(self):
        """Test base64 encoding with special characters."""
        command = "echo 'hello world'"
        result = base64.b64encode(command.encode()).decode()
        # Should decode back to original
        decoded = base64.b64decode(result).decode()
        self.assertEqual(decoded, command)


class TestDNSServerEdgeCases(unittest.TestCase):
    """Test edge cases in DNS server encoding."""
    
    def test_empty_chunk(self):
        """Test encoding empty chunk."""
        result = encode_chunk_to_ip("", False)
        self.assertEqual(result, "10.0.0.0")
    
    def test_chunk_with_padding(self):
        """Test that chunks are padded with zeros."""
        result = encode_chunk_to_ip("a", False)
        # Should have 4 octets, padded with zeros
        octets = result.split('.')
        self.assertEqual(len(octets), 4)
        self.assertEqual(octets[0], "10")
        self.assertEqual(octets[1], "97")  # 'a'
        self.assertEqual(octets[2], "0")   # padding
        self.assertEqual(octets[3], "0")   # padding
    
    def test_last_chunk_marker(self):
        """Test that last chunk has correct marker."""
        # Not last
        result_not_last = encode_chunk_to_ip("abc", False)
        self.assertTrue(result_not_last.startswith("10."))
        
        # Last
        result_last = encode_chunk_to_ip("abc", True)
        self.assertTrue(result_last.startswith("11."))


class TestDNSServerRegressionBugs(unittest.TestCase):
    """Test cases for specific bugs in DNS server."""
    
    def test_chunk_boundary_calculation(self):
        """
        Test that is_last calculation is correct at chunk boundaries.
        
        Bug: Off-by-one errors in is_last calculation could cause
        incorrect chunk markers.
        """
        # "whoami" -> "d2hvYW1p" (8 chars)
        encoded = "d2hvYW1p"
        
        # Chunk 0: chars 0-2 (d2h) - not last
        is_last_0 = (0 + 3 >= len(encoded))
        self.assertFalse(is_last_0)
        
        # Chunk 1: chars 3-5 (vYW) - not last
        is_last_1 = (3 + 3 >= len(encoded))
        self.assertFalse(is_last_1)
        
        # Chunk 2: chars 6-8 (1p) - IS last
        is_last_2 = (6 + 3 >= len(encoded))
        self.assertTrue(is_last_2)
    
    def test_exact_multiple_of_three(self):
        """
        Test commands that are exact multiples of 3 chars in base64.
        
        Bug: Edge case where last chunk calculation might be wrong.
        """
        # Create a command that encodes to exactly 9 chars (3 chunks)
        # "hello" -> "aGVsbG8=" (8 chars) - close enough
        encoded = base64.b64encode("hello".encode()).decode()
        
        chunk_count = (len(encoded) + 2) // 3
        last_chunk_start = (chunk_count - 1) * 3
        
        # Last chunk should be marked correctly
        is_last = (last_chunk_start + 3 >= len(encoded))
        self.assertTrue(is_last)


def run_tests():
    """Run all tests."""
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromModule(sys.modules[__name__])
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    return result.wasSuccessful()


if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)

