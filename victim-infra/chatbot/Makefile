# Victim Chatbot Makefile

setup:
	uv sync --all-extras

# Run chatbot locally (hot-reload)
local:
	uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Test that prompt injection tricks the LLM into executing code
# Uses real Bedrock API + real Code Interpreter (needs AWS creds + deployed infra)
#
# Usage:
#   make test-injection
#   make test-injection CI_ID=abc-123
#   make test-injection CI_NAME=my_interpreter
#   make test-injection MODEL=us.anthropic.claude-3-5-haiku-20241022-v1:0
#   make test-injection REGION=us-west-2
EXTRA_ARGS =
ifdef CI_ID
EXTRA_ARGS += --id $(CI_ID)
endif
ifdef MODEL
EXTRA_ARGS += --model $(MODEL)
endif
ifdef REGION
EXTRA_ARGS += --region $(REGION)
endif
ifdef CI_NAME
EXTRA_ARGS += --name $(CI_NAME)
endif

test-injection:
	uv run python test_prompt_injection.py $(EXTRA_ARGS)

.PHONY: setup local test-injection
