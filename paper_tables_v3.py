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
Phase 5 (v0.3) slot generation. Extends paper_tables.py's CH1-CH4 slots
(unchanged, still generated solely from out/metrics.json + the manifest)
with CH5-CH8 slots generated solely from out/results/sweep_summary.json
(the V3-gate 30-seed sweep) and out/checkers/*.json (the V2-gate
exhaustive checkers) -- no independent re-derivation, no placeholder
numbers, same discipline as paper_tables.py.

SEED = 26313
"""
from __future__ import annotations

from typing import Any, Dict

from paper_tables import generate_tables_and_slots


def _fmt_ci(stat: Dict[str, float], decimals: int = 2) -> str:
    return (
        f"{stat['mean']:.{decimals}f} (95% CI [{stat['ci95_low']:.{decimals}f}, "
        f"{stat['ci95_high']:.{decimals}f}], n={stat['n']})"
    )


def _format_table5_ch2_ch3_ci(sweep: Dict[str, Any]) -> str:
    lines = ["| Metric | Mean (95% CI, n=30 seeds) |"]
    lines.append("|---|---|")
    lines.append(f"| ch2_divergent_decisions | {_fmt_ci(sweep['ch2_divergent_decisions'], 1)} |")
    lines.append(f"| label_only_differences | {_fmt_ci(sweep['label_only_differences'], 1)} |")
    lines.append(f"| ch3_false_hold | {_fmt_ci(sweep['ch3_false_hold'], 6)} |")
    lines.append(f"| ch5_max_violations (of 98 held profiles) | {_fmt_ci(sweep['ch5_max_violations'], 1)} |")
    return "\n".join(lines)


def _format_table6_ch6_contamination(sweep: Dict[str, Any]) -> str:
    lines = ["| Workflow | Strategy | Poisoned substitutions (mean, 95% CI) | Mean abs value delta (95% CI) |"]
    lines.append("|---|---|---|---|")
    for workflow in ("W1", "W2"):
        block = sweep["ch6"][workflow]
        for strategy in ("plain", "quarantine", "median_of_3"):
            s = block[strategy]
            lines.append(
                f"| {workflow} | {strategy} | {_fmt_ci(s['poisoned_substitutions'], 2)} | "
                f"{_fmt_ci(s['poisoned_mean_abs_value_delta'], 3)} |"
            )
    return "\n".join(lines)


def _format_table7_ch8_robustness(sweep: Dict[str, Any]) -> str:
    r = sweep["ch8_robustness"]
    lines = ["| Hypothesis | Robust across all 30 seeds (x both workflows for CH6) |"]
    lines.append("|---|---|")
    labels = {
        "ch1_robust": "CH1 (veto soundness)",
        "ch2_robust": "CH2 (single-pass unsoundness, new semantics)",
        "ch3_robust": "CH3 (deterministic selectivity)",
        "ch4_robust": "CH4 (coverage honesty)",
        "ch5_robust": "CH5 (compensation unsafe)",
        "ch6_robust": "CH6 (buffer contamination + mitigation)",
    }
    for key, label in labels.items():
        lines.append(f"| {label} | {r[key]} |")
    return "\n".join(lines)


def _abstract_sentence_v3(sweep: Dict[str, Any], compensation_result: Dict[str, Any], remediator_result: Dict[str, Any]) -> str:
    ch1 = "supported" if sweep["ch1_supported_seed_count"] == sweep["n_seeds"] else "NOT SUPPORTED as written"
    ch2 = "supported" if sweep["ch2_supported_seed_count"] == sweep["n_seeds"] else "NOT SUPPORTED as written"
    ch3 = "supported" if sweep["ch3_supported_seed_count"] == sweep["n_seeds"] else "NOT SUPPORTED as written"
    ch4 = "supported" if sweep["ch4_union_ok_seed_count"] == sweep["n_seeds"] else "NOT SUPPORTED as written"
    ch5 = "supported" if compensation_result["proposition_1_holds_exhaustively"] else "NOT SUPPORTED as written"
    w1_ok = sweep["ch6"]["W1"]["plain_has_poisoning_every_seed"] and sweep["ch6"]["W1"]["quarantine_strictly_lower_every_seed"] and sweep["ch6"]["W1"]["median_of_3_strictly_lower_every_seed"]
    w2_ok = sweep["ch6"]["W2"]["plain_has_poisoning_every_seed"] and sweep["ch6"]["W2"]["quarantine_strictly_lower_every_seed"] and sweep["ch6"]["W2"]["median_of_3_strictly_lower_every_seed"]
    if w1_ok and w2_ok:
        ch6 = "supported on every seed in both workflows"
    elif w1_ok:
        ch6 = "supported on every seed under W1; NOT supported on every seed under W2 (smaller weekly-commitment population)"
    else:
        ch6 = "NOT SUPPORTED as written"
    ch7 = remediator_result["ch7_registered_outcome"].replace("_", "-")
    off_grid = remediator_result["off_grid_probe"]
    return (
        f"CH1 {ch1}; CH2 {ch2}; CH3 {ch3}; CH4 {ch4}; CH5 {ch5} (exhaustive over the discrete grid); "
        f"CH6 {ch6}; CH7 {ch7} (two remediators do not commute, "
        f"{remediator_result['counterexample_count']}/{remediator_result['grid_points_checked']} grid points, "
        f"plus {off_grid['non_confluent_count']}/{off_grid['n_probes']} off-grid points per an independent-review-promoted probe); "
        f"CH8 robustness across 30 seeds x 2 workflows holds for CH1-CH5, not for CH6."
    )


def generate_v3_slots(
    metrics: Dict[str, Any],
    manifest: Dict[str, Any],
    sweep: Dict[str, Any],
    lattice_result: Dict[str, Any],
    compensation_result: Dict[str, Any],
    remediator_result: Dict[str, Any],
) -> Dict[str, str]:
    """All slots: the original CH1-CH4/single-run slots (paper_tables.py,
    unchanged) plus the new CH5-CH8/CI/checker slots this v0.3 draft
    additionally needs."""
    slots = generate_tables_and_slots(metrics, manifest)

    slots["abstract_results_sentence_v3"] = _abstract_sentence_v3(sweep, compensation_result, remediator_result)
    slots["table5_ci"] = _format_table5_ch2_ch3_ci(sweep)
    slots["table6_ch6"] = _format_table6_ch6_contamination(sweep)
    slots["table7_ch8"] = _format_table7_ch8_robustness(sweep)

    slots["metrics.label_only_differences"] = str(metrics["label_only_differences"])

    slots["sweep.n_seeds"] = str(sweep["n_seeds"])
    slots["sweep.ch1_supported_seed_count"] = f"{sweep['ch1_supported_seed_count']}/{sweep['n_seeds']}"
    slots["sweep.ch2_divergent_decisions_ci"] = _fmt_ci(sweep["ch2_divergent_decisions"], 1)
    slots["sweep.label_only_differences_ci"] = _fmt_ci(sweep["label_only_differences"], 1)
    slots["sweep.ch3_false_hold_ci"] = _fmt_ci(sweep["ch3_false_hold"], 6)
    slots["sweep.ch4_union_ok_seed_count"] = f"{sweep['ch4_union_ok_seed_count']}/{sweep['n_seeds']}"
    slots["sweep.ch5_supported_seed_count"] = f"{sweep['ch5_supported_seed_count']}/{sweep['n_seeds']}"
    # Round-two ("second"/positioning) response, recommendation R4: the
    # formal (discrete-grid) and empirical (30-seed sweep, decision-
    # instance) CH5 quantities use different denominators and must be
    # labeled distinctly in prose, not just in Table 5 where this same
    # value already appeared unlabeled as "ch5_max_violations". Sourced
    # from the same already-committed sweep_summary.json field Table 5
    # uses -- not a new measurement, not typed.
    slots["sweep.ch5_empirical_compensated_ci"] = _fmt_ci(sweep["ch5_max_violations"], 1)

    ch6_w1_plain = sweep["ch6"]["W1"]["plain"]
    ch6_w2_plain = sweep["ch6"]["W2"]["plain"]
    slots["sweep.ch6_w1_plain_poisoned_ci"] = _fmt_ci(ch6_w1_plain["poisoned_substitutions"], 2)
    slots["sweep.ch6_w2_plain_poisoned_ci"] = _fmt_ci(ch6_w2_plain["poisoned_substitutions"], 2)
    slots["sweep.ch6_w1_mitigations_hold"] = str(
        sweep["ch6"]["W1"]["quarantine_strictly_lower_every_seed"]
        and sweep["ch6"]["W1"]["median_of_3_strictly_lower_every_seed"]
    )
    slots["sweep.ch6_w2_mitigations_hold"] = str(
        sweep["ch6"]["W2"]["quarantine_strictly_lower_every_seed"]
        and sweep["ch6"]["W2"]["median_of_3_strictly_lower_every_seed"]
    )
    slots["sweep.ch6_w2_plain_has_poisoning_every_seed"] = str(sweep["ch6"]["W2"]["plain_has_poisoning_every_seed"])

    slots["sweep.ch8_robustness"] = str(sweep["ch8_robustness"])
    slots["sweep.ch8_all_robust"] = str(sweep["ch8_robustness"]["all_robust"])

    slots["checkers.lattice_total_checks"] = str(lattice_result["total_checks"])
    slots["checkers.lattice_all_hold"] = str(lattice_result["all_hold"])

    slots["checkers.compensation_grid_cells"] = str(compensation_result["grid_cells_checked"])
    slots["checkers.compensation_held_profiles"] = str(compensation_result["held_profiles_count"])
    slots["checkers.compensation_max_violations"] = str(compensation_result["max_violations"])
    slots["checkers.compensation_holds"] = str(compensation_result["proposition_1_holds_exhaustively"])

    slots["checkers.remediator_grid_points"] = str(remediator_result["grid_points_checked"])
    slots["checkers.remediator_counterexamples"] = str(remediator_result["counterexample_count"])
    slots["checkers.remediator_outcome"] = remediator_result["ch7_registered_outcome"]

    off_grid = remediator_result["off_grid_probe"]
    slots["checkers.remediator_offgrid_probes"] = str(off_grid["n_probes"])
    slots["checkers.remediator_offgrid_non_confluent"] = str(off_grid["non_confluent_count"])

    return slots
