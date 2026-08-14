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

from runner import _serialize_evidence_record, build_engines, build_scenarios, run_scenario
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
        "S2": {"scenario": scenario, "plan": [], "results": {"remediate_regate": {"lines": [], "audit_flags": {}, "audit_violations": 0, "exec_evidence_by_decision": {}}}},
        "S3": {"scenario": scenario, "plan": [], "results": {"remediate_regate": {"lines": [], "audit_flags": {}, "audit_violations": 0, "exec_evidence_by_decision": {}}}},
        "S4": {"scenario": scenario, "plan": [], "results": {"remediate_regate": {"lines": [], "audit_flags": {}, "audit_violations": 0, "exec_evidence_by_decision": {}}}},
    }
    for name in ("S2", "S3", "S4"):
        all_results[name]["results"]["single_pass"] = all_results[name]["results"]["remediate_regate"]
    all_results["S1"]["results"]["single_pass"] = all_results["S1"]["results"]["remediate_regate"]

    runner_module._write_outputs(sim, all_results, True)

    exec_evidence_path = tmp_path / "out" / "S1" / "rtr-exec-evidence.jsonl"
    assert exec_evidence_path.exists()
    lines = exec_evidence_path.read_text().splitlines()
    assert lines
    first = json.loads(lines[0])
    assert "decision_id" in first
    assert first["evidence"]
    assert "evidence_id" in first["evidence"][0]
    assert "ground_truth" not in first["evidence"][0]
