"""
AgentCore Service - Integration with AWS Bedrock AgentCore

Wraps a Bedrock LLM (with code execution tool) around the AgentCore
Code Interpreter. The `analyze_csv` method passes raw CSV content into
the LLM prompt without sanitization, which makes it susceptible to
prompt injection — an attacker can embed instructions in CSV cells that
trick the model into executing arbitrary code.
"""

import boto3
import boto3.session
import logging
import time
import uuid
from typing import Optional

from botocore.config import Config as BotoConfig

from app.config import get_settings

logger = logging.getLogger(__name__)

# Tool definition for Python code execution
PYTHON_TOOL = {
    "toolSpec": {
        "name": "execute_python",
        "description": (
            "Execute Python code for data analysis. Use this to read files, "
            "run computations, create visualizations, or perform any Python operations."
        ),
        "inputSchema": {
            "json": {
                "type": "object",
                "properties": {
                    "code": {
                        "type": "string",
                        "description": "Python code to execute",
                    }
                },
                "required": ["code"],
            }
        },
    }
}

MAX_TOOL_ITERATIONS = 3

# Shared config for all boto3 clients
_BOTO_CONFIG = BotoConfig(read_timeout=600)


class AgentCoreService:
    """Service for interacting with AWS Bedrock AgentCore Code Interpreter."""

    def __init__(self):
        """Initialize the AgentCore service."""
        settings = get_settings()
        self.region = settings.aws_region
        self.model_id = settings.model_id
        self.code_interpreter_id = settings.code_interpreter_id
        self.code_interpreter_arn = settings.code_interpreter_arn
        self.active_sessions = {}

        logger.info("AgentCore service initialized")
        logger.info(f"  Region: {self.region}")
        logger.info(f"  Model: {self.model_id}")
        logger.info(f"  Code Interpreter ID: {self.code_interpreter_id}")

    def _make_clients(self):
        """Create a fresh boto3 session and clients for this thread.

        boto3 clients created from the default session are not safe to share
        across threads — concurrent calls can corrupt the underlying SSL
        connection pool and cause response ordering issues.  Each background
        task therefore gets its own session + clients.
        """
        session = boto3.session.Session()
        agentcore = session.client(
            "bedrock-agentcore",
            region_name=self.region,
            endpoint_url=f"https://bedrock-agentcore.{self.region}.amazonaws.com",
            config=_BOTO_CONFIG,
        )
        bedrock_runtime = session.client(
            "bedrock-runtime",
            region_name=self.region,
            config=_BOTO_CONFIG,
        )
        return agentcore, bedrock_runtime

    def chat(self, message: str, session_id: Optional[str] = None) -> dict:
        """Handle a basic chat message."""
        if not session_id:
            session_id = f"sess_{uuid.uuid4().hex[:8]}"

        response = (
            "Hello! I'm your AI Data Analyst. I can help you analyze CSV files. "
            "To get started, please upload a CSV file using the file upload button, "
            "then ask me a question about your data. For example:\n\n"
            "- 'What are the top 10 customers by revenue?'\n"
            "- 'Show me a summary of sales by region'\n"
            "- 'Calculate the average order value'\n\n"
            "I'll analyze your data and provide insights!"
        )

        return {"response": response, "session_id": session_id}

    def analyze_csv(
        self,
        user_message: str,
        csv_content: str,
        session_id: Optional[str] = None,
    ) -> dict:
        """
        Analyze CSV content using an LLM with a Code Interpreter tool.

        The raw csv_content is embedded in the LLM prompt without sanitization.
        If an attacker controls the CSV content (e.g. via file upload), they can
        embed prompt injection that tricks the model into running arbitrary code
        inside the Code Interpreter sandbox.
        """
        if not session_id:
            session_id = f"sess_{uuid.uuid4().hex[:8]}"

        logger.info(f"[{session_id}] Starting CSV analysis ({len(csv_content)} bytes)")

        # Create per-request clients to avoid threading issues with shared
        # boto3 sessions (concurrent BackgroundTasks corrupt connection pools)
        agentcore, bedrock_runtime = self._make_clients()
        logger.info(f"[{session_id}] Created per-request boto3 clients")

        try:
            # Step 1: Start a Code Interpreter session
            logger.info(f"[{session_id}] >> start_code_interpreter_session()")
            t0 = time.monotonic()
            start_resp = agentcore.start_code_interpreter_session(
                codeInterpreterIdentifier=self.code_interpreter_id,
                name=f"session-{session_id}",
                sessionTimeoutSeconds=3600,
            )
            ci_session_id = start_resp["sessionId"]
            self.active_sessions[session_id] = ci_session_id
            logger.info(
                f"[{session_id}] << start_code_interpreter_session() "
                f"-> {ci_session_id} ({time.monotonic() - t0:.1f}s)"
            )

            # Step 2: Write CSV to sandbox
            logger.info(f"[{session_id}] >> invoke(writeFiles, {len(csv_content)} bytes)")
            t0 = time.monotonic()
            agentcore.invoke_code_interpreter(
                codeInterpreterIdentifier=self.code_interpreter_id,
                sessionId=ci_session_id,
                name="writeFiles",
                arguments={
                    "content": [{"path": "data.csv", "text": csv_content}]
                },
            )
            logger.info(
                f"[{session_id}] << invoke(writeFiles) ({time.monotonic() - t0:.1f}s)"
            )

            # Step 3: Build analysis prompt — CSV is on disk, not inlined
            prompt = (
                f"You are a data analyst. The user uploaded a CSV file "
                f"saved at data.csv. Follow the user's instructions.\n\n"
                f"User's instructions: {user_message}"
            )

            # Step 4: LLM agentic loop
            messages = [{"role": "user", "content": [{"text": prompt}]}]
            logger.info(
                f"[{session_id}] Entering LLM loop (model={self.model_id}, "
                f"prompt={len(prompt)} chars)"
            )

            for iteration in range(MAX_TOOL_ITERATIONS):
                logger.info(
                    f"[{session_id}] >> converse() iteration {iteration + 1}"
                )
                t0 = time.monotonic()
                response = bedrock_runtime.converse(
                    modelId=self.model_id,
                    messages=messages,
                    toolConfig={"tools": [PYTHON_TOOL]},
                )
                elapsed = time.monotonic() - t0

                stop_reason = response["stopReason"]
                assistant_msg = response["output"]["message"]
                messages.append(assistant_msg)
                logger.info(
                    f"[{session_id}] << converse() stopReason={stop_reason} "
                    f"({elapsed:.1f}s)"
                )

                if stop_reason != "tool_use":
                    # Model finished — extract text response
                    text_parts = [
                        block["text"]
                        for block in assistant_msg["content"]
                        if "text" in block
                    ]
                    logger.info(
                        f"[{session_id}] Analysis complete "
                        f"({len(text_parts)} text blocks)"
                    )
                    return {
                        "response": "\n".join(text_parts) or "Analysis complete.",
                        "session_id": session_id,
                    }

                # Model wants to execute code — run it in Code Interpreter
                tool_results = []
                for block in assistant_msg["content"]:
                    if "toolUse" not in block:
                        continue

                    tool_use = block["toolUse"]
                    code = tool_use["input"].get("code", "")
                    if not code:
                        continue
                    logger.info(
                        f"[{session_id}] >> executeCode (iteration {iteration + 1}, "
                        f"{len(code)} chars): {code[:200]}..."
                    )

                    try:
                        t0 = time.monotonic()
                        exec_resp = agentcore.invoke_code_interpreter(
                            codeInterpreterIdentifier=self.code_interpreter_id,
                            sessionId=ci_session_id,
                            name="executeCode",
                            arguments={"code": code, "language": "python"},
                        )
                        output = self._read_exec_output(exec_resp)
                        logger.info(
                            f"[{session_id}] << executeCode ({time.monotonic() - t0:.1f}s, "
                            f"{len(output)} chars): {output[:2000]}"
                        )
                    except Exception as e:
                        logger.error(
                            f"[{session_id}] !! executeCode failed: {e}",
                            exc_info=True,
                        )
                        output = f"Error: {e}"

                    tool_results.append(
                        {
                            "toolResult": {
                                "toolUseId": tool_use["toolUseId"],
                                "content": [{"text": output or "(no output)"}],
                            }
                        }
                    )

                messages.append({"role": "user", "content": tool_results})

            logger.info(f"[{session_id}] Hit max iterations ({MAX_TOOL_ITERATIONS})")
            return {
                "response": "Analysis reached maximum iterations.",
                "session_id": session_id,
            }

        except Exception as e:
            logger.error(f"Analysis error: {e}", exc_info=True)

            # Fall back to mock analysis for local testing
            if self.code_interpreter_id is None:
                return self._mock_analysis(csv_content, user_message, session_id)

            return {
                "response": f"Analysis failed: {e}",
                "session_id": session_id,
            }

    @staticmethod
    def _read_exec_output(exec_resp: dict) -> str:
        """Read execution output from an invoke_code_interpreter response.

        The API returns an EventStream under the ``stream`` key.  We consume
        every event and concatenate any text we find.  If for some reason
        ``stream`` is absent, fall back to looking for ``result``.
        """

        def _extract_text(obj):
            """Recursively extract text from nested response structures."""
            if isinstance(obj, str):
                return obj
            if isinstance(obj, list):
                # List of content blocks: [{"type": "text", "text": "..."}]
                texts = []
                for item in obj:
                    extracted = _extract_text(item)
                    if extracted:
                        texts.append(extracted)
                return "\n".join(texts)
            if isinstance(obj, dict):
                # Content block: {"type": "text", "text": "..."}
                if "text" in obj:
                    return obj["text"]
                # Wrapper: {"content": [...]} or {"output": "..."}
                for key in ("content", "output", "text", "stdout", "result"):
                    if key in obj:
                        extracted = _extract_text(obj[key])
                        if extracted:
                            return extracted
            return ""

        # Primary path: consume the EventStream
        stream = exec_resp.get("stream")
        if stream is not None:
            parts = []
            try:
                for event in stream:
                    for _key, value in event.items():
                        text = _extract_text(value)
                        if text:
                            parts.append(text)
            except Exception as e:
                logger.warning(f"Error reading execution stream: {e}")
            if parts:
                return "\n".join(parts)

        # Fallback: plain dict response
        result = exec_resp.get("result", {})
        text = _extract_text(result)
        return text or "(no output)"

    def _mock_analysis(
        self, csv_content: str, user_message: str, session_id: str
    ) -> dict:
        """Mock analysis response when Code Interpreter is unavailable."""
        logger.warning("Using mock analysis (Code Interpreter not available)")

        lines = csv_content.strip().split("\n")
        if lines:
            headers = lines[0].split(",")
            row_count = len(lines) - 1
            response = (
                f"## Analysis Results\n\n"
                f"**Dataset Overview:**\n"
                f"- Columns: {len(headers)}\n"
                f"- Rows: {row_count}\n"
                f"- Headers: {', '.join(headers[:5])}{'...' if len(headers) > 5 else ''}\n\n"
                f"**Your Question:** {user_message}\n\n"
                f"*Note: Mock response. Deploy with Code Interpreter for full analysis.*"
            )
        else:
            response = "Unable to parse CSV content."

        return {"response": response, "session_id": session_id}

    def end_session(self, session_id: str) -> bool:
        """End a Code Interpreter session."""
        if session_id not in self.active_sessions:
            return False

        ci_session_id = self.active_sessions[session_id]

        try:
            agentcore, _ = self._make_clients()
            agentcore.end_code_interpreter_session(
                codeInterpreterIdentifier=self.code_interpreter_id,
                sessionId=ci_session_id,
            )
            del self.active_sessions[session_id]
            logger.info(f"Session {session_id} ended")
            return True
        except Exception as e:
            logger.error(f"Error ending session: {e}")
            return False
