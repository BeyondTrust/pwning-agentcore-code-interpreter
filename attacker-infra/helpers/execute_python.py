import boto3
import argparse


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


def main():
    # https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/code-interpreter-getting-started.html
    parser = argparse.ArgumentParser(description="Execute Python code in AWS Bedrock Code Interpreter")
    parser.add_argument("--file", help="Path to Python file to execute")
    parser.add_argument("--interpreter-name", default="kmcquade_exfil", help="Interpreter name (default: kmcquade_exfil)")
    parser.add_argument("--region", default="us-east-1", help="AWS region")
    args = parser.parse_args()
    target_file = args.file
    
    # Lookup the actual interpreter ID
    code_interpreter_id = get_interpreter_id(args.interpreter_name, args.region)
    # Custom one:  code_interpreter_public-NwCV96rKZ

    with open(target_file, "r", encoding="utf-8") as f:
        code_to_execute = f.read()

    client = boto3.client("bedrock-agentcore", region_name=args.region,
                          endpoint_url=f"https://bedrock-agentcore.{args.region}.amazonaws.com")

    session_id = client.start_code_interpreter_session(
        codeInterpreterIdentifier=code_interpreter_id,
        name="my-code-session",
        sessionTimeoutSeconds=900
    )["sessionId"]

    execute_response = client.invoke_code_interpreter(
        codeInterpreterIdentifier=code_interpreter_id,
        sessionId=session_id,
        name="executeCode",
        arguments={
            "language": "python",
            "code": code_to_execute
        }
    )

    # Extract and print the text output from the stream
    for event in execute_response['stream']:
        if 'result' in event:
            result = event['result']
            if 'content' in result:
                for content_item in result['content']:
                    if content_item['type'] == 'text':
                        print(content_item['text'])

    # Don't forget to stop the session when you're done
    client.stop_code_interpreter_session(
        codeInterpreterIdentifier=code_interpreter_id,
        sessionId=session_id
    )


if __name__ == "__main__":
    main()
