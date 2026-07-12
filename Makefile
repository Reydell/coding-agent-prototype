.PHONY: orchestrator coder

orchestrator:
	uv run python -m src.orchestrator

instruction ?=
CODER_INSTRUCTION := $(strip $(if $(instruction),$(instruction),$(filter-out coder,$(MAKECMDGOALS))))

coder:
	@if [ -z "$(CODER_INSTRUCTION)" ]; then \
		echo 'Usage: make coder "instruction"'; \
		exit 2; \
	fi
	uv run python -m src.coder "$(CODER_INSTRUCTION)"

ifneq ($(filter coder,$(MAKECMDGOALS)),)
%:
	@:
endif
