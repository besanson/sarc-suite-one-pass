.PHONY: suite paper test clean all bootstrap ci-local

# SARC Suite One-Pass Demo Makefile
# Apache License 2.0
# SEED = 26313

all: suite paper test

bootstrap:
	@echo "Bootstrapping pinned engines + toolchain..."
	bash bootstrap.sh

ci-local: bootstrap test suite
	@echo "ci-local: bootstrap + test + suite all green."

suite:
	@echo "Running SARC Suite: all four scenarios in two composition modes..."
	python3 runner.py

paper: suite
	@echo "Generating paper tables and populating draft..."
	python3 main.py

test:
	@echo "Running test suite..."
	python3 -m pytest -v

clean:
	@echo "Cleaning up outputs..."
	rm -rf out/
	rm -f paper4-composition-draft-v*.md
	rm -rf .pytest_cache .hypothesis
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete

help:
	@echo "SARC Suite One-Pass Demo"
	@echo ""
	@echo "Targets:"
	@echo "  make bootstrap Clone pinned engines (engines.lock) + install toolchain"
	@echo "  make ci-local  bootstrap + test + suite (local acceptance for ci.yml)"
	@echo "  make suite     Run all scenarios (S1-S4) in both modes"
	@echo "  make paper     Generate paper tables and populate draft"
	@echo "  make test      Run the test suite"
	@echo "  make clean     Remove all outputs"
	@echo "  make all       suite + paper + test (default)"
	@echo ""
	@echo "Outputs:"
	@echo "  out/           Evidence sets, run logs, metrics"
	@echo "  paper4-*-v0.1.md    Paper draft (verbatim from PART 2)"
	@echo "  paper4-*-v0.2-populated.md    Populated paper (slots filled)"
	@echo ""
	@echo "See README.md for full documentation."
