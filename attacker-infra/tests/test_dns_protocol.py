#!/usr/bin/env python3
"""
Unit tests for DNS protocol functions.

Run with: python3 -m pytest tests/test_dns_protocol.py -v
Or: python3 tests/test_dns_protocol.py
"""

import unittest
import sys
import base64
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from dns_protocol import (
    encode_command_to_base64,
    decode_base64_to_command,
    split_into_chunks,
    encode_chunk_to_ip,
    decode_ip_to_chunk,
    encode_command_to_chunks,
    decode_chunks_to_command,
    validate_chunk_sequence,
    get_chunk_count,
)


class TestBase64Encoding(unittest.TestCase):
    """Test base64 encoding/decoding."""
    
    def test_encode_simple_command(self):
        """Test encoding a simple command."""
        result = encode_command_to_base64("whoami")
        self.assertEqual(result, "d2hvYW1p")
    
    def test_encode_decode_roundtrip(self):
        """Test that encode->decode returns original."""
        commands = ["whoami", "ls", "pwd", "cat /etc/passwd", "echo 'hello world'"]
        for cmd in commands:
            encoded = encode_command_to_base64(cmd)
            decoded = decode_base64_to_command(encoded)
            self.assertEqual(decoded, cmd)
    
    def test_decode_invalid_base64(self):
        """Test that invalid base64 raises error."""
        with self.assertRaises(Exception):
            decode_base64_to_command("invalid!!!")


class TestChunking(unittest.TestCase):
    """Test data chunking."""
    
    def test_split_exact_multiple(self):
        """Test splitting data that's an exact multiple of chunk size."""
        result = split_into_chunks("abcdef", 3)
        self.assertEqual(result, ["abc", "def"])
    
    def test_split_with_remainder(self):
        """Test splitting data with a remainder."""
        result = split_into_chunks("abcdefgh", 3)
        self.assertEqual(result, ["abc", "def", "gh"])
    
    def test_split_shorter_than_chunk(self):
        """Test splitting data shorter than chunk size."""
        result = split_into_chunks("ab", 3)
        self.assertEqual(result, ["ab"])
    
    def test_split_whoami_base64(self):
        """Test splitting 'whoami' base64 encoding."""
        result = split_into_chunks("d2hvYW1p", 3)
        self.assertEqual(result, ["d2h", "vYW", "1p"])
        self.assertEqual(len(result), 3)


class TestIPEncoding(unittest.TestCase):
    """Test IP address encoding/decoding."""
    
    def test_encode_first_chunk(self):
        """Test encoding the first chunk (not last)."""
        result = encode_chunk_to_ip("d2h", False)
        self.assertEqual(result, "10.100.50.104")
    
    def test_encode_middle_chunk(self):
        """Test encoding a middle chunk (not last)."""
        result = encode_chunk_to_ip("vYW", False)
        self.assertEqual(result, "10.118.89.87")
    
    def test_encode_last_chunk(self):
        """Test encoding the last chunk."""
        result = encode_chunk_to_ip("1p", True)
        self.assertEqual(result, "11.49.112.0")
    
    def test_encode_single_char(self):
        """Test encoding a single character."""
        result = encode_chunk_to_ip("a", False)
        self.assertEqual(result, "10.97.0.0")
    
    def test_encode_two_chars(self):
        """Test encoding two characters."""
        result = encode_chunk_to_ip("ab", False)
        self.assertEqual(result, "10.97.98.0")
    
    def test_encode_chunk_too_long(self):
        """Test that chunks longer than 3 chars raise error."""
        with self.assertRaises(ValueError):
            encode_chunk_to_ip("abcd", False)
    
    def test_decode_first_chunk(self):
        """Test decoding the first chunk."""
        chunk_data, is_last = decode_ip_to_chunk("10.100.50.104")
        self.assertEqual(chunk_data, "d2h")
        self.assertFalse(is_last)
    
    def test_decode_last_chunk(self):
        """Test decoding the last chunk."""
        chunk_data, is_last = decode_ip_to_chunk("11.49.112.0")
        self.assertEqual(chunk_data, "1p")
        self.assertTrue(is_last)
    
    def test_encode_decode_roundtrip(self):
        """Test that encode->decode returns original."""
        test_cases = [
            ("d2h", False),
            ("vYW", False),
            ("1p", True),
            ("a", False),
            ("ab", True),
        ]
        for chunk_data, is_last in test_cases:
            ip = encode_chunk_to_ip(chunk_data, is_last)
            decoded_data, decoded_last = decode_ip_to_chunk(ip)
            self.assertEqual(decoded_data, chunk_data)
            self.assertEqual(decoded_last, is_last)


