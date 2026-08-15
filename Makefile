.PHONY: suite paper paper-legacy test clean all bootstrap ci-local mutate latency sweep formal paper-v3 arxiv

# SARC Suite One-Pass Demo Makefile
# Apache License 2.0
# SEED = 26313

# `paper` depends on `formal` (round-two independent review, finding
# R2-N1/R2-F1(a)): the committed out/checkers/*.json and out/paper/
# slots_v3.json used to be able to drift apart, because `paper` only
# depended on `suite`, so a rerun of `make formal` alone (or a fresh
# commit's HEAD-derived probe re-seeding, since fixed by R2-F1(b))
# could regenerate checker output that the paper draft never picked up.
# `all` lists suite, formal, paper explicitly in that order so a single
# `make all` invocation regenerates everything coherently, not just in
# whatever order each target's own prerequisites happen to imply.
all: suite formal paper test

bootstrap:
	@echo "Bootstrapping pinned engines + toolchain..."
	bash bootstrap.sh

ci-local: bootstrap test suite
	@echo "ci-local: bootstrap + test + suite all green."

suite:
	@echo "Running SARC Suite: all four scenarios in two composition modes..."
	python3 runner.py

# The canonical paper build (Phase 5, v0.3: CH1-CH8, 30-seed CIs,
# exhaustive proofs, V4 citations). Depends on suite, sweep, AND formal
# -- in that order -- so out/paper/slots_v3.json is always populated
# from checker output generated in the SAME invocation, never a stale
# out/checkers/*.json left over from an earlier commit (R2-F1(a)).
paper: suite sweep formal
	@echo "Generating v0.3 paper (CH1-CH8, 30-seed CIs, exhaustive proofs, V4 citations)..."
	python3 paper_v3.py

# Backward-compatible alias: some docs/scripts still say paper-v3.
paper-v3: paper

# The original v0.1/v0.2 paper pipeline (main.py, paper_tables.py) --
# superseded by `paper` (v0.3) as this artifact's live paper, kept only
# because test_suite_sim.py still imports main.py's PAPER_DRAFT_TEXT
# directly for its leakage/committed-files checks. Not part of `all`.
paper-legacy: suite
	@echo "Generating legacy v0.1/v0.2 paper tables and populating draft..."
	python3 main.py

# arXiv LaTeX conversion (paper-tex/): regenerates refs.bib from
# verified-citations.json (never hand-edited, so it can never drift --
# see paper-tex/generate_refs_bib.py), builds main.tex with latexmk
# (falls back to tectonic if latexmk/a TeX Live install is unavailable),
# runs the six parity gates (paper-tex/gates/run_gates.py) and stops on
# any failure, then packages exactly what arXiv needs: main.tex plus the
# already-built main.bbl (arXiv's own documented preference over
# shipping refs.bib + relying on their pipeline to invoke bibtex).
arxiv:
	@echo "Regenerating paper-tex/refs.bib from verified-citations.json..."
	cd paper-tex && python3 generate_refs_bib.py
	@echo "Building main.tex (latexmk, falling back to tectonic)..."
	cd paper-tex && ( \
		latexmk -pdf -interaction=nonstopmode -halt-on-error main.tex \
		|| tectonic main.tex \
	)
	@echo "Running parity gates G1-G6..."
	cd paper-tex && python3 gates/run_gates.py
	@echo "Packaging arxiv.tar.gz (main.tex, main.bbl)..."
	cd paper-tex && rm -f arxiv.tar.gz && tar --sort=name --mtime='UTC 2026-01-01' \
		--owner=0 --group=0 --numeric-owner \
		-cf arxiv.tar.gz main.tex main.bbl
	@echo "arxiv.tar.gz written to paper-tex/arxiv.tar.gz"

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
	@echo "  make sweep     V3 gate: 30-seed sweep, CH1-CH6 means + 95% CIs"
	@echo "  make formal    V2 gate: exhaustive checkers (lattice, CH5, CH7) + proof lint"
	@echo "  make paper     Phase 5: v0.3 paper (depends on suite, sweep, formal, in order)"
	@echo "  make paper-v3  Alias for make paper"
	@echo "  make paper-legacy  Superseded v0.1/v0.2 paper pipeline (main.py)"
	@echo "  make arxiv     Build paper-tex/main.tex, run parity gates G1-G6, package arxiv.tar.gz"
	@echo "  make test      Run the test suite"
	@echo "  make clean     Remove all outputs"
	@echo "  make all       suite + formal + paper + test, in that order (default)"
	@echo ""
	@echo "Outputs:"
	@echo "  out/           Evidence sets, run logs, metrics"
	@echo "  paper4-*-v0.1.md    Paper draft (verbatim from PART 2)"
	@echo "  paper4-*-v0.2-populated.md    Populated paper (slots filled)"
	@echo ""
	@echo "See README.md for full documentation."
