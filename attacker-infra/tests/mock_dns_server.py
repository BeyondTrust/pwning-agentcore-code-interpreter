#!/usr/bin/env python3
"""
Mock DNS C2 Server for integration testing.

Replicates the actual dns_server_with_api.py behavior without needing EC2.
Used to test client/server interactions, retries, and state management.
"""

import sys
import base64
from pathlib import Path

# Add terraform/c2-server to path to import DNS server helper functions
sys.path.insert(0, str(Path(__file__).parent.parent / 'terraform' / 'c2-server'))

from dns_server_with_api import encode_chunk_to_ip


class MockC2Server:
    """
    Mock DNS C2 Server that simulates actual server behavior.
    
    Used for integration testing to verify:
    - Client/server interaction
    - DNS retry handling
    - State management
    - Multiple session handling
    """
    
    def __init__(self):
        """Initialize mock server state."""
        self.pending_commands = {}      # {session_id: encoded_command}
        self.completed_commands = set() # Sessions where last chunk was sent
        self.poll_count = {}             # Track polls per session
    
    def queue_command(self, command, session_id="*"):
        """
        Queue a command for a session.
        
        Args:
            command: Shell command to queue
            session_id: Session to queue for (default "*" = all sessions)
        """
        # Encode to base64 just like real server
        encoded = base64.b64encode(command.encode()).decode()
        self.pending_commands[session_id] = encoded
        
        # Reset completion tracking for new command
        if session_id in self.completed_commands:
            self.completed_commands.remove(session_id)
        
        return encoded
    
    def query_chunk(self, session_id, chunk_num):
        """
        Simulate client querying for a chunk.
        
        Returns IP address response:
        - 10.X.Y.Z = chunk data (more chunks coming)
        - 11.X.Y.Z = chunk data (last chunk)
        - 0.0.0.0 = no data / session terminated
        
        Args:
            session_id: Session ID making the query
            chunk_num: Chunk number requested (0, 1, 2, ...)
        
        Returns:
            IP address string
        """
        # Track polls
        if session_id not in self.poll_count:
            self.poll_count[session_id] = 0
        self.poll_count[session_id] += 1
        
        # Try to get command for this session
        encoded = self.pending_commands.get(session_id)
        
        # If no session-specific command, try wildcard
        if not encoded and "*" in self.pending_commands:
            encoded = self.pending_commands["*"]
        
        if not encoded:
            # No command available
            return "0.0.0.0"
        
        # Calculate chunk data
        start_idx = chunk_num * 3
        chunk_data = encoded[start_idx:start_idx + 3]
        
        if not chunk_data:
            # No more chunks
            return "0.0.0.0"
        
        # Check if this is last chunk
        is_last = (start_idx + 3 >= len(encoded))
        
        # Encode to IP using actual server function
        ip_address = encode_chunk_to_ip(chunk_data, is_last)
        
        # Track completion
        if is_last:
            self.completed_commands.add(session_id)
            # ✅ THE FIX: DON'T delete pending command after last chunk
            # Keep it in memory so retries can still get the chunk
            # Only delete when a NEW command is queued (in queue_command method)
        
        return ip_address
    
    def decode_chunk(self, ip_address):
        """
        Decode an IP address back to chunk data.
        
        This simulates what the client does.
        
        Args:
            ip_address: IP address from server response
        
        Returns:
            Tuple of (chunk_data, is_last)
        """
        octets = ip_address.split('.')
        
        if len(octets) != 4:
            return None, False
        
        # Check if last chunk
        is_last = (octets[0] == '11')
        
        # Decode octets to characters
        chunk_data = ""
        for i in range(1, 4):
            val = int(octets[i])
            if val > 0:
                chunk_data += chr(val)
        
        return chunk_data, is_last
    
    def get_command_from_chunks(self, session_id, max_chunks=50):
        """
        Simulate client fetching a complete command.
        
        This replicates the actual client behavior: poll chunks until
        getting the last marker, then decode the base64.
        
        Args:
            session_id: Session to fetch for
            max_chunks: Maximum chunks to try (matches client limit)
        
        Returns:
            Tuple of (decoded_command, chunks_received, got_complete)
        """
        command_b64 = ""
        chunks_received = []
        
        for chunk_num in range(max_chunks):
            # Query for chunk
            response = self.query_chunk(session_id, chunk_num)
            chunks_received.append(response)
            
            # Decode chunk
            chunk_data, is_last = self.decode_chunk(response)
            
            if not chunk_data and response == "0.0.0.0":
                # Hit 0.0.0.0, can't get more chunks
                break
            
            # Add to command
            command_b64 += chunk_data
            
            if is_last:
                # Got last chunk, stop
                break
        
        # Try to decode
        try:
            if command_b64:
                command = base64.b64decode(command_b64).decode()
                return command, chunks_received, True
            else:
                return None, chunks_received, False
        except Exception as e:
            # Base64 decode failed (incomplete command)
            return None, chunks_received, False
    
    def get_state(self):
        """
        Get current server state for debugging.
        
        Returns:
            Dict with pending commands and poll counts
        """
        return {
            "pending_commands": self.pending_commands,
            "completed_commands": list(self.completed_commands),
            "poll_counts": self.poll_count,
        }


if __name__ == "__main__":
    # Quick test
    print("Testing MockC2Server...")
    
    server = MockC2Server()
    server.queue_command("whoami")
    
    # Get chunks
    command, chunks, success = server.get_command_from_chunks("test_session")
    
    print(f"Command: {command}")
    print(f"Chunks: {chunks}")
    print(f"Success: {success}")
    print(f"State: {server.get_state()}")
    
    assert command == "whoami", f"Expected 'whoami', got '{command}'"
    assert success, "Failed to get complete command"
    print("\n✅ MockC2Server working correctly!")
