# Root Makefile - DNS Exfiltration Security Demo
#
# This project demonstrates a DNS-based exfiltration vulnerability in
# AWS Bedrock AgentCore Code Interpreter's "sandbox" network mode.
#
# Architecture:
#   - attacker-infra/: C2 server and attack tools
#   - victim-infra/: Vulnerable chatbot application
#
# Each infrastructure has its own venv and Makefile. This root Makefile
# orchestrates common operations across both.

.PHONY: help setup deploy-all destroy-all exploit attack demo \
        deploy-attacker destroy-attacker connect-session operator attach generate-csv \
        deploy-victim destroy-victim victim-url victim-local

# Default target
help:
	@echo ""
	@echo "DNS Exfiltration Security Demo"
	@echo "=============================="
	@echo ""
	@echo "Quick Start:"
	@echo "  make setup              Set up both infrastructures (venv + deps)"
	@echo "  make deploy-all         Deploy both C2 server and victim chatbot"
	@echo "  make exploit            Generate payload + send to victim"
	@echo "  make connect-session    Attach to C2 session interactively"
	@echo ""
	@echo "Attacker Infrastructure (attacker-infra/):"
	@echo "  make deploy-attacker    Deploy C2 server to AWS"
	@echo "  make generate-csv       Generate malicious CSV payload"
	@echo "  make exploit TARGET=url Override victim URL for exploit"
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
	@echo "Setting up attacker infrastructure..."
	cd attacker-infra && $(MAKE) setup
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

deploy-all: deploy-attacker deploy-victim
	@echo ""
	@echo "=========================================="
	@echo "  All Infrastructure Deployed!"
	@echo "=========================================="
	@echo ""
	@echo "Victim Chatbot:"
	@cd victim-infra && $(MAKE) show-url
	@echo ""
	@echo "To run the exploit:"
	@echo "  make exploit"
	@echo ""
	@echo "Then connect to the session:"
	@echo "  make connect-session"
	@echo ""

destroy-all:
	-cd victim-infra && $(MAKE) destroy
	-cd attacker-infra && $(MAKE) destroy
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
