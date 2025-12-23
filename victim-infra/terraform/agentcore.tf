# AWS Bedrock AgentCore Code Interpreter
# This creates the Code Interpreter that will be exploited via prompt injection

resource "aws_bedrockagentcore_code_interpreter" "main" {
  name               = "${var.project_name}-interpreter-${random_id.suffix.hex}"
  execution_role_arn = aws_iam_role.code_interpreter.arn

  # VULNERABILITY: SANDBOX mode does NOT properly isolate DNS
  # This allows data exfiltration via DNS queries
  network_configuration {
    network_mode = "SANDBOX"
  }

  tags = merge(var.tags, {
    Name    = "${var.project_name}-code-interpreter"
    Warning = "SANDBOX-MODE-DNS-VULNERABLE"
  })
}
