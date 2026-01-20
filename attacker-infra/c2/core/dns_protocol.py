"""DNS Protocol Functions - Pure functions for encoding/decoding DNS C2 protocol."""

import base64
from typing import List, Optional, Tuple


def encode_command_to_base64(command: str) -> str:
    """Encode a command to base64."""
    return base64.b64encode(command.encode()).decode()


def decode_base64_to_command(encoded: str) -> str:
    """Decode a base64 string to a command."""
    return base64.b64decode(encoded).decode()


def split_into_chunks(data: str, chunk_size: int = 3) -> List[str]:
    """Split data into fixed-size chunks."""
    return [data[i : i + chunk_size] for i in range(0, len(data), chunk_size)]


def encode_chunk_to_ip(chunk_data: str, is_last: bool) -> str:
    """
    Encode a chunk of base64 data into an IP address.

    Protocol:
    - First octet: 10 (more chunks) or 11 (last chunk)
    - Octets 2-4: ASCII values of up to 3 characters
    - Pad with 0 if less than 3 characters
    """
    if len(chunk_data) > 3:
        raise ValueError(f"Chunk data too long: {len(chunk_data)} chars (max 3)")

    first_octet = "11" if is_last else "10"
    octets = [first_octet]

    for char in chunk_data:
        octets.append(str(ord(char)))

    while len(octets) < 4:
        octets.append("0")

    return ".".join(octets)


def decode_ip_to_chunk(ip_address: str) -> Tuple[str, bool]:
    """Decode an IP address back to chunk data."""
    octets = ip_address.split(".")

    if len(octets) != 4:
        raise ValueError(f"Invalid IP address: {ip_address}")

    is_last = octets[0] == "11"
    chunk_data = ""

    for octet_str in octets[1:]:
        octet_val = int(octet_str)
        if octet_val > 0:
            chunk_data += chr(octet_val)

    return chunk_data, is_last


def encode_command_to_chunks(command: str) -> List[Tuple[str, bool]]:
    """Encode a complete command into IP address chunks."""
    encoded = encode_command_to_base64(command)
    chunks = split_into_chunks(encoded, 3)

    result = []
    for i, chunk in enumerate(chunks):
        is_last = i == len(chunks) - 1
        ip = encode_chunk_to_ip(chunk, is_last)
        result.append((ip, is_last))

    return result


def decode_chunks_to_command(ip_addresses: List[str]) -> str:
    """Decode a list of IP addresses back to the original command."""
    chunks = []
    for ip in ip_addresses:
        chunk_data, is_last = decode_ip_to_chunk(ip)
        chunks.append(chunk_data)
        if is_last:
            break

    encoded = "".join(chunks)
    return decode_base64_to_command(encoded)


def validate_chunk_sequence(ip_addresses: List[str]) -> Tuple[bool, Optional[str]]:
    """Validate that a sequence of IP addresses forms a valid command."""
    if not ip_addresses:
        return False, "No IP addresses provided"

    found_last = False
    for i, ip in enumerate(ip_addresses):
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

    try:
        decode_chunks_to_command(ip_addresses)
        return True, None
    except Exception as e:
        return False, f"Command decode error: {e}"


def get_chunk_count(command: str) -> int:
    """Calculate how many chunks a command will need."""
    encoded = encode_command_to_base64(command)
    return len(split_into_chunks(encoded, 3))
