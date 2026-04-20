# Root Makefile - AgentCore Sandbox Breakout Security Demo
#
# This project demonstrates DNS and S3-based exfiltration vulnerabilities in
# AWS Bedrock AgentCore Code Interpreter's "sandbox" network mode.
#
# Architecture:
#   - attacker-infra/: DNS-based C2 server and attack tools
#   - attacker-infra-s3/: S3-based C2 channel
#   - victim-infra/: Vulnerable chatbot application
#
# Each infrastructure has its own venv and Makefile. This root Makefile
# orchestrates common operations across all three.

.PHONY: help setup deploy-all destroy-all exploit attack demo \
        deploy-attacker destroy-attacker connect-session operator attach generate-csv \
        setup-s3 deploy-attacker-s3 destroy-attacker-s3 exploit-s3 connect-session-s3 generate-csv-s3 \
        deploy-victim destroy-victim victim-url victim-local

# Default target
help:
	@echo ""
	@echo "AgentCore Sandbox Breakout Security Demo"
	@echo "========================================"
	@echo ""
	@echo "Quick Start:"
	@echo "  make setup              Set up all infrastructures (venv + deps)"
	@echo "  make deploy-all         Deploy DNS C2 server + victim chatbot"
	@echo "  make exploit            Generate payload + send to victim (DNS channel)"
	@echo "  make connect-session    Attach to C2 session interactively (DNS channel)"
	@echo ""
	@echo "DNS C2 Channel (attacker-infra/):"
	@echo "  make deploy-attacker    Deploy DNS C2 server to AWS"
	@echo "  make generate-csv       Generate malicious CSV payload"
	@echo "  make exploit TARGET=url Override victim URL for exploit"
	@echo ""
	@echo "S3 C2 Channel (attacker-infra-s3/):"
	@echo "  make setup-s3           Set up S3 channel dependencies"
	@echo "  make deploy-attacker-s3 Deploy S3 C2 bucket to AWS"
	@echo "  make generate-csv-s3    Generate malicious CSV (S3 channel)"
	@echo "  make exploit-s3         Full S3 attack (TARGET=url)"
	@echo "  make connect-session-s3 Attach to S3 C2 session interactively"
	@echo ""
	@echo "Victim Infrastructure (victim-infra/):"
	@echo "  make deploy-victim      Deploy vulnerable chatbot to AWS"
	@echo "  make victim-url         Show chatbot URL"
	@echo "  make victim-local       Run chatbot locally"
	@echo ""
	@echo "Cleanup:"
	@echo "  make destroy-all        Destroy all infrastructure"
	@echo ""

# =============================================================================
# Setup
# =============================================================================

setup:
	@echo "Setting up attacker infrastructure (DNS channel)..."
	cd attacker-infra && $(MAKE) setup
	@echo ""
	@echo "Setting up attacker infrastructure (S3 channel)..."
	cd attacker-infra-s3 && $(MAKE) setup
	@echo ""
	@echo "Setting up victim infrastructure..."
	cd victim-infra && $(MAKE) setup
	@echo ""
	@echo "Setup complete! Each project has its own venv."

# =============================================================================
# Attacker Infrastructure
# =============================================================================

deploy-attacker:
	@echo "Deploying attacker C2 infrastructure..."
	cd attacker-infra && $(MAKE) deploy

destroy-attacker:
	cd attacker-infra && $(MAKE) destroy

# Exploit: generate payload + send to victim in one step
# Usage: make exploit (reads .victim_url) or make exploit TARGET=https://chatbot.victim.com
exploit:
	@if [ -n "$(TARGET)" ]; then \
		cd attacker-infra && $(MAKE) exploit TARGET=$(TARGET); \
	else \
		cd attacker-infra && $(MAKE) exploit; \
	fi

connect-session:
	cd attacker-infra && $(MAKE) connect-session

# Aliases for backwards compatibility
operator attach:
	cd attacker-infra && $(MAKE) connect-session

generate-csv:
	cd attacker-infra && $(MAKE) generate-csv

# Attack command - requires TARGET
# Usage: make attack TARGET=https://chatbot.victim.com
attack:
	@if [ -z "$(TARGET)" ]; then \
		echo "Error: No target specified."; \
		echo "Usage: make attack TARGET=https://chatbot.victim.com"; \
		exit 1; \
	fi
	cd attacker-infra && $(MAKE) attack TARGET=$(TARGET)

# =============================================================================
# S3 C2 Channel (attacker-infra-s3/)
# =============================================================================
deploy-attacker-s3:
	@echo "Deploying S3 C2 infrastructure..."
	cd attacker-infra-s3 && $(MAKE) deploy

destroy-attacker-s3:
	cd attacker-infra-s3 && $(MAKE) destroy

exploit-s3:
	@if [ -n "$(TARGET)" ]; then \
		cd attacker-infra-s3 && $(MAKE) exploit TARGET=$(TARGET); \
	else \
		cd attacker-infra-s3 && $(MAKE) exploit; \
	fi

connect-session-s3:
	cd attacker-infra-s3 && $(MAKE) connect-session

generate-csv-s3:
	cd attacker-infra-s3 && $(MAKE) generate-csv

# =============================================================================
# Victim Infrastructure
# =============================================================================

deploy-victim:
	@echo "Deploying victim chatbot infrastructure..."
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

deploy-all: deploy-attacker deploy-victim deploy-attacker-s3
	@echo ""
	@echo "=========================================="
	@echo "  All Infrastructure Deployed!"
	@echo "=========================================="
	@echo ""
	@echo "Victim Chatbot:"
	@cd victim-infra && $(MAKE) show-url
	@echo ""
	@echo "To run the exploit, run one of:"
	@echo "  make exploit"
	@echo "  make exploit-s3"
	@echo ""
	@echo "Then connect to the session, run one of:"
	@echo "  make connect-session"
	@echo "  make connect-session-s3"
	@echo ""

destroy-all:
	-cd victim-infra && $(MAKE) destroy
	-cd attacker-infra && $(MAKE) destroy
	-cd attacker-infra-s3 && $(MAKE) destroy
	@echo "All infrastructure destroyed"

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
	@read -p "Press Enter to start the exploit..."
	@$(MAKE) exploit
