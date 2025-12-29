# Testing Guide

## Overview

We've implemented comprehensive unit tests for the DNS protocol to catch bugs early and ensure reliability.

## Test Structure

```
tests/
├── __init__.py
├── test_dns_protocol.py       # DNS protocol unit tests (36 tests)
├── test_dns_server.py         # DNS server encoding/decoding tests (27 tests)
├── test_dns_integration.py    # Client/server integration tests
└── mock_dns_server.py         # Mock DNS server for integration testing

src/
├── dns_protocol.py            # Pure functions for DNS encoding/decoding
├── payload_client.py          # Client payload for sandbox
└── attacker_shell.py          # Operator interface

terraform/c2-server/
└── dns_server_with_api.py     # DNS C2 server with HTTP API
```

## Running Tests

### Quick Test
```bash
make test
```

### Verbose Output
```bash
make test-verbose
```

### Direct Execution
```bash
python3 tests/test_dns_protocol.py
```

## Test Coverage

### 1. Base64 Encoding (3 tests)
- ✅ Simple command encoding
- ✅ Encode/decode roundtrip
- ✅ Invalid base64 handling

### 2. Chunking (4 tests)
- ✅ Exact multiples of chunk size
- ✅ Data with remainder
- ✅ Data shorter than chunk size
- ✅ Real 'whoami' base64 splitting

### 3. IP Encoding (10 tests)
- ✅ First chunk encoding
- ✅ Middle chunk encoding
- ✅ Last chunk encoding (with marker)
- ✅ Single/two character chunks
- ✅ Chunk length validation
- ✅ IP decoding
- ✅ Encode/decode roundtrip

### 4. Command Encoding (5 tests)
- ✅ Full 'whoami' encoding
- ✅ Various command encoding
- ✅ Chunk count calculation
- ✅ Complete encode/decode flow

### 5. Validation (5 tests)
- ✅ Valid chunk sequences
- ✅ Empty sequences
- ✅ Sequences with 0.0.0.0
- ✅ Missing last chunk marker
- ✅ Truncated sequences

### 6. Edge Cases (3 tests)
- ✅ Empty commands
- ✅ Very long commands (1000+ chars)
- ✅ Special characters

### 7. Regression Tests (2 tests)
- ✅ **DNS retry bug** (chunk 2 returning 0.0.0.0)
- ✅ **Incorrect padding** error

## Integration Tests

### Overview
Integration tests verify that the DNS protocol works correctly in real client-server scenarios, catching state management bugs that unit tests might miss.

### Test Files
- **`tests/test_dns_integration.py`** - Full integration test suite
- **`tests/mock_dns_server.py`** - MockC2Server simulating DNS server behavior

### Key Integration Tests

1. **test_single_command_flow**
   - Simulates complete flow: client polls, receives command, executes, exfiltrates output
   - Validates encoding/decoding roundtrip through full pipeline

2. **test_multiple_commands**
   - Tests handling of sequential commands
   - Validates state cleanup between commands

3. **test_retry_last_chunk**
   - Reproduces DNS retry bug where last chunk returns 0.0.0.0
   - Validates fix that keeps pending_commands in memory for retries
   - **Important**: This test caught a real production bug!

4. **test_chunking_with_different_sizes**
   - Tests various output sizes (single chunk, multi-chunk, large outputs)
   - Validates chunk assembly and reassembly

### Running Integration Tests

```bash
# Run all tests (unit + integration)
make test

# Run only integration tests
python3 -m unittest tests.test_dns_integration

# Run specific integration test
python3 -m unittest tests.test_dns_integration.TestIntegration.test_retry_last_chunk
```

## Example Test Output

```
test_encode_whoami ... ok
test_decode_whoami ... ok
test_dns_retry_bug ... ok
test_single_command_flow ... ok
test_multiple_commands ... ok
test_retry_last_chunk ... ok
test_validate_with_zero_ip ... ok

----------------------------------------------------------------------
Ran 31 protocol + 27 server + N integration tests in 0.001s

OK
```

## Key Test Cases

### DNS Retry Bug Test

This test specifically validates the bug we encountered:

