#!/bin/bash
# Check DNS C2 server status on EC2

if [ -z "$EC2_INSTANCE_ID" ]; then
    echo "Error: EC2_INSTANCE_ID not set"
    echo "Run: source set_env_vars.sh"
    exit 1
fi

echo "🔍 Checking DNS C2 Server Status on EC2..."
echo ""

# Check if process is running
echo "1️⃣ Checking if DNS server process is running..."
CMD_ID=$(aws ssm send-command \
    --instance-ids "$EC2_INSTANCE_ID" \
    --document-name "AWS-RunShellScript" \
    --parameters 'commands=["ps aux | grep -E \"dns_server|python3\" | grep -v grep"]' \
    --query 'Command.CommandId' \
    --output text)

sleep 3

aws ssm get-command-invocation \
    --command-id "$CMD_ID" \
    --instance-id "$EC2_INSTANCE_ID" \
    --query 'StandardOutputContent' \
    --output text

echo ""
echo "2️⃣ Checking log file..."
CMD_ID=$(aws ssm send-command \
    --instance-ids "$EC2_INSTANCE_ID" \
    --document-name "AWS-RunShellScript" \
    --parameters 'commands=["sudo tail -20 /var/log/dns-c2/dns_server.log 2>&1 || echo \"Log file not found or empty\""]' \
    --query 'Command.CommandId' \
    --output text)

sleep 3

aws ssm get-command-invocation \
    --command-id "$CMD_ID" \
    --instance-id "$EC2_INSTANCE_ID" \
    --query 'StandardOutputContent' \
    --output text

echo ""
echo "3️⃣ Checking CloudWatch agent status..."
CMD_ID=$(aws ssm send-command \
    --instance-ids "$EC2_INSTANCE_ID" \
    --document-name "AWS-RunShellScript" \
    --parameters 'commands=["sudo /opt/aws/amazon-cloudwatch-agent/bin/amazon-cloudwatch-agent-ctl -a query -m ec2 -c default -s 2>&1"]' \
    --query 'Command.CommandId' \
    --output text)

sleep 3

aws ssm get-command-invocation \
    --command-id "$CMD_ID" \
    --instance-id "$EC2_INSTANCE_ID" \
    --query 'StandardOutputContent' \
    --output text

echo ""
echo "4️⃣ Checking if log directory exists and permissions..."
CMD_ID=$(aws ssm send-command \
    --instance-ids "$EC2_INSTANCE_ID" \
    --document-name "AWS-RunShellScript" \
    --parameters 'commands=["sudo ls -la /var/log/dns-c2/ 2>&1 || echo \"Directory not found\""]' \
    --query 'Command.CommandId' \
    --output text)

sleep 3

aws ssm get-command-invocation \
    --command-id "$CMD_ID" \
    --instance-id "$EC2_INSTANCE_ID" \
    --query 'StandardOutputContent' \
    --output text

