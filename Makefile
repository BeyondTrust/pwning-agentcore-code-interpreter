# Root Makefile - DNS Exfiltration Security Demo
#
# This project demonstrates a DNS-based exfiltration vulnerability in
# AWS Bedrock AgentCore Code Interpreter's "sandbox" network mode.
#
# Architecture:
#   - attacker-infra/: C2 server and attack tools
#   - victim-infra/: Vulnerable chatbot application
#
# The demo shows that an attacker with NO AWS credentials can exfiltrate
# data by sending a malicious CSV to the victim's public chatbot API.

.PHONY: help setup install local-api deploy-all destroy-all attack demo

# =============================================================================
# Local Development Setup
# =============================================================================

setup:
	python3 -m venv venv
	. venv/bin/activate && pip install --upgrade pip

install: setup
	. venv/bin/activate && pip install -r requirements.txt

local-api:
	. venv/bin/activate && cd victim-infra/chatbot && uvicorn app.main:app --reload --port 8000

# Default target
help:
	@echo ""
	@echo "DNS Exfiltration Security Demo"
	@echo "=============================="
	@echo ""
	@echo "Local Development:"
	@echo "  make install            Set up venv and install all dependencies"
	@echo "  make local-api          Run FastAPI chatbot locally (http://localhost:8000)"
	@echo ""
	@echo "Quick Start:"
	@echo "  make deploy-attacker    Deploy C2 server infrastructure"
	@echo "  make deploy-victim      Deploy vulnerable chatbot"
	@echo "  make attack             Run prompt injection attack"
	@echo ""
	@echo "Individual Commands:"
	@echo "  Attacker Infrastructure (attacker-infra/):"
	@echo "    make deploy-attacker  Deploy C2 server to AWS"
	@echo "    make operator         Start interactive C2 shell"
	@echo "    make generate-csv     Generate malicious CSV payload"
	@echo "    make attack           Attack victim chatbot"
	@echo ""
	@echo "  Victim Infrastructure (victim-infra/):"
	@echo "    make deploy-victim    Deploy vulnerable chatbot to AWS"
	@echo "    make victim-url       Show chatbot URL"
	@echo ""
	@echo "  Demo:"
	@echo "    make demo             Full attack demonstration"
	@echo ""
	@echo "  Cleanup:"
	@echo "    make destroy-all      Destroy all infrastructure"
	@echo ""

# =============================================================================
# Attacker Infrastructure
# =============================================================================

deploy-attacker:
	@echo "Deploying attacker C2 infrastructure..."
	cd attacker-infra && $(MAKE) install
	cd attacker-infra && $(MAKE) terraform-yolo

destroy-attacker:
	cd attacker-infra && $(MAKE) terraform-destroy

operator:
	cd attacker-infra && $(MAKE) operator

generate-csv:
	cd attacker-infra && $(MAKE) generate-csv

# Attack command - requires VICTIM_URL or TARGET
# Usage: make attack TARGET=https://chatbot.victim.com
attack:
	@if [ -z "$(TARGET)" ] && [ -z "$$VICTIM_URL" ]; then \
		echo "Error: No target specified."; \
		echo "Usage: make attack TARGET=https://chatbot.victim.com"; \
		echo "   or: export VICTIM_URL=https://chatbot.victim.com && make attack"; \
		exit 1; \
	fi
	cd attacker-infra && $(MAKE) attack TARGET=$(TARGET)

# =============================================================================
# Victim Infrastructure
# =============================================================================

deploy-victim:
	@echo "Deploying victim chatbot infrastructure..."
	cd victim-infra && $(MAKE) install
	cd victim-infra && $(MAKE) deploy

destroy-victim:
	cd victim-infra && $(MAKE) destroy

victim-url:
	cd victim-infra && $(MAKE) show-url

victim-local:
	cd victim-infra && $(MAKE) local

# =============================================================================
# Full Deployment
# =============================================================================

deploy-all: deploy-attacker deploy-victim
	@echo ""
	@echo "=========================================="
	@echo "  All Infrastructure Deployed!"
	@echo "=========================================="
	@echo ""
	@echo "Attacker C2 Server:"
	@cd attacker-infra && source set_env_vars.sh && echo "  http://$$EC2_IP:8080"
	@echo ""
	@echo "Victim Chatbot:"
	@cd victim-infra && $(MAKE) show-url
	@echo ""
	@echo "To run the attack:"
	@echo "  make attack TARGET=<victim-url>"
	@echo ""
	@echo "Or start the interactive operator shell:"
	@echo "  make operator"
	@echo ""

destroy-all:
	-cd victim-infra && $(MAKE) destroy
	-cd attacker-infra && $(MAKE) terraform-destroy
	@echo "✓ All infrastructure destroyed"

# =============================================================================
# Demo Mode
# =============================================================================

demo:
	@echo ""
	@echo "=========================================="
	@echo "  DNS EXFILTRATION ATTACK DEMO"
	@echo "=========================================="
	@echo ""
	@echo "This demo shows how an attacker can exfiltrate sensitive data"
	@echo "from a victim's AWS account WITHOUT having any AWS credentials."
	@echo ""
	@echo "Attack Flow:"
	@echo "  1. Attacker generates malicious CSV with prompt injection"
	@echo "  2. Attacker sends CSV to victim's public chatbot API"
	@echo "  3. Chatbot passes CSV to AgentCore Code Interpreter"
	@echo "  4. Prompt injection triggers DNS C2 payload"
	@echo "  5. Data exfiltrates via DNS queries to attacker's C2"
	@echo ""
	@echo "Prerequisites:"
	@echo "  - Both infrastructures deployed (make deploy-all)"
	@echo "  - Attacker C2 server running"
	@echo ""
	@read -p "Press Enter to start the attack demo..."
	@$(MAKE) attack TARGET=$$(cd victim-infra/terraform && terraform output -raw chatbot_url)