```python
def test_dns_retry_bug(self):
    """
    Test the DNS retry bug where chunk 2 returned 0.0.0.0.
    """
    # Simulate what the client received
    ips_with_bug = ["10.100.50.104", "10.118.89.87", "0.0.0.0"]
    
    # This should fail validation
    is_valid, error = validate_chunk_sequence(ips_with_bug)
    self.assertFalse(is_valid)
    self.assertIn("0.0.0.0", error)
```

### Incomplete Base64 Test

```python
def test_incomplete_base64_padding(self):
    """
    Test the 'Incorrect padding' error.
    """
    incomplete_base64 = "d2hvYW"  # Missing 'mi'
    
    with self.assertRaises(Exception):
        decode_base64_to_command(incomplete_base64)
```

## Using Test Functions in Code

The `dns_protocol.py` module provides pure functions that can be used anywhere:

```python
from src.dns_protocol import (
    encode_command_to_chunks,
    decode_chunks_to_command,
    validate_chunk_sequence,
)

# Encode a command
chunks = encode_command_to_chunks("whoami")
# [('10.100.50.104', False), ('10.118.89.87', False), ('11.49.112.0', True)]

# Decode chunks
ips = ["10.100.50.104", "10.118.89.87", "11.49.112.0"]
command = decode_chunks_to_command(ips)
# 'whoami'

# Validate a sequence
is_valid, error = validate_chunk_sequence(ips)
# (True, None)
```

## Benefits

✅ **Catch bugs early** - Tests run in milliseconds  
✅ **Prevent regressions** - Specific tests for known bugs  
✅ **Document behavior** - Tests serve as examples  
✅ **Refactor safely** - Change code with confidence  
✅ **Pure functions** - Easy to test, no side effects  

## Adding New Tests

When adding new features or fixing bugs:

1. **Write a failing test first**
   ```python
   def test_new_feature(self):
       """Test description."""
       result = my_new_function(input)
       self.assertEqual(result, expected)
   ```

2. **Implement the feature**

3. **Verify test passes**
   ```bash
   make test
   ```

4. **Add regression test for bugs**
   ```python
   def test_bug_xyz(self):
       """Test for bug #XYZ - describe the bug."""
       # Test that reproduces the bug
       # Assert it's fixed
   ```

## Test Categories

### Unit Tests (Current)
- Test individual functions in isolation
- Fast execution (< 1 second)
- No external dependencies
- Located in `tests/test_dns_protocol.py`

### Integration Tests (Future)
- Test DNS server with real queries
- Test client/server interaction
- Requires running DNS server

### End-to-End Tests (Future)
- Test complete flow with Code Interpreter
- Test with actual AWS services
- Slowest but most comprehensive

## CI/CD Integration

Add to your CI pipeline:

```yaml
# .github/workflows/test.yml
name: Tests
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Set up Python
        uses: actions/setup-python@v2
        with:
          python-version: '3.11'
      - name: Run tests
        run: make test
```

## Test-Driven Development

For new features, follow TDD:

1. **Red** - Write failing test
2. **Green** - Make it pass
3. **Refactor** - Clean up code
4. **Repeat**

Example:
```bash
# 1. Write test
vim tests/test_dns_protocol.py

# 2. Run test (should fail)
make test

# 3. Implement feature
vim src/dns_protocol.py

# 4. Run test (should pass)
make test

# 5. Refactor if needed
# 6. Run test again
make test
```

## Debugging Failed Tests

If a test fails:

1. **Read the error message**
   ```
   AssertionError: 'whoami' != 'whoa'
   ```

2. **Run with verbose output**
   ```bash
   make test-verbose
   ```

3. **Add print statements**
   ```python
   print(f"DEBUG: chunks = {chunks}")
   ```

4. **Run specific test**
   ```bash
   python3 -m unittest tests.test_dns_protocol.TestCommandEncoding.test_encode_whoami
   ```

## Related Documentation

- [DNS_PROTOCOL.md](DNS_PROTOCOL.md) - Protocol specification
- [CLAUDE.md](../CLAUDE.md) - Project overview and architecture

