"""
Usage: uv run execute_shell.py <command>

Example:
    uv run execute_shell.py "pip list"
"""
from bedrock_agentcore.tools.code_interpreter_client import CodeInterpreter
import argparse
import boto3


def get_interpreter_id(name, region):
    """Look up Code Interpreter ID by name using bedrock-agentcore-control API"""
    try:
        control_client = boto3.client(
            'bedrock-agentcore-control',
            region_name=region,
            endpoint_url=f"https://bedrock-agentcore-control.{region}.amazonaws.com"
        )
        response = control_client.list_code_interpreters()
        for interpreter in response.get('codeInterpreterSummaries', []):
            if interpreter.get('name') == name:
                return interpreter.get('codeInterpreterId')
        return name
    except Exception:
        return name


def print_response(response):
    for event in response["stream"]:
        result = event["result"]
        for content in result["content"]:
            print(content["text"])

def main():
    # https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/code-interpreter-getting-started.html
    parser = argparse.ArgumentParser(description="Execute shell code in AWS Bedrock Code Interpreter")
    parser.add_argument("command", help="Command")
    parser.add_argument("--interpreter-name", default="kmcquade_exfil", help="Interpreter name (default: kmcquade_exfil)")
    parser.add_argument("--region", default="us-east-1", help="AWS region")
    args = parser.parse_args()
    command = args.command
    
    # Lookup the actual interpreter ID
    interpreter_id = get_interpreter_id(args.interpreter_name, args.region)

    code_client = CodeInterpreter(args.region)
    session_id = code_client.start(identifier=interpreter_id)
    response = code_client.invoke("executeCommand", {
        "command": command,
    })
    print_response(response)
    code_client.stop()

if __name__ == '__main__':
    main()
