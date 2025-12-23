#!/bin/bash
# Configure EC2 instance with DNS server

# Check required environment variables first (before set -e)
if [ -z "$EC2_INSTANCE_ID" ] || [ -z "$S3_BUCKET" ] || [ -z "$DOMAIN" ]; then
    echo "Error: Required environment variables not set"
    echo "Please run: source set_env_vars.sh"
    return 1 2>/dev/null || exit 1
fi

set -e

echo "=========================================="
echo "Configuring EC2 Instance"
echo "=========================================="
echo ""
echo "[*] Instance ID: $EC2_INSTANCE_ID"
echo "[*] S3 Bucket: $S3_BUCKET"
echo "[*] Domain: $DOMAIN"
echo ""

INSTANCE_ID="$EC2_INSTANCE_ID"
BUCKET="$S3_BUCKET"
DNS_PREFIX="dns-server"

# Stop any running DNS server process
echo "[*] Stopping any running DNS server process..."
aws ssm send-command \
    --instance-ids "$INSTANCE_ID" \
    --document-name "AWS-RunShellScript" \
    --parameters 'commands=["pkill -f dns_server || true"]' \
    --output text > /dev/null 2>&1
echo "[✓] DNS server process stopped"
echo ""

# Create deployment script for EC2
cat > /tmp/deploy_dns_ec2.sh << DEPLOY_SCRIPT
#!/bin/bash
set -e

BUCKET="$BUCKET"
DNS_PREFIX="$DNS_PREFIX"
DOMAIN="$DOMAIN"
INSTALL_DIR="/opt/dns-c2"
LOG_DIR="/var/log/dns-c2"

echo "=========================================="
echo "EC2 Setup for DNS Server"
echo "=========================================="
echo ""

# Install dependencies
echo "[*] Installing dependencies..."
sudo yum install -y python3-pip amazon-cloudwatch-agent 2>/dev/null || sudo apt-get install -y python3-pip amazon-cloudwatch-agent
sudo pip3 install dnslib

# Create log directory
echo "[*] Creating log directory..."
sudo mkdir -p /var/log/dns-c2
sudo chmod 755 /var/log/dns-c2

# Create directory in /opt (accessible by all users)
echo "[*] Creating directory at /opt/dns-c2..."
sudo mkdir -p /opt/dns-c2
cd /opt/dns-c2

# Download DNS server from S3
echo "[*] Downloading DNS server from S3..."
sudo aws s3 cp "s3://$BUCKET/$DNS_PREFIX/dns_server_with_api.py" dns_server_with_api.py

# Make readable by all users
sudo chmod 755 /opt/dns-c2
sudo chmod 644 /opt/dns-c2/dns_server_with_api.py

# Also create symlink in ssm-user home if it exists
if [ -d "/home/ssm-user" ]; then
    echo "[*] Creating symlink for ssm-user..."
    sudo ln -sf /opt/dns-c2 /home/ssm-user/dns-c2
    sudo chown -h ssm-user:ssm-user /home/ssm-user/dns-c2
fi

# Configure CloudWatch Logs agent
echo "[*] Configuring CloudWatch Logs agent..."
sudo tee /opt/aws/amazon-cloudwatch-agent/etc/amazon-cloudwatch-agent.json > /dev/null << CWCONFIG
{
  "logs": {
    "logs_collected": {
      "files": {
        "collect_list": [
          {
            "file_path": "/var/log/dns-c2/dns_server.log",
            "log_group_name": "/aws/ec2/dns-c2-server",
            "log_stream_name": "{instance_id}/dns-server",
            "timezone": "UTC"
          }
        ]
      }
    }
  }
}
CWCONFIG

# Start CloudWatch Logs agent
echo "[*] Starting CloudWatch Logs agent..."
sudo /opt/aws/amazon-cloudwatch-agent/bin/amazon-cloudwatch-agent-ctl \
    -a fetch-config \
    -m ec2 \
    -s \
    -c file:/opt/aws/amazon-cloudwatch-agent/etc/amazon-cloudwatch-agent.json

