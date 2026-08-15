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
Independent review finding F4 (review/REVIEW.md): the post-hoc audit
must re-evaluate the EXACT Phase II evidence, not a synthetic
reconstruction. These tests cover runner.py's exec_evidence threading
and persistence, complementing composition.py's own audit_executed unit
tests in test_audit_unit.py.

SEED = 26313
"""
from __future__ import annotations

import json

from runner import (
    _deserialize_evidence_record,
    _serialize_evidence_record,
    build_engines,
    build_scenarios,
    reload_and_reaudit,
    run_scenario,
)
from sarc_dq.records import EvidenceRecord, RecordMetadata
from suite_sim import RetailSimulation


def test_serialize_evidence_record_excludes_ground_truth_includes_evidence_id():
    record = EvidenceRecord(
        record_id="X-primary",
        payload={"sku": "X", "unit_cost": 5.0, "currency": "GBP"},
        metadata=RecordMetadata(source="erp.pricing", as_of_day=1, retrieved_day=2, version=2, lineage=("supplier_feed:SKU",)),
    )
    serialized = _serialize_evidence_record(record)
    assert serialized["record_id"] == "X-primary"
    assert serialized["evidence_id"] == record.evidence_id()
    assert serialized["payload"] == {"sku": "X", "unit_cost": 5.0, "currency": "GBP"}
    assert serialized["metadata"]["source"] == "erp.pricing"
    assert "ground_truth" not in serialized  # never leaked into persisted output


def test_run_scenario_populates_exec_evidence_for_every_admitted_decision():
    sim = RetailSimulation()
    dq_spec, sarc_spec, green_engines = build_engines(sim)
    scenario = build_scenarios(sim)["S1"]
    result = run_scenario(sim, dq_spec, sarc_spec, green_engines, scenario, modes=("remediate_regate",))
    lines = result["results"]["remediate_regate"]["lines"]
    exec_evidence_by_decision = result["results"]["remediate_regate"]["exec_evidence_by_decision"]

    admitted_ids = {line["decision_id"] for line in lines if line["final"]["admitted"]}
    assert admitted_ids  # sanity: S1 admits plenty
    assert set(exec_evidence_by_decision.keys()) == admitted_ids
    for records in exec_evidence_by_decision.values():
        assert records and all(isinstance(r, EvidenceRecord) for r in records)


def test_run_scenario_exec_evidence_matches_substituted_value_when_triggered():
    sim = RetailSimulation()
    dq_spec, sarc_spec, green_engines = build_engines(sim)
    scenario = build_scenarios(sim)["S1"]
    result = run_scenario(sim, dq_spec, sarc_spec, green_engines, scenario, modes=("remediate_regate",))
    lines = result["results"]["remediate_regate"]["lines"]
    exec_evidence_by_decision = result["results"]["remediate_regate"]["exec_evidence_by_decision"]

    substituted = [line for line in lines if line["remediation"]["evidence_substitution"] and line["final"]["admitted"]]
    assert substituted  # sanity: some decisions substitute and admit
    sample = substituted[0]
    records = exec_evidence_by_decision[sample["decision_id"]]
    assert records[0].payload["unit_cost"] == sample["remediation"]["evidence_substitution"]["substituted_value"]


def test_write_outputs_persists_exec_evidence_jsonl(tmp_path, monkeypatch):
    import runner as runner_module

    # Build everything (needs the real repo's data/specs on disk) BEFORE
    # chdir'ing into an isolated tmp_path -- _write_outputs itself only
    # writes based on the already-in-memory sim/all_results, so it does
    # not need data/specs available at the new cwd.
    sim = RetailSimulation()
    dq_spec, sarc_spec, green_engines = build_engines(sim)
    scenario = build_scenarios(sim)["S1"]
    scenario_result = run_scenario(sim, dq_spec, sarc_spec, green_engines, scenario, modes=("remediate_regate",))

    monkeypatch.chdir(tmp_path)
    all_results = {
        "S1": {"scenario": scenario, "plan": scenario_result["plan"], "results": scenario_result["results"]},
        "S2": {"scenario": scenario, "plan": [], "results": {"remediate_regate": {"lines": [], "audit_flags": {}, "audit_violations": 0, "exec_evidence_by_decision": {}, "buffer_writes": []}}},
        "S3": {"scenario": scenario, "plan": [], "results": {"remediate_regate": {"lines": [], "audit_flags": {}, "audit_violations": 0, "exec_evidence_by_decision": {}, "buffer_writes": []}}},
        "S4": {"scenario": scenario, "plan": [], "results": {"remediate_regate": {"lines": [], "audit_flags": {}, "audit_violations": 0, "exec_evidence_by_decision": {}, "buffer_writes": []}}},
    }
    for name in ("S2", "S3", "S4"):
        all_results[name]["results"]["single_pass"] = all_results[name]["results"]["remediate_regate"]
    all_results["S1"]["results"]["single_pass"] = all_results["S1"]["results"]["remediate_regate"]

    runner_module._write_outputs(sim, all_results, True, dq_spec, sarc_spec, green_engines)

    exec_evidence_path = tmp_path / "out" / "S1" / "rtr-exec-evidence.jsonl"
    assert exec_evidence_path.exists()
    lines = exec_evidence_path.read_text().splitlines()
    assert lines
    first = json.loads(lines[0])
    assert "decision_id" in first
    assert first["evidence"]
    assert "evidence_id" in first["evidence"][0]
    assert "ground_truth" not in first["evidence"][0]


def test_write_outputs_persists_buffer_writes_jsonl_and_substitutions_resolve_uniquely(tmp_path, monkeypatch):
    """Independent review round-two finding R2-F6(a): the durable
    governed-buffer write log is persisted next to the evidence lines,
    and every substitution's buffer_write_eid resolves to exactly one
    entry in it -- not zero, not several."""
    import runner as runner_module

    sim = RetailSimulation()
    dq_spec, sarc_spec, green_engines = build_engines(sim)
    scenario = build_scenarios(sim)["S4"]  # S4 guarantees substitutions occur
    scenario_result = run_scenario(sim, dq_spec, sarc_spec, green_engines, scenario, modes=("remediate_regate",))

    monkeypatch.chdir(tmp_path)
    all_results = {
        "S1": {"scenario": scenario, "plan": [], "results": {"remediate_regate": {"lines": [], "audit_flags": {}, "audit_violations": 0, "exec_evidence_by_decision": {}, "buffer_writes": []}}},
        "S2": {"scenario": scenario, "plan": [], "results": {"remediate_regate": {"lines": [], "audit_flags": {}, "audit_violations": 0, "exec_evidence_by_decision": {}, "buffer_writes": []}}},
        "S3": {"scenario": scenario, "plan": [], "results": {"remediate_regate": {"lines": [], "audit_flags": {}, "audit_violations": 0, "exec_evidence_by_decision": {}, "buffer_writes": []}}},
        "S4": {"scenario": scenario, "plan": scenario_result["plan"], "results": scenario_result["results"]},
    }
    for name in ("S1", "S2", "S3"):
        all_results[name]["results"]["single_pass"] = all_results[name]["results"]["remediate_regate"]
    all_results["S4"]["results"]["single_pass"] = all_results["S4"]["results"]["remediate_regate"]

    runner_module._write_outputs(sim, all_results, True, dq_spec, sarc_spec, green_engines)

    buffer_writes_path = tmp_path / "out" / "S4" / "rtr-buffer-writes.jsonl"
    assert buffer_writes_path.exists()
    write_entries = [json.loads(line) for line in buffer_writes_path.read_text().splitlines()]
    assert write_entries
    assert {"write_seq", "key", "value", "day", "event_id"} <= set(write_entries[0].keys())
    assert len({e["event_id"] for e in write_entries}) == len(write_entries)  # every event id distinct

    evidence_path = tmp_path / "out" / "S4" / "rtr-evidence.jsonl"
    lines = [json.loads(line) for line in evidence_path.read_text().splitlines()]
    substituted = [line for line in lines if line["remediation"]["evidence_substitution"] is not None]
    assert substituted  # S4 is constructed to guarantee at least one
    event_ids_by_id = {e["event_id"]: e for e in write_entries}
    for line in substituted:
        eid = line["remediation"]["evidence_substitution"]["substitute_source"]["buffer_write_eid"]
        matches = [e for e in write_entries if e["event_id"] == eid]
        assert len(matches) == 1  # resolves to exactly one durable write-log entry
        assert eid in event_ids_by_id


# ---------------------------------------------------------------------------
# Persisted-evidence reload audit (independent review round-two finding
# R2-F6(b)): "audit_executed runs before _write_outputs ... the round-two
# requirement for a persisted-evidence replay remains unmet."
# ---------------------------------------------------------------------------


def test_deserialize_evidence_record_round_trips_evidence_id():
    """evidence_id() is a pure function of full_view() (payload +
    metadata); reconstructing a record from its own persisted view must
    therefore reproduce the identical evidence_id, proving the
    round-trip preserves everything the id certifies."""
    original = EvidenceRecord(
        record_id="SKU1-primary",
        payload={"sku": "SKU1", "unit_cost": 12.5, "currency": "GBP"},
        metadata=RecordMetadata(source="erp.pricing", as_of_day=10, retrieved_day=12, version=2, lineage=("supplier_feed:SKU1",)),
    )
    view = _serialize_evidence_record(original)
    reconstructed = _deserialize_evidence_record(view)
    assert reconstructed.evidence_id() == original.evidence_id()
    assert reconstructed.record_id == original.record_id
    assert reconstructed.payload == original.payload
    assert reconstructed.ground_truth == {}  # full_view() never carries it -- never fabricated back in


def test_reload_and_reaudit_matches_the_in_memory_audit(tmp_path, monkeypatch):
    """The exact reproduction the round-two review asked for: after
    outputs are written, load the persisted *-exec-evidence.jsonl back,
    reconstruct the records, rerun the audit from that loaded
    representation, and confirm it agrees with the in-memory audit --
    for every scenario/mode, not just a hand-picked decision."""
    import runner as runner_module

    sim = RetailSimulation()
    dq_spec, sarc_spec, green_engines = build_engines(sim)
    scenario = build_scenarios(sim)["S4"]  # S4: substitutions + a resource downroute path both exercised
    scenario_result = run_scenario(sim, dq_spec, sarc_spec, green_engines, scenario)
    in_memory_flags = {
        mode: dict(scenario_result["results"][mode]["audit_flags"])
        for mode in ("remediate_regate", "single_pass")
    }
    assert any(in_memory_flags["remediate_regate"].values()) is False  # CH1: remediate_regate is sound

    monkeypatch.chdir(tmp_path)
    all_results = {
        "S1": {"scenario": scenario, "plan": [], "results": {m: {"lines": [], "audit_flags": {}, "audit_violations": 0, "exec_evidence_by_decision": {}, "buffer_writes": []} for m in ("remediate_regate", "single_pass")}},
        "S2": {"scenario": scenario, "plan": [], "results": {m: {"lines": [], "audit_flags": {}, "audit_violations": 0, "exec_evidence_by_decision": {}, "buffer_writes": []} for m in ("remediate_regate", "single_pass")}},
        "S3": {"scenario": scenario, "plan": [], "results": {m: {"lines": [], "audit_flags": {}, "audit_violations": 0, "exec_evidence_by_decision": {}, "buffer_writes": []} for m in ("remediate_regate", "single_pass")}},
        "S4": {"scenario": scenario, "plan": scenario_result["plan"], "results": scenario_result["results"]},
    }

    # _write_outputs itself performs the reload+reaudit and raises if it
    # disagrees with the in-memory result -- getting here at all is part
    # of the assertion. Also call reload_and_reaudit directly afterward
    # to check its S4 output against the ORIGINAL in-memory flags one
    # more time, independent of _write_outputs's own bookkeeping.
    runner_module._write_outputs(sim, all_results, True, dq_spec, sarc_spec, green_engines)

    reloaded = runner_module.reload_and_reaudit(dq_spec, sarc_spec, green_engines, sim.sku_true_cost)
    for mode in ("remediate_regate", "single_pass"):
        assert reloaded["S4"][mode] == in_memory_flags[mode]

    # CH1 is reported from the reloaded audit: metrics.json's
    # ch1_violations sums remediate_regate audit_violations across
    # S1-S4 (metrics._ch1_violations) -- confirm it matches the
    # (post-reload) all_results state _write_outputs left behind.
    metrics = json.loads((tmp_path / "out" / "metrics.json").read_text())
    expected_ch1 = sum(
        all_results[name]["results"]["remediate_regate"]["audit_violations"] for name in ("S1", "S2", "S3", "S4")
    )
    assert metrics["ch1_violations"] == expected_ch1
