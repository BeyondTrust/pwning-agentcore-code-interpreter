# Note: IAM role for Bedrock Code Interpreter is defined in iam.tf
# with realistic misconfiguration (AWS managed policies from starter toolkit)

# Bedrock AgentCore Code Interpreter
resource "aws_bedrockagentcore_code_interpreter" "main" {
  name               = "kmcquade_exfil"
  description        = "Code interpreter for DNS exfiltration demo"
  execution_role_arn = aws_iam_role.bedrock_code_interpreter.arn

  network_configuration {
    network_mode = "SANDBOX"
  }

  tags = var.tags
}
