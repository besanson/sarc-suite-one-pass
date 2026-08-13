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
Aggregate CH1-CH4 metrics from a completed suite run. Every number here is
computed from the actual gate decisions recorded during the run — nothing
is hand-entered.

SEED = 26313
"""
from __future__ import annotations

from collections import defaultdict
from typing import Dict, List

from runner import aggregate_scenario_block
from suite_sim import DEFECT_CLASSES

SCENARIO_ORDER = ["S1", "S2", "S3", "S4"]


def _ch1_violations(all_results: Dict[str, dict]) -> int:
    return sum(all_results[s]["results"]["remediate_regate"]["audit_violations"] for s in SCENARIO_ORDER)


def _ch2(all_results: Dict[str, dict]):
    """prereg/ch2-semantics.md: a decision is divergent iff (1) the
    Exec/Held class differs between remediate_regate and single_pass, or
    (2) both execute (same class) but the post-hoc audit flags a
    violation for single_pass's executed action. A same-class decision
    whose response *string* differs from a clean audit is a label-only
    difference — real, but reported separately, not folded into
    ch2_divergent_decisions."""
    s4 = all_results["S4"]
    rtr_lines = s4["results"]["remediate_regate"]["lines"]
    sp_lines = s4["results"]["single_pass"]["lines"]
    sp_audit_flags = s4["results"]["single_pass"]["audit_flags"]

    divergent = 0
    label_only = 0
    admits_then_violates = 0
    holds_remediated_compliant = 0
    for rtr_line, sp_line in zip(rtr_lines, sp_lines):
        decision_id = rtr_line["decision_id"]
        sp_admitted = sp_line["final"]["admitted"]
        rtr_admitted = rtr_line["final"]["admitted"]
        class_change = rtr_admitted != sp_admitted
        # Rule 2 only applies within a shared Exec class: a class change
        # is already rule 1, regardless of what the audit says.
        audited_violation = (
            sp_admitted and rtr_admitted and sp_audit_flags.get(decision_id, False)
        )

        if class_change or audited_violation:
            divergent += 1
        elif rtr_line["final"]["response"] != sp_line["final"]["response"]:
            label_only += 1

        if sp_admitted and sp_audit_flags.get(decision_id, False):
            admits_then_violates += 1
        elif (not sp_admitted) and rtr_admitted:
            holds_remediated_compliant += 1

    return divergent, label_only, {
        "single_pass_admits_then_violates": admits_then_violates,
        "single_pass_holds_remediated_compliant": holds_remediated_compliant,
    }


def _ch3_false_hold(all_results: Dict[str, dict]) -> float:
    population = 0
    held = 0
    for s in SCENARIO_ORDER:
        lines = all_results[s]["results"]["remediate_regate"]["lines"]
        plan = all_results[s]["plan"]
        for line, p in zip(lines, plan):
            clean = p.injected_defect is None
            authorised = line["gates"]["sarc"]["verdict"] == "admit"
            in_budget = line["gates"]["green"]["verdict"] == "admit"
            if clean and authorised and in_budget:
                population += 1
                if not line["final"]["admitted"]:
                    held += 1
    return (held / population) if population else 0.0


CH4_SOURCE_SCENARIO = "S1"  # loose budgets, all roles authorised: zero sarc/green
# vetoes overall (verified by T-c), so per-class sarc/green detection rates
# here are not confounded by S2's tight budgets or S3's authority pressure —
# exactly the "clean laboratory" the original brief describes S1 as.


def _ch4_matrix(all_results: Dict[str, dict]) -> Dict[str, object]:
    counts = {cls: {"dq": 0, "sarc": 0, "green": 0, "n": 0} for cls in DEFECT_CLASSES}
    winner_counts = {cls: defaultdict(int) for cls in DEFECT_CLASSES}
    lines = all_results[CH4_SOURCE_SCENARIO]["results"]["remediate_regate"]["lines"]
    plan = all_results[CH4_SOURCE_SCENARIO]["plan"]
    for line, p in zip(lines, plan):
        cls = p.injected_defect
        if cls is None:
            continue
        counts[cls]["n"] += 1
        # dq: use the real GateDecision.detected flag (Phase I under
        # remediate_regate re-evaluates DQ on the remediated evidence in
        # Phase II, so "verdict" alone would read "admit" post-substitution).
        if line["gates"]["dq"]["detected"]:
            counts[cls]["dq"] += 1
        for gate in ("sarc", "green"):
            if line["gates"][gate]["verdict"] != "admit":
                counts[cls][gate] += 1
        winner_counts[cls][line["final"]["winner_gate"]] += 1

    matrix: Dict[str, object] = {}
    composed_detected = set()
    member_detected = set()
    for cls, c in counts.items():
        n = c["n"]
        rates = {gate: (c[gate] / n if n else 0.0) for gate in ("dq", "sarc", "green")}
        rates["winner_gate_counts"] = dict(winner_counts[cls])
        matrix[cls] = rates
        if n and any(c[gate] > 0 for gate in ("dq", "sarc", "green")):
            member_detected.add(cls)

    # Composed detection = "did any single gate's own detection fire" — this
    # is intentionally the same basis as member_detected above (there is no
    # separate composition-level detector); the equality check verifies
    # Proposition 5 (no manufactured coverage) rather than assuming it.
    for line, p in zip(lines, plan):
        if p.injected_defect is None:
            continue
        gate_fired = (
            line["gates"]["dq"]["detected"]
            or line["gates"]["sarc"]["verdict"] != "admit"
            or line["gates"]["green"]["verdict"] != "admit"
        )
        if gate_fired:
            composed_detected.add(p.injected_defect)

    matrix["union_ok"] = composed_detected == member_detected
    matrix["source_scenario"] = CH4_SOURCE_SCENARIO
    return matrix


def _s4_divergent_decisions(all_results: Dict[str, dict]) -> List[Dict[str, object]]:
    s4 = all_results["S4"]
    rtr_lines = s4["results"]["remediate_regate"]["lines"]
    sp_lines = s4["results"]["single_pass"]["lines"]
    out = []
    for rtr_line, sp_line in zip(rtr_lines, sp_lines):
        if rtr_line["final"]["response"] == sp_line["final"]["response"]:
            continue
        evidence_sub = rtr_line["remediation"]["evidence_substitution"]
        out.append({
            "decision_id": rtr_line["decision_id"],
            "remediate_regate_response": rtr_line["final"]["response"],
            "single_pass_response": sp_line["final"]["response"],
            "pre_order_value": evidence_sub["pre_order_value"] if evidence_sub else None,
            "post_order_value": evidence_sub["post_order_value"] if evidence_sub else None,
            "cap": rtr_line["context"]["order_value_cap"],
        })
    return out


def build_metrics(sim, all_results: Dict[str, dict], source_sha256_unchanged: bool) -> Dict[str, object]:
    ch2_divergent, ch2_label_only, ch2_directions = _ch2(all_results)
    metrics: Dict[str, object] = {
        "ch1_violations": _ch1_violations(all_results),
        "ch2_divergent_decisions": ch2_divergent,
        "ch2_direction_counts": ch2_directions,
        "label_only_differences": ch2_label_only,
        "ch3_false_hold": _ch3_false_hold(all_results),
        "ch4_matrix": _ch4_matrix(all_results),
    }
    for s in SCENARIO_ORDER:
        metrics[s] = aggregate_scenario_block(all_results[s])
    metrics["S4"]["divergent_decisions"] = _s4_divergent_decisions(all_results)
    metrics["source_sha256_unchanged"] = source_sha256_unchanged
    return metrics
