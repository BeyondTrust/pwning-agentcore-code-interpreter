# Victim Infrastructure Makefile
# This deploys the vulnerable chatbot application

AWS_REGION ?= us-east-1

# Load .env file if it exists (sets AWS_PROFILE)
ifneq (,$(wildcard .env))
include .env
export
endif

# Get ECR repository URL from Terraform output
ECR_REPO = $(shell cd terraform && terraform output -raw ecr_repository_url 2>/dev/null || echo "not-deployed")

# =============================================================================
# Setup
# =============================================================================

setup:
	cd chatbot && uv sync
	@echo ""
	@echo "Setup complete! Run with: cd chatbot && uv run uvicorn app.main:app --reload"

# Generate .env from Terraform outputs (run after terraform-apply)
env-from-terraform:
	@if [ ! -d "terraform/.terraform" ]; then \
		echo "Error: Run 'make terraform-init' first"; \
		exit 1; \
	fi
	@echo "# Generated from Terraform outputs" > .env
	@echo "AWS_REGION=us-east-1" >> .env
	@echo "CODE_INTERPRETER_ID=$$(cd terraform && terraform output -raw code_interpreter_id)" >> .env
	@echo "CODE_INTERPRETER_ARN=$$(cd terraform && terraform output -raw code_interpreter_arn)" >> .env
	@echo "Generated .env file"

# =============================================================================
# Terraform
# =============================================================================

terraform-init:
	cd terraform && terraform init

terraform-plan:
	cd terraform && terraform plan

terraform-apply:
	cd terraform && terraform apply

terraform-destroy:
	cd terraform && terraform destroy

# Full deploy: init + plan + apply (auto-approve) + generate .env
terraform-yolo: terraform-init
	cd terraform && terraform plan && terraform apply -auto-approve
	$(MAKE) env-from-terraform
	@echo ""
	@echo "✓ Infrastructure deployed!"

# Alias for terraform-yolo (backwards compatibility)
terraform-deploy: terraform-yolo
	@echo "Next steps:"
	@echo "  1. Build and push the container: make docker-push"
	@echo "  2. Force ECS to redeploy: make ecs-redeploy"
	@echo "  3. Get the chatbot URL: make show-url"

# =============================================================================
# Docker
# =============================================================================

docker-build:
	cd chatbot && docker build --platform linux/amd64 --no-cache -t victim-chatbot:latest .

docker-run-local:
	docker run -p 8000:8000 \
		-e AWS_REGION=$(AWS_REGION) \
		-e CODE_INTERPRETER_ID=local-testing \
		victim-chatbot:latest

docker-login:
	aws ecr get-login-password --region $(AWS_REGION) | \
		docker login --username AWS --password-stdin $(ECR_REPO)

docker-tag:
	docker tag victim-chatbot:latest $(ECR_REPO):latest

docker-push: docker-build docker-login docker-tag
	docker push $(ECR_REPO):latest
	@echo ""
	@echo "✓ Container pushed to ECR!"
	@echo ""
	@echo "Next: make ecs-redeploy"

# =============================================================================
# ECS
# =============================================================================

ecs-redeploy:
	@echo "Forcing ECS service to redeploy with new container..."
	@CLUSTER=$$(cd terraform && terraform output -raw ecs_cluster_name) && \
	SERVICE=$$(cd terraform && terraform output -raw ecs_service_name) && \
	aws ecs update-service --cluster $$CLUSTER --service $$SERVICE --force-new-deployment --region $(AWS_REGION) > /dev/null
	@echo "✓ Redeployment initiated. New tasks will start shortly."
	@echo ""
	@echo "Monitor with: make ecs-status"

ecs-status:
	@CLUSTER=$$(cd terraform && terraform output -raw ecs_cluster_name) && \
	SERVICE=$$(cd terraform && terraform output -raw ecs_service_name) && \
	aws ecs describe-services --cluster $$CLUSTER --services $$SERVICE --region $(AWS_REGION) \
		--query 'services[0].{Status:status,Running:runningCount,Desired:desiredCount,Pending:pendingCount}'

ecs-logs:
	@LOG_GROUP=$$(cd terraform && terraform output -raw ecs_log_group 2>/dev/null || echo "/ecs/victim-chatbot") && \
	aws logs tail $$LOG_GROUP --follow --region $(AWS_REGION)

# =============================================================================
# Outputs
# =============================================================================

show-url:
	@echo ""
	@echo "Victim Chatbot URL:"
	@cd terraform && terraform output -raw chatbot_url
	@echo ""
	@cd terraform && terraform output -raw chatbot_url > ../../.victim_url
	@echo ""

show-outputs:
	cd terraform && terraform output

show-attack-command:
	@echo ""
	@echo "To attack this chatbot, run from attacker-infra/:"
	@echo ""
	@cd terraform && terraform output -raw attack_command
	@echo ""
	@echo ""

# =============================================================================
# Full Deployment
# =============================================================================

# Deploy everything from scratch
deploy: terraform-deploy docker-push ecs-redeploy
	@echo ""
	@echo "=========================================="
	@echo "  Victim Infrastructure Deployed!"
	@echo "=========================================="
	@$(MAKE) show-url
	@cd terraform && terraform output -raw chatbot_url > ../../.victim_url
	@echo "Victim URL saved to .victim_url"
	@$(MAKE) show-attack-command

# Export environment variables
set-env:
	@echo "export VICTIM_URL=$$(cd terraform && terraform output -raw chatbot_url)"
	@echo ""
	@echo "Run: eval \$$(make set-env)"

# =============================================================================
# Development
# =============================================================================

# Run chatbot locally (without AWS)
local:
	cd chatbot && uv run uvicorn app.main:app --reload --port 8000

# =============================================================================
# Cleanup
# =============================================================================

clean:
	rm -rf chatbot/__pycache__
	rm -rf chatbot/app/__pycache__
	rm -rf chatbot/app/**/__pycache__
	rm -rf chatbot/.venv
	rm -rf .venv

destroy: terraform-destroy clean
	@echo "✓ All victim infrastructure destroyed"

.PHONY: setup terraform-init terraform-plan terraform-apply terraform-destroy \
        terraform-deploy docker-build docker-run-local docker-login docker-tag docker-push \
        ecs-redeploy ecs-status ecs-logs show-url show-outputs show-attack-command \
        deploy set-env local clean destroy env-from-terraform
