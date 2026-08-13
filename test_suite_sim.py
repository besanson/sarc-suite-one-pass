# Copyright 2026 SARC Suite Contributors
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
Comprehensive test suite for the SARC Suite demo repair.

Includes the original 11 acceptance tests (renumbered for the real-engine
API) plus the R9 tripwires T-a..T-g that catch the review's enumerated
defects from recurring.

SEED = 26313
"""
from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path

import pytest

from composition import (
    ActionContext,
    CompositionEngine,
    Response,
    build_green_engines,
    is_executed,
    load_sarc_spec,
)
from sarc_dq.dq_spec import load_spec as load_dq_spec
from sarc_dq.gate import GovernedBuffer, PreActionGate as DQPreActionGate
from sarc_dq.records import EvidenceRecord, RecordMetadata
from suite_sim import CARBON_PER_UNIT, COST_MULTIPLIER, RetailSimulation

SKU = "TESTSKU"
TRUE_COST = 10.0
DAY = 200


def _clean_record(unit_cost=TRUE_COST, day=DAY, source="erp.pricing", currency="GBP", version=2):
    payload = {"sku": SKU, "unit_cost": unit_cost}
    if currency is not None:
        payload["currency"] = currency
    return EvidenceRecord(
        record_id=f"{SKU}-primary",
        payload=payload,
        metadata=RecordMetadata(source=source, as_of_day=day, retrieved_day=day, version=version, lineage=("supplier_feed:SKU",)),
    )


def _engine() -> CompositionEngine:
    dq_spec = load_dq_spec()
    sarc_spec = load_sarc_spec("specs/authority.yaml")
    green_engines = build_green_engines({SKU: TRUE_COST}, CARBON_PER_UNIT, COST_MULTIPLIER)
    buffer = GovernedBuffer(values={SKU: TRUE_COST})
    dq_gate = DQPreActionGate(spec=dq_spec, buffer=buffer)
    return CompositionEngine(dq_gate, sarc_spec, green_engines, CARBON_PER_UNIT, COST_MULTIPLIER)


def _ctx(qty=5.0, cost=TRUE_COST, role="agent-replenish"):
    order_value = qty * cost
    return ActionContext(
        agent_id="agent-test", role=role, sku=SKU, day=DAY,
        proposed_qty=qty, order_value=order_value,
        est_cost_eur=order_value * COST_MULTIPLIER, est_carbon_g=qty * CARBON_PER_UNIT,
    )


LOOSE = 1e12


# ---------------------------------------------------------------------------
# Tests 1-6: single-decision gate mechanics (real engines, hand-built inputs)
# ---------------------------------------------------------------------------


def test_1_clean_authorised_inbudget_admits_winner_none():
    engine = _engine()
    ctx = _ctx()
    line, _ = engine.remediate_regate(0, ctx, [_clean_record()], ("agent-replenish",), LOOSE, LOOSE, LOOSE)
    assert line["final"]["admitted"] is True
    assert line["final"]["response"] == "admit"
    assert line["final"]["winner_gate"] == "none"


def test_2_stale_record_substitutes_admitted_phase1_recorded():
    engine = _engine()
    ctx = _ctx()
    stale = _clean_record(unit_cost=TRUE_COST * 0.7, day=DAY)
    stale = EvidenceRecord(
        record_id=stale.record_id, payload=stale.payload,
        metadata=RecordMetadata(source="erp.pricing", as_of_day=DAY - 60, retrieved_day=DAY, version=2, lineage=("supplier_feed:SKU",)),
    )
    line, exec_ctx = engine.remediate_regate(0, ctx, [stale], ("agent-replenish",), LOOSE, LOOSE, LOOSE)
    assert line["final"]["admitted"] is True
    assert line["remediation"]["evidence_substitution"] is not None
    assert line["remediation"]["evidence_substitution"]["substituted_value"] == TRUE_COST
    assert line["remediation"]["order_applied"] == ["evidence_substitution"]
    assert exec_ctx.order_value == pytest.approx(ctx.proposed_qty * TRUE_COST)


def test_3_schema_drift_blocks_winner_dq():
    engine = _engine()
    ctx = _ctx()
    bad = _clean_record(unit_cost=str(TRUE_COST))
    line, _ = engine.remediate_regate(0, ctx, [bad], ("agent-replenish",), LOOSE, LOOSE, LOOSE)
    assert line["final"]["response"] == "block"
    assert line["final"]["winner_gate"] == "dq"
    assert line["final"]["admitted"] is False


def test_4_unauthorised_role_held_winner_sarc():
    engine = _engine()
    ctx = _ctx(role="agent-intruder")
    line, _ = engine.remediate_regate(0, ctx, [_clean_record()], ("agent-replenish",), LOOSE, LOOSE, LOOSE)
    assert line["final"]["winner_gate"] == "sarc"
    assert line["final"]["admitted"] is False
    assert line["final"]["response"] == "block"


def test_5_over_budget_vetoed_winner_green():
    engine = _engine()
    ctx = _ctx()
    line, _ = engine.remediate_regate(0, ctx, [_clean_record()], ("agent-replenish",), LOOSE, 0.001, LOOSE)
    assert line["final"]["winner_gate"] == "green"
    assert line["final"]["admitted"] is False


def test_6_dirty_and_over_budget_most_restrictive_wins_both_recorded():
    engine = _engine()
    ctx = _ctx()
    bad = _clean_record(unit_cost=str(TRUE_COST))  # dq -> block
    line, _ = engine.remediate_regate(0, ctx, [bad], ("agent-replenish",), LOOSE, 0.001, LOOSE)  # green also vetoes
    # exactly one final response
    assert isinstance(line["final"]["response"], str)
    assert line["final"]["response"] == "block"  # block > escalate in restrictiveness
    # both gates' firings are recorded in the line regardless of who won
    assert line["gates"]["dq"]["verdict"] == "block"
    assert line["gates"]["green"]["verdict"] != "admit"


# ---------------------------------------------------------------------------
# Full-suite fixture (run once, shared across the run-level tests)
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def suite_run():
    from runner import run_all_scenarios
    from metrics import build_metrics

    sim, all_results, sha_unchanged = run_all_scenarios()
    metrics = build_metrics(sim, all_results, sha_unchanged)
    return sim, all_results, metrics


# -- Test 7 / T-e: determinism -----------------------------------------------


def test_7_determinism_two_s1_runs_byte_identical():
    sim = RetailSimulation()
    plan_a = sim.generate_plan(seed=26313, unauthorized_role_rate=0.0, authorized_roles=["agent-replenish"])
    plan_b = sim.generate_plan(seed=26313, unauthorized_role_rate=0.0, authorized_roles=["agent-replenish"])
    assert len(plan_a) == len(plan_b)
    for a, b in zip(plan_a, plan_b):
        assert a.injected_defect == b.injected_defect
        assert a.role == b.role
        assert a.read_cost == b.read_cost
        assert a.proposed_qty == b.proposed_qty


def test_7b_determinism_metrics_byte_identical(suite_run):
    from runner import run_all_scenarios
    from metrics import build_metrics

    _, _, metrics_a = suite_run
    sim_b, all_results_b, sha_b = run_all_scenarios()
    metrics_b = build_metrics(sim_b, all_results_b, sha_b)
    assert json.dumps(metrics_a, sort_keys=True) == json.dumps(metrics_b, sort_keys=True)


# -- Test 8 / T-g: one line per decision, no ground_truth, sha unchanged, repos clean --


def test_8_one_line_per_decision_no_ground_truth_sha_unchanged_repos_clean(suite_run):
    sim, all_results, metrics = suite_run
    for s in ("S1", "S2", "S3", "S4"):
        plan = all_results[s]["plan"]
        for mode in ("remediate_regate", "single_pass"):
            lines = all_results[s]["results"][mode]["lines"]
            assert len(lines) == len(plan)
            for line in lines:
                assert "ground_truth" not in json.dumps(line)

    assert metrics["source_sha256_unchanged"] is True

    for repo_dir in ("../dqSarc", "../sarc-governance", "../sarc-governance-engine", "../Greensarc"):
        if Path(repo_dir).is_dir():
            result = subprocess.run(
                ["git", "-C", repo_dir, "status", "--porcelain"], capture_output=True, text=True,
            )
            assert result.stdout == "", f"{repo_dir} has uncommitted changes"


# -- Test 9 / T-d (S4 half): divergences + audit --------------------------


def test_9_s4_divergent_decisions_and_admits_then_violates(suite_run):
    _, _, metrics = suite_run
    assert metrics["ch2_divergent_decisions"] > 0
    assert metrics["ch2_direction_counts"]["single_pass_admits_then_violates"] >= 1


# -- Test 10 / T-d (audit half): CH1 zero across S1-S4 ----------------------


def test_10_ch1_zero_remediate_regate_audit_across_all_scenarios(suite_run):
    _, all_results, metrics = suite_run
    assert metrics["ch1_violations"] == 0
    for s in ("S1", "S2", "S3", "S4"):
        assert all_results[s]["results"]["remediate_regate"]["audit_violations"] == 0


def test_single_pass_s4_audit_finds_violations_above_zero(suite_run):
    _, all_results, _ = suite_run
    assert all_results["S4"]["results"]["single_pass"]["audit_violations"] > 0


# -- Test 11: paper pipeline -------------------------------------------------


def test_11_paper_pipeline_verbatim_and_zero_unfilled(suite_run, tmp_path):
    from manifest import build_manifest
    from paper_tables import generate_tables_and_slots
    from populate_draft import populate_draft
    from main import PAPER_DRAFT_TEXT
    import hashlib

    _, _, metrics = suite_run
    sha = hashlib.sha256(open("data/open_retail_daily.csv", "rb").read()).hexdigest()
    manifest = build_manifest(sha, 26313)
    slots = generate_tables_and_slots(metrics, manifest)

    draft = tmp_path / "v0.1.md"
    draft.write_text(PAPER_DRAFT_TEXT)
    populated = tmp_path / "v0.2.md"
    unfilled = populate_draft(str(draft), slots, str(populated))
    assert unfilled == []

    populated_text = populated.read_text()
    assert "[GENERATED:" not in populated_text


# ---------------------------------------------------------------------------
# R9 tripwires T-a .. T-g
# ---------------------------------------------------------------------------


def test_Ta_no_local_defect_logic_and_real_gates_instantiated():
    composition_src = Path("composition.py").read_text()

    # No hand-rolled staleness/freshness magic numbers (the review's exact
    # "0.55c <= c <= 0.9c" vacuous-predicate bug).
    assert "0.55" not in composition_src
    assert "0.9" not in composition_src

    # No isinstance() call inspects unit_cost — schema/type validation is
    # the real sarc_dq schema_conformant predicate's job, not ours.
    for call_text in re.findall(r"isinstance\([^)]*\)", composition_src):
        assert "unit_cost" not in call_text, f"local type-check on unit_cost: {call_text!r}"

    # No hand-rolled staleness arithmetic (e.g. `retrieved_day - as_of_day`
    # compared against a threshold) — freshness is the real sarc_dq
    # `freshness` predicate's job. RecordMetadata(as_of_day=..., ...) is
    # still constructed here (building remediated/audit evidence), so we
    # check for the ARITHMETIC pattern specifically, not the field name.
    assert not re.search(r"retrieved_day\s*-\s*as_of_day", composition_src)
    assert not re.search(r"as_of_day\s*-\s*retrieved_day", composition_src)

    # The real engines' own types are used directly, not reimplemented.
    import ast
    tree = ast.parse(composition_src)
    imported_names = {
        (alias.asname or alias.name)
        for node in ast.walk(tree) if isinstance(node, ast.ImportFrom)
        for alias in node.names
    }
    assert "GovernedBuffer" in imported_names
    assert "EvidenceRecord" in imported_names
    assert "RecordMetadata" in imported_names

    import composition as comp_module
    from sarc_dq.gate import GovernedBuffer as RealGovernedBuffer
    from sarc_dq.gate import PreActionGate as RealDQGate
    assert comp_module.DQPreActionGate is RealDQGate
    assert comp_module.GovernedBuffer is RealGovernedBuffer

    suite_sim_src = Path("suite_sim.py").read_text()
    assert "from sarc_dq.records import EvidenceRecord, RecordMetadata" in suite_sim_src


def test_Tb_per_class_detection_semantics(suite_run):
    _, _, metrics = suite_run
    matrix = metrics["ch4_matrix"]
    for cls in (
        "stale_master_data", "superseded_golden_record", "schema_drift",
        "missing_mandatory_field", "cross_source_contradiction",
    ):
        assert matrix[cls]["dq"] == 1.0, f"{cls} dq detection should be 1.0, got {matrix[cls]['dq']}"

    po = matrix["plausible_outlier"]
    assert po["dq"] == 0.0
    assert po["sarc"] == 0.0
    assert po["green"] == 0.0

    # lineage_missing: PAA flag only, never gated (dq PAG detection is 0.0)
    assert matrix["lineage_missing"]["dq"] == 0.0


def test_Tb_lineage_missing_paa_flag_count_matches_injected_count(suite_run):
    _, all_results, _ = suite_run
    lines = all_results["S1"]["results"]["remediate_regate"]["lines"]
    plan = all_results["S1"]["plan"]
    injected = sum(1 for p in plan if p.injected_defect == "lineage_missing")
    flagged = sum(1 for line in lines if line["gates"]["dq"]["paa_lineage_flag"])
    assert injected > 0
    assert flagged == injected
    # never gated: none of these decisions were held because of dq
    for line, p in zip(lines, plan):
        if p.injected_defect == "lineage_missing":
            assert line["gates"]["dq"]["verdict"] == "admit"


def test_Tc_s1_zero_sarc_and_green_vetoes(suite_run):
    _, _, metrics = suite_run
    assert metrics["S1"]["veto_counts"]["sarc"] == 0
    assert metrics["S1"]["veto_counts"]["green"] == 0


def test_Td_audit_ch1_zero_and_single_pass_s4_above_zero(suite_run):
    _, all_results, metrics = suite_run
    assert metrics["ch1_violations"] == 0
    assert all_results["S4"]["results"]["single_pass"]["audit_violations"] > 0
    assert metrics["ch2_direction_counts"]["single_pass_admits_then_violates"] >= 1


def test_Te_determinism_already_covered():
    # Covered by test_7 / test_7b; kept as an explicit named tripwire entry.
    assert True


def test_Tf_winner_gate_none_on_clean_admits_lowercase_everywhere(suite_run):
    _, all_results, _ = suite_run
    lines = all_results["S1"]["results"]["remediate_regate"]["lines"]
    saw_clean_admit = False
    for line in lines:
        if line["final"]["response"] == "admit":
            assert line["final"]["winner_gate"] == "none"
            saw_clean_admit = True
        for gate in ("dq", "sarc", "green"):
            v = line["gates"][gate]["verdict"]
            assert v == v.lower()
        assert line["final"]["response"] == line["final"]["response"].lower()
    assert saw_clean_admit


def test_Tg_no_ground_truth_sha_unchanged_repos_clean(suite_run):
    # Same substance as test_8; kept as an explicit named tripwire entry.
    sim, all_results, metrics = suite_run
    assert metrics["source_sha256_unchanged"] is True
    for s in ("S1", "S2", "S3", "S4"):
        for mode in ("remediate_regate", "single_pass"):
            for line in all_results[s]["results"][mode]["lines"]:
                assert "ground_truth" not in json.dumps(line)


# ---------------------------------------------------------------------------
# Additional coverage
# ---------------------------------------------------------------------------


def test_response_restrictiveness_order():
    assert Response.ADMIT < Response.SUBSTITUTE < Response.DEGRADE < Response.ESCALATE < Response.BLOCK


def test_imports_real_packages():
    import sarc_dq
    import sarc_governance
    import green_sarc
    assert sarc_dq is not None and sarc_governance is not None and green_sarc is not None


def test_manifest_versions_are_not_hardcoded():
    from manifest import build_manifest
    import hashlib

    sha = hashlib.sha256(open("data/open_retail_daily.csv", "rb").read()).hexdigest()
    manifest = build_manifest(sha, 26313)
    import importlib.metadata as im
    for pkg, key in (("sarc-dq", "sarc-dq"), ("sarc-governance", "sarc-governance"), ("green-sarc", "green-sarc")):
        assert manifest["engines"][key]["version"] == im.version(pkg)
        assert len(manifest["engines"][key]["commit"]) == 40  # real git sha


def test_apache_headers_present_on_new_files():
    for f in (
        "composition.py", "suite_sim.py", "runner.py", "metrics.py",
        "manifest.py", "paper_tables.py", "populate_draft.py", "main.py",
        "test_suite_sim.py", "process_data.py",
    ):
        text = Path(f).read_text()
        assert "Apache License, Version 2.0" in text, f"{f} missing Apache-2.0 header"


def test_metrics_top_level_keys_exact(suite_run):
    _, _, metrics = suite_run
    expected = {
        "ch1_violations", "ch2_divergent_decisions", "ch2_direction_counts",
        "label_only_differences", "ch3_false_hold", "ch4_matrix",
        "S1", "S2", "S3", "S4", "source_sha256_unchanged",
    }
    assert set(metrics.keys()) == expected
