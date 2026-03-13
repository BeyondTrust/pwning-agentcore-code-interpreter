"""
Usage: uv run execute_shell.py <command>

Example:
    uv run execute_shell.py "pip list"
"""
from bedrock_agentcore.tools.code_interpreter_client import CodeInterpreter
import argparse


def print_response(response):
    for event in response["stream"]:
        result = event["result"]
        for content in result["content"]:
            print(content["text"])

def main():
    # https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/code-interpreter-getting-started.html
    parser = argparse.ArgumentParser(description="Execute shell code in AWS Bedrock Code Interpreter")
    parser.add_argument("command", help="Command")
    parser.add_argument("--interpreter-id", default="aws.codeinterpreter.v1")
    args = parser.parse_args()
    command = args.command
    interpreter_id = args.interpreter_id

    code_client = CodeInterpreter('us-east-1')
    session_id = code_client.start(identifier=interpreter_id)
    response = code_client.invoke("executeCommand", {
        "command": command,
    })
    print_response(response)
    code_client.stop()

if __name__ == '__main__':
    main()
