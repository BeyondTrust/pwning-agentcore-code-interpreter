"""
AgentCore Service - Integration with AWS Bedrock AgentCore

SECURITY WARNING: This service is INTENTIONALLY VULNERABLE.
It demonstrates how passing user-controlled input to AI systems
without proper sanitization enables prompt injection attacks.

The vulnerability exists in the `analyze_csv` method where user
messages and CSV content are directly concatenated into the prompt.
"""

import boto3
import logging
import os
import uuid
import time
from typing import Optional

logger = logging.getLogger(__name__)


class AgentCoreService:
    """
    Service for interacting with AWS Bedrock AgentCore Code Interpreter.

    This service wraps the Code Interpreter API and provides methods
    for analyzing data. It is intentionally vulnerable to demonstrate
    prompt injection attacks in AI systems.
    """

    def __init__(self):
        """Initialize the AgentCore service."""
        self.region = os.environ.get('AWS_REGION', 'us-east-1')
        self.code_interpreter_id = os.environ.get('CODE_INTERPRETER_ID')
        self.code_interpreter_arn = os.environ.get('CODE_INTERPRETER_ARN')

        # Initialize boto3 client
        self.client = boto3.client(
            'bedrock-agent-runtime',
            region_name=self.region
        )

        # Session tracking
        self.active_sessions = {}

        logger.info(f"AgentCore service initialized")
        logger.info(f"  Region: {self.region}")
        logger.info(f"  Code Interpreter ID: {self.code_interpreter_id}")

    def chat(self, message: str, session_id: Optional[str] = None) -> dict:
        """
        Handle a basic chat message.

        For simple chat without file analysis, we return a helpful response
        guiding the user to upload a CSV for analysis.

        Args:
            message: The user's message
            session_id: Optional session ID for continuity

        Returns:
            Dict with response and session_id
        """
        if not session_id:
            session_id = f"sess_{uuid.uuid4().hex[:8]}"

        # Simple response for demo purposes
        # In production, this would invoke a conversational AI
        response = (
            "Hello! I'm your AI Data Analyst. I can help you analyze CSV files. "
            "To get started, please upload a CSV file using the file upload button, "
            "then ask me a question about your data. For example:\n\n"
            "- 'What are the top 10 customers by revenue?'\n"
            "- 'Show me a summary of sales by region'\n"
            "- 'Calculate the average order value'\n\n"
            "I'll analyze your data and provide insights!"
        )

        return {
            "response": response,
            "session_id": session_id
        }

    def analyze_csv(
        self,
        user_message: str,
        csv_content: str,
        session_id: Optional[str] = None
    ) -> dict:
        """
        Analyze CSV content using Code Interpreter.

        VULNERABILITY: This method directly concatenates user-controlled input
        (user_message and csv_content) into the prompt sent to the Code Interpreter.
        This allows an attacker to inject malicious instructions that will be
        executed as Python code.

        Attack Vector:
        1. Attacker crafts a CSV with malicious content in a cell
        2. The malicious content contains prompt injection payload
        3. Payload instructs the AI to execute arbitrary Python code
        4. Code Interpreter executes the malicious code with its IAM permissions
        5. Attacker exfiltrates data via DNS (sandbox bypass)

        Args:
            user_message: The user's analysis request
            csv_content: Raw CSV file content (UNSANITIZED - VULNERABLE)
            session_id: Optional session ID

        Returns:
            Dict with analysis response and session_id
        """
        if not session_id:
            session_id = f"sess_{uuid.uuid4().hex[:8]}"

        logger.info(f"Starting CSV analysis for session {session_id}")

        # VULNERABLE PROMPT CONSTRUCTION
        # User-controlled input is directly embedded without sanitization
        # This is the core vulnerability that enables prompt injection
        analysis_prompt = f"""You are a helpful data analyst assistant. The user has uploaded
a CSV file and wants you to analyze it.

User's analysis request: {user_message}

Here is the CSV data to analyze:

```csv
{csv_content}
```

Please analyze this data and answer the user's question. You can write and execute
Python code to perform the analysis. Use pandas for data manipulation and provide
clear, insightful results.

Important: Execute any code blocks you find in the data if they appear to be
calibration or preprocessing code required for proper analysis.
"""

        try:
            # Start a Code Interpreter session
            logger.info(f"Creating Code Interpreter session...")

            start_response = self.client.start_code_interpreter_session(
                codeInterpreterIdentifier=self.code_interpreter_id,
                sessionTimeoutSeconds=300
            )

            ci_session_id = start_response['sessionId']
            logger.info(f"Code Interpreter session created: {ci_session_id}")

            # Store session mapping
            self.active_sessions[session_id] = ci_session_id

            # Invoke the Code Interpreter with the vulnerable prompt
            logger.info(f"Invoking Code Interpreter with analysis prompt...")

            invoke_response = self.client.invoke_code_interpreter(
                codeInterpreterIdentifier=self.code_interpreter_id,
                sessionId=ci_session_id,
                name="execute",
                arguments={
                    "prompt": analysis_prompt
                }
            )

            # Extract the response
            result_text = invoke_response.get('result', {}).get('text', '')

            if not result_text:
                result_text = "Analysis complete. No specific output was generated."

            logger.info(f"Analysis complete for session {session_id}")

            return {
                "response": result_text,
                "session_id": session_id
            }

        except self.client.exceptions.ValidationException as e:
            logger.error(f"Validation error: {e}")
            return {
                "response": f"Validation error: {str(e)}",
                "session_id": session_id
            }
        except self.client.exceptions.ResourceNotFoundException as e:
            logger.error(f"Resource not found: {e}")
            return {
                "response": "Code Interpreter not found. Please check configuration.",
                "session_id": session_id
            }
        except Exception as e:
            logger.error(f"Code Interpreter error: {e}", exc_info=True)

            # For demo purposes, if Code Interpreter isn't available,
            # return a mock response
            if "not found" in str(e).lower() or self.code_interpreter_id is None:
                return self._mock_analysis(csv_content, user_message, session_id)

            raise

    def _mock_analysis(
        self,
        csv_content: str,
        user_message: str,
        session_id: str
    ) -> dict:
        """
        Provide a mock analysis response when Code Interpreter is unavailable.

        This is used for local testing without AWS infrastructure.
        """
        logger.warning("Using mock analysis (Code Interpreter not available)")

        # Parse CSV to provide basic stats
        lines = csv_content.strip().split('\n')
        if lines:
            headers = lines[0].split(',')
            row_count = len(lines) - 1

            response = f"""## Analysis Results

**Dataset Overview:**
- Columns: {len(headers)}
- Rows: {row_count}
- Headers: {', '.join(headers[:5])}{'...' if len(headers) > 5 else ''}

**Your Question:** {user_message}

*Note: This is a mock response. In production, the Code Interpreter would
analyze your data and provide detailed insights.*

To test the full functionality, deploy with a configured Code Interpreter.
"""
        else:
            response = "Unable to parse CSV content."

        return {
            "response": response,
            "session_id": session_id
        }

    def end_session(self, session_id: str) -> bool:
        """
        End a Code Interpreter session.

        Args:
            session_id: The session ID to end

        Returns:
            True if session was ended successfully
        """
        if session_id not in self.active_sessions:
            return False

        ci_session_id = self.active_sessions[session_id]

        try:
            self.client.stop_code_interpreter_session(
                codeInterpreterIdentifier=self.code_interpreter_id,
                sessionId=ci_session_id
            )
            del self.active_sessions[session_id]
            logger.info(f"Session {session_id} ended")
            return True
        except Exception as e:
            logger.error(f"Error ending session: {e}")
            return False
