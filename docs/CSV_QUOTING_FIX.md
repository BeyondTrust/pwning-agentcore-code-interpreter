# CSV Quoting Fix: RFC 4180 Double-Quote Escaping Bug

## Summary

The CSV payload generator produced invalid Python code due to `csv.QUOTE_ALL` double-quoting fields that already contained quotes. The fix was switching the prompt injection text to use single quotes instead of double quotes.

## The Bug

`csv.QUOTE_ALL` wraps every field in double quotes per RFC 4180. When a field **already contains** double quotes, the CSV writer escapes them by doubling: `"` becomes `""`.

### Before (broken)

The injection text contained a base64 decode call with double-quoted string arguments. After `csv.QUOTE_ALL` processing, those double quotes got doubled — turning valid Python into a syntax error. `""value""` is parsed as an empty string concatenated with an identifier, not a quoted string.

### After (fixed)

The injection text uses single-quoted string arguments. Single quotes pass through the CSV writer untouched since RFC 4180 only escapes double quotes.

## Why This Was Subtle

1. **The benchmark masked it.** The prompt injection benchmark (`benchmark_injection.py`) tested whether the LLM would *attempt* code — not whether the code was syntactically valid. A high injection success rate gave false confidence.

2. **The error was invisible.** The Code Interpreter sandbox swallows Python syntax errors silently. The payload just didn't run. No error was exfiltrated because the payload never started.

3. **Manual testing skipped the CSV path.** When testing the C2 channel directly (pasting payload into the interpreter), single quotes were already used. The bug only appeared when the payload went through `csv.writer`.

## The Fix

In `create_injection_text()` (`attacker-infra/c2/core/payload_generator.py`), the base64 string is wrapped in single quotes instead of double quotes. This is safe because base64 output never contains single quotes (only `A-Za-z0-9+/=`).

## Lesson

When embedding code inside CSV cells, always consider the quoting layer. RFC 4180 only escapes double quotes — single quotes, backticks, and other delimiters pass through unchanged.