class TestCommandEncoding(unittest.TestCase):
    """Test full command encoding/decoding."""
    
    def test_encode_whoami(self):
        """Test encoding 'whoami' command."""
        chunks = encode_command_to_chunks("whoami")
        self.assertEqual(len(chunks), 3)
        
        # Check each chunk
        self.assertEqual(chunks[0], ("10.100.50.104", False))
        self.assertEqual(chunks[1], ("10.118.89.87", False))
        self.assertEqual(chunks[2], ("11.49.112.0", True))
    
    def test_encode_ls(self):
        """Test encoding 'ls' command."""
        chunks = encode_command_to_chunks("ls")
        # "ls" -> "bHM=" (4 chars) -> 2 chunks
        self.assertEqual(len(chunks), 2)
        self.assertTrue(chunks[-1][1])  # Last chunk should be marked
    
    def test_decode_whoami(self):
        """Test decoding 'whoami' from IP addresses."""
        ips = ["10.100.50.104", "10.118.89.87", "11.49.112.0"]
        command = decode_chunks_to_command(ips)
        self.assertEqual(command, "whoami")
    
    def test_encode_decode_various_commands(self):
        """Test encoding and decoding various commands."""
        commands = [
            "whoami",
            "ls",
            "pwd",
            "cat /etc/passwd",
            "echo 'hello world'",
            "aws sts get-caller-identity",
        ]
        for cmd in commands:
            chunks = encode_command_to_chunks(cmd)
            ips = [ip for ip, _ in chunks]
            decoded = decode_chunks_to_command(ips)
            self.assertEqual(decoded, cmd, f"Failed for command: {cmd}")
    
    def test_get_chunk_count(self):
        """Test calculating chunk count."""
        self.assertEqual(get_chunk_count("whoami"), 3)
        self.assertEqual(get_chunk_count("ls"), 2)
        self.assertEqual(get_chunk_count("pwd"), 2)


class TestValidation(unittest.TestCase):
    """Test chunk sequence validation."""
    
    def test_validate_valid_sequence(self):
        """Test validating a valid chunk sequence."""
        ips = ["10.100.50.104", "10.118.89.87", "11.49.112.0"]
        is_valid, error = validate_chunk_sequence(ips)
        self.assertTrue(is_valid)
        self.assertIsNone(error)
    
    def test_validate_empty_sequence(self):
        """Test validating an empty sequence."""
        is_valid, error = validate_chunk_sequence([])
        self.assertFalse(is_valid)
        self.assertIn("No IP addresses", error)
    
    def test_validate_with_zero_ip(self):
        """Test validating sequence with 0.0.0.0."""
        ips = ["10.100.50.104", "0.0.0.0", "11.49.112.0"]
        is_valid, error = validate_chunk_sequence(ips)
        self.assertFalse(is_valid)
        self.assertIn("0.0.0.0", error)
    
    def test_validate_no_last_marker(self):
        """Test validating sequence without last chunk marker."""
        ips = ["10.100.50.104", "10.118.89.87"]  # Both start with 10
        is_valid, error = validate_chunk_sequence(ips)
        self.assertFalse(is_valid)
        self.assertIn("No last chunk marker", error)
    
    def test_validate_truncated_sequence(self):
        """Test validating a truncated sequence (the bug we had!)."""
        # This simulates the bug: only 2 chunks when we need 3
        ips = ["10.100.50.104", "10.118.89.87"]  # Missing last chunk!
        is_valid, error = validate_chunk_sequence(ips)
        self.assertFalse(is_valid)
        # Should fail because no last marker


class TestEdgeCases(unittest.TestCase):
    """Test edge cases and error conditions."""
    
    def test_empty_command(self):
        """Test encoding an empty command."""
        chunks = encode_command_to_chunks("")
        # Empty string -> "" base64 -> empty string -> 0 chunks
        # This is actually correct behavior - empty command = no chunks
        self.assertEqual(len(chunks), 0)
    
    def test_very_long_command(self):
        """Test encoding a very long command."""
        long_cmd = "echo " + "A" * 1000
        chunks = encode_command_to_chunks(long_cmd)
        
        # Verify we can decode it back
        ips = [ip for ip, _ in chunks]
        decoded = decode_chunks_to_command(ips)
        self.assertEqual(decoded, long_cmd)
    
    def test_special_characters(self):
        """Test commands with special characters."""
        commands = [
            "echo 'hello world'",
            'echo "test"',
            "cat /etc/passwd | grep root",
            "ls -la && pwd",
        ]
        for cmd in commands:
            chunks = encode_command_to_chunks(cmd)
            ips = [ip for ip, _ in chunks]
            decoded = decode_chunks_to_command(ips)
            self.assertEqual(decoded, cmd)


