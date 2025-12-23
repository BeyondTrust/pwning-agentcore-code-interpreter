# Shared utilities for DNS C2 system
from .dns_protocol import (
    encode_command_to_base64,
    decode_base64_to_command,
    encode_chunk_to_ip,
    decode_ip_to_chunk,
    encode_command_to_chunks,
    decode_chunks_to_command,
    make_dns_safe,
    unmake_dns_safe,
)

__all__ = [
    'encode_command_to_base64',
    'decode_base64_to_command',
    'encode_chunk_to_ip',
    'decode_ip_to_chunk',
    'encode_command_to_chunks',
    'decode_chunks_to_command',
    'make_dns_safe',
    'unmake_dns_safe',
]
