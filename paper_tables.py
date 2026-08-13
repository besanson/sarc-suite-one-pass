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
Generate paper tables and [GENERATED: ...] slot values SOLELY from
out/metrics.json and the generated manifest (R10) — no independent
re-derivation, no placeholder numbers.

SEED = 26313
"""
from __future__ import annotations

import json
from typing import Any, Dict

SCENARIOS = ["S1", "S2", "S3", "S4"]
DEFECT_CLASSES = [
    "stale_master_data",
    "superseded_golden_record",
    "cross_source_contradiction",
    "schema_drift",
    "missing_mandatory_field",
    "lineage_missing",
    "plausible_outlier",
]


def _format_table1(metrics: Dict[str, Any]) -> str:
    lines = ["| Scenario | Decisions | Executed | Held | DQ Vetoes | SARC Vetoes | Green Vetoes | Winner-gate distribution |"]
    lines.append("|---|---|---|---|---|---|---|---|")
    for s in SCENARIOS:
        block = metrics[s]
        veto = block["veto_counts"]
        loss = block["executed_vs_held_loss"]
        winners = ", ".join(f"{k}={v}" for k, v in sorted(block["winner_gate_distribution"].items()))
        lines.append(
            f"| {s} | {block['decisions']} | {loss['executed_count']} | {loss['held_count']} | "
            f"{veto['dq']} | {veto['sarc']} | {veto['green']} | {winners} |"
        )
    return "\n".join(lines)


def _format_table2(metrics: Dict[str, Any]) -> str:
    matrix = metrics["ch4_matrix"]
    lines = ["| Defect class | dq detection rate | sarc detection rate | green detection rate | winner-gate counts |"]
    lines.append("|---|---|---|---|---|")
    for cls in DEFECT_CLASSES:
        row = matrix.get(cls, {"dq": 0.0, "sarc": 0.0, "green": 0.0, "winner_gate_counts": {}})
        winners = ", ".join(f"{k}={v}" for k, v in sorted(row.get("winner_gate_counts", {}).items()))
        lines.append(
            f"| {cls} | {row['dq']:.3f} | {row['sarc']:.3f} | {row['green']:.3f} | {winners} |"
        )
    lines.append("")
    lines.append(f"union_ok = {matrix['union_ok']}")
    return "\n".join(lines)


def _format_table3(metrics: Dict[str, Any]) -> str:
    divergences = metrics["S4"].get("divergent_decisions", [])
    lines = ["| decision_id | rtr | single_pass | V_pre | V_post | kappa |"]
    lines.append("|---|---|---|---|---|---|")
    if not divergences:
        lines.append("| — | — | — | — | — | — |")
    for d in divergences[:20]:
        pre = d["pre_order_value"]
        post = d["post_order_value"]
        lines.append(
            f"| {d['decision_id']} | {d['remediate_regate_response']} | {d['single_pass_response']} | "
            f"{pre:.2f} | {post:.2f} | {d['cap']:.2f} |" if pre is not None else
            f"| {d['decision_id']} | {d['remediate_regate_response']} | {d['single_pass_response']} | — | — | {d['cap']:.2f} |"
        )
    if len(divergences) > 20:
        lines.append(f"\n({len(divergences) - 20} further divergent decisions omitted for brevity)")
    return "\n".join(lines)


def _format_table4(metrics: Dict[str, Any]) -> str:
    lines = ["| Scenario | Executed count | Executed order value | Held count | Held clean value foregone |"]
    lines.append("|---|---|---|---|---|")
    for s in SCENARIOS:
        loss = metrics[s]["executed_vs_held_loss"]
        lines.append(
            f"| {s} | {loss['executed_count']} | {loss['executed_order_value']:.2f} | "
            f"{loss['held_count']} | {loss['held_clean_value_foregone']:.2f} |"
        )
    return "\n".join(lines)


def _ch_supported(metrics: Dict[str, Any]) -> Dict[str, bool]:
    ch1 = metrics["ch1_violations"] == 0
    ch2 = (
        metrics["ch2_divergent_decisions"] > 0
        and metrics["ch2_direction_counts"]["single_pass_admits_then_violates"] >= 1
    )
    ch3 = metrics["ch3_false_hold"] == 0.0
    po = metrics["ch4_matrix"].get("plausible_outlier", {})
    ch4 = (
        po.get("dq", 1.0) == 0.0
        and po.get("sarc", 1.0) == 0.0
        and po.get("green", 1.0) == 0.0
        and metrics["ch4_matrix"]["union_ok"] is True
    )
    return {"CH1": ch1, "CH2": ch2, "CH3": ch3, "CH4": ch4}


def _abstract_sentence(supported: Dict[str, bool]) -> str:
    parts = []
    for ch in ("CH1", "CH2", "CH3", "CH4"):
        status = "supported" if supported[ch] else "NOT SUPPORTED as written"
        parts.append(f"{ch} {status}")
    return "; ".join(parts) + "."


def generate_tables_and_slots(metrics: Dict[str, Any], manifest: Dict[str, Any]) -> Dict[str, str]:
    """Build every [GENERATED: ...] slot value from metrics + manifest only."""
    slots: Dict[str, str] = {}

    slots["table1"] = _format_table1(metrics)
    slots["table2"] = _format_table2(metrics)
    slots["table3"] = _format_table3(metrics)
    slots["table4"] = _format_table4(metrics)

    slots["metrics.ch1_violations"] = str(metrics["ch1_violations"])
    slots["metrics.ch2_divergent_decisions"] = str(metrics["ch2_divergent_decisions"])
    d = metrics["ch2_direction_counts"]
    slots["metrics.ch2_direction_counts"] = (
        f"{d['single_pass_admits_then_violates']} single_pass_admits_then_violates, "
        f"{d['single_pass_holds_remediated_compliant']} single_pass_holds_remediated_compliant"
    )
    slots["metrics.ch3_false_hold"] = f"{metrics['ch3_false_hold']:.6f}"
    po = metrics["ch4_matrix"].get("plausible_outlier", {})
    slots["metrics.ch4_matrix"] = (
        f"union_ok={metrics['ch4_matrix']['union_ok']}; "
        f"plausible_outlier detection dq={po.get('dq', 0.0):.3f} "
        f"sarc={po.get('sarc', 0.0):.3f} green={po.get('green', 0.0):.3f} "
        f"(declared uncovered); full matrix in Table 2"
    )

    supported = _ch_supported(metrics)
    slots["abstract_results_sentence"] = _abstract_sentence(supported)

    slots["appendixB_manifest"] = json.dumps(manifest, indent=2, sort_keys=True)

    return slots