# Create start script (with API)
echo "[*] Creating start script..."
sudo tee /opt/dns-c2/start_dns_server.sh > /dev/null << STARTSCRIPT
#!/bin/bash
cd /opt/dns-c2
sudo python3 dns_server_with_api.py --domain $DOMAIN --dns-port 53 --api-port 8080
STARTSCRIPT
sudo chmod +x /opt/dns-c2/start_dns_server.sh

echo ""
echo "[✓] Setup complete!"
echo ""
echo "Files installed to: /opt/dns-c2"
echo ""
echo "To start the DNS server, choose ONE option:"
echo ""
echo "Option 1 - With API (for remote operator shell):"
echo "  sudo /opt/dns-c2/start_dns_with_api.sh"
echo "  Then connect from your machine: python operator_shell_remote.py --server http://<EC2-IP>:8080"
echo ""
echo "Option 2 - Standalone (view logs locally):"
echo "  sudo /opt/dns-c2/start_dns_server.sh"
echo ""
DEPLOY_SCRIPT

# Upload deployment script to S3
echo "[*] Uploading deployment script to S3..."
aws s3 cp /tmp/deploy_dns_ec2.sh "s3://$BUCKET/$DNS_PREFIX/deploy_dns_ec2.sh"

# Execute deployment on EC2 via SSM
echo "[*] Executing deployment on EC2 via SSM..."
COMMAND_ID=$(aws ssm send-command \
    --instance-ids "$INSTANCE_ID" \
    --document-name "AWS-RunShellScript" \
    --parameters commands="[
        \"aws s3 cp s3://$BUCKET/$DNS_PREFIX/deploy_dns_ec2.sh /tmp/deploy_dns_ec2.sh\",
        \"chmod +x /tmp/deploy_dns_ec2.sh\",
        \"bash /tmp/deploy_dns_ec2.sh\"
    ]" \
    --output text \
    --query 'Command.CommandId')

echo "[*] Command ID: $COMMAND_ID"
echo "[*] Waiting for command to complete..."

# Wait for command to complete
aws ssm wait command-executed \
    --command-id "$COMMAND_ID" \
    --instance-id "$INSTANCE_ID"

# Get command output
echo ""
echo "=========================================="
echo "Deployment Output:"
echo "=========================================="
aws ssm get-command-invocation \
    --command-id "$COMMAND_ID" \
    --instance-id "$INSTANCE_ID" \
    --query 'StandardOutputContent' \
    --output text

echo ""
echo "=========================================="
echo "[✓] EC2 configuration complete!"
echo "=========================================="
echo ""
echo "📦 Files installed on EC2 instance to: /opt/dns-c2/"
echo ""

# Kill any existing DNS server processes and start the server
echo "[*] Stopping any existing DNS server processes..."
aws ssm send-command \
    --instance-ids "$INSTANCE_ID" \
    --document-name "AWS-RunShellScript" \
    --parameters 'commands=["sudo pkill -f dns_server || true"]' \
    --output text > /dev/null 2>&1

sleep 2

echo "[*] Starting DNS C2 server with API..."
START_CMD_ID=$(aws ssm send-command \
    --instance-ids "$INSTANCE_ID" \
    --document-name "AWS-RunShellScript" \
    --parameters 'commands=["sudo nohup /opt/dns-c2/start_dns_server.sh > /var/log/dns-c2/startup.log 2>&1 &"]' \
    --output text \
    --query 'Command.CommandId')

echo "[✓] DNS C2 server started (Command ID: $START_CMD_ID)"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🎮 DNS C2 Server is now running on EC2!"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "📊 Monitor logs:"
echo "  make logs"
echo ""
echo "🎮 Start your operator shell:"
echo "  make operator"
echo ""
echo "🧪 Test with payload:"
echo "  make sandbox"
echo ""