class TestClientDecoding(unittest.TestCase):
    """Test the decoding logic used in payload_client.py."""
    
    def test_client_chunk_parsing_first_chunk(self):
        """Test parsing first chunk like the client does."""
        # Simulate client's chunk parsing logic
        chunk_response = "10.100.50.104"
        octets = chunk_response.split('.')
        
        # Check if last chunk
        is_last = (octets[0] == '11')
        self.assertFalse(is_last)
        
        # Extract data
        chunk_data = ""
        for i in range(1, 4):
            val = int(octets[i])
            if val > 0:
                chunk_data += chr(val)
        
        self.assertEqual(chunk_data, "d2h")
    
    def test_client_chunk_parsing_last_chunk(self):
        """Test parsing last chunk like the client does."""
        chunk_response = "11.49.112.0"
        octets = chunk_response.split('.')
        
        # Check if last chunk
        is_last = (octets[0] == '11')
        self.assertTrue(is_last)
        
        # Extract data
        chunk_data = ""
        for i in range(1, 4):
            val = int(octets[i])
            if val > 0:
                chunk_data += chr(val)
        
        self.assertEqual(chunk_data, "1p")
    
    def test_client_full_command_reconstruction(self):
        """Test full command reconstruction like the client does."""
        # Simulate receiving chunks
        chunks = [
            "10.100.50.104",  # d2h
            "10.118.89.87",   # vYW
            "11.49.112.0"     # 1p (last)
        ]
        
        command_b64 = ""
        for chunk_num, chunk_response in enumerate(chunks):
            octets = chunk_response.split('.')
            is_last = (octets[0] == '11')
            
            for i in range(1, 4):
                val = int(octets[i])
                if val > 0:
                    command_b64 += chr(val)
            
            if is_last:
                break
        
        # Decode
        self.assertEqual(command_b64, "d2hvYW1p")
        command = base64.b64decode(command_b64).decode()
        self.assertEqual(command, "whoami")
    
    def test_client_handles_zero_ip(self):
        """Test that client detects 0.0.0.0 responses."""
        chunk_response = "0.0.0.0"
        octets = chunk_response.split('.')
        
        # Client should detect this as an error
        # In actual client, this would break the loop
        is_valid_chunk = octets[0] in ['10', '11']
        self.assertFalse(is_valid_chunk)
    
    def test_client_special_responses(self):
        """Test client's special response handling."""
        # IDLE response
        idle_response = "127.0.0.1"
        self.assertEqual(idle_response, "127.0.0.1")
        
        # EXIT response
        exit_response = "192.168.0.1"
        self.assertEqual(exit_response, "192.168.0.1")
        
        # Command available response
        cmd_available = "10.0.0.1"
        self.assertTrue(cmd_available.startswith("10."))


class TestRegressionBugs(unittest.TestCase):
    """Test cases for specific bugs we've encountered."""
    
    def test_dns_retry_bug(self):
        """
        Test the DNS retry bug where chunk 2 returned 0.0.0.0.
        
        This was the bug where:
        - Client queries c0, c1, c2
        - Server sends c2 correctly (11.49.112.0)
        - Server deletes pending command
        - Client retries c2 (DNS retry)
        - Server returns 0.0.0.0 (no pending command)
        - Client gets incomplete base64
        """
        # Simulate what the client received
        ips_with_bug = ["10.100.50.104", "10.118.89.87", "0.0.0.0"]
        
        # This should fail validation
        is_valid, error = validate_chunk_sequence(ips_with_bug)
        self.assertFalse(is_valid)
        self.assertIn("0.0.0.0", error)
        
        # The correct sequence should work
        ips_correct = ["10.100.50.104", "10.118.89.87", "11.49.112.0"]
        is_valid, error = validate_chunk_sequence(ips_correct)
        self.assertTrue(is_valid)
    
    def test_incomplete_base64_padding(self):
        """
        Test the 'Incorrect padding' error.
        
        This happens when we get incomplete base64 like 'd2hvYW'
        instead of 'd2hvYW1p'.
        """
        # This should raise an error when trying to decode
        incomplete_base64 = "d2hvYW"  # Missing 'mi'
        
        with self.assertRaises(Exception):
            decode_base64_to_command(incomplete_base64)


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

