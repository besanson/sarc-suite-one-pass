.PHONY: suite paper test clean all bootstrap ci-local mutate latency sweep formal

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

mutate:
	@echo "Mutation testing composition.py + metrics.py (V5 gate, target >=0.85)..."
	rm -rf mutants .mutmut-cache
	mutmut run || true
	mutmut results
	@echo "See ADR-002-mutation-testing.md for the kill score and survivor analysis."

latency:
	@echo "Latency microbenchmark (per-gate + composed, stored in out/quality.json)..."
	python3 latency_bench.py

sweep:
	@echo "V3 gate: 30-seed statistical sweep (prereg/seeds.json), CH1-CH6 + CIs..."
	@echo "Checkpointed per seed under out/results/sweep/ -- safe to re-run/resume."
	python3 sweep.py

formal:
	@echo "V2 gate: exhaustive checkers (lattice, compensation/CH5, remediator/CH7)..."
	python3 -m checkers.lattice_check
	python3 -m checkers.compensation_check
	python3 -m checkers.remediator_check
	python3 -m checkers.proof_status_lint
	@echo "See appendix-a-proofs.md for the proofs these checkers verify."

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
	@echo "  make sweep     V3 gate: 30-seed sweep, CH1-CH6 means + 95% CIs"
	@echo "  make formal    V2 gate: exhaustive checkers (lattice, CH5, CH7) + proof lint"
	@echo "  make clean     Remove all outputs"
	@echo "  make all       suite + paper + test (default)"
	@echo ""
	@echo "Outputs:"
	@echo "  out/           Evidence sets, run logs, metrics"
	@echo "  paper4-*-v0.1.md    Paper draft (verbatim from PART 2)"
	@echo "  paper4-*-v0.2-populated.md    Populated paper (slots filled)"
	@echo ""
	@echo "See README.md for full documentation."
