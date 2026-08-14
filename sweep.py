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
Phase 3d / V3 gate: the 30-seed statistical sweep over prereg/seeds.json.

Scenario economics (budgets, caps) are calibrated ONCE from the
registered baseline SEED, exactly as build_scenarios/build_w2_scenarios/
build_contamination_scenarios already do — only each scenario's own
`.seed` is overridden per sweep iteration. This holds the "experimental
treatment" (what counts as tight/loose) fixed across the sweep and varies
only the stochastic decision stream (injected defects, roles, plan
quantities), which is the correct design for a seed-robustness study: the
same scenario, repeated draws.

For each of the 30 registered seeds this recomputes CH1-CH4 (S1-S4, W1,
under the ch2-semantics.md redefinition), CH5 (pooled S1-S4 lines against
the weights.json grid), and CH6 (both workflows x plain/quarantine/
median_of_3, prereg/contamination.md). Per-seed summaries (small: no raw
decision lines) are checkpointed to out/results/sweep/seed_<seed>.json so
a killed/resumed run does not redo completed seeds. aggregate_sweep()
then computes 30-seed means and 95% CIs into out/results/sweep_summary.json,
including the CH8 robustness readout (did each hypothesis's registered
decision rule hold in every seed x workflow it was evaluated on).

SEED = 26313 (first entry of prereg/seeds.json)
"""
from __future__ import annotations

import json
import statistics
from dataclasses import replace
from pathlib import Path
from typing import Any, Dict, List

import scipy.stats
from sarc_dq.gate import GovernedBuffer

from ch5_aggregator import evaluate_ch5, load_weights
from contamination import (
    MedianOf3Buffer,
    QuarantineWindowBuffer,
    compute_poisoned_substitutions,
)
from metrics import build_metrics
from runner import (
    build_contamination_scenarios,
    build_engines,
    build_scenarios,
    run_scenario,
)
from suite_sim import RetailSimulation

SEEDS_PATH = "prereg/seeds.json"
SWEEP_DIR = Path("out/results/sweep")
SWEEP_SUMMARY_PATH = Path("out/results/sweep_summary.json")

# 95% two-tailed t-critical value for df = 30 - 1 = 29, computed exactly at
# runtime (fixed per independent review finding F6 -- the previous rounded
# constant 2.045230 diverged from the exact value by up to 3.77e-6 in some
# CI endpoints). The registered seed list is fixed at exactly 30 entries,
# so this single value is always the correct one for this sweep. Cast to
# a plain float: scipy.stats.t.ppf returns a numpy float64, which is not
# JSON-serializable by json.dump.
T_CRIT_DF29 = float(scipy.stats.t.ppf(0.975, 29))

BUFFER_STRATEGIES = {
    "plain": GovernedBuffer,
    "quarantine": QuarantineWindowBuffer,
    "median_of_3": MedianOf3Buffer,
}


def load_seeds() -> List[int]:
    return json.loads(Path(SEEDS_PATH).read_text())["seeds"]


def mean_ci95(values: List[float]) -> Dict[str, float]:
    n = len(values)
    if n == 0:
        return {"mean": 0.0, "ci95_low": 0.0, "ci95_high": 0.0, "n": 0}
    m = statistics.mean(values)
    if n < 2:
        return {"mean": m, "ci95_low": m, "ci95_high": m, "n": n}
    se = statistics.stdev(values) / (n ** 0.5)
    half = T_CRIT_DF29 * se
    return {"mean": m, "ci95_low": m - half, "ci95_high": m + half, "n": n}


def _run_ch1_to_ch5(sim, dq_spec, sarc_spec, green_engines, seed: int) -> Dict[str, Any]:
    scenarios = build_scenarios(sim)  # calibrated once, at the registered SEED
    for name, cfg in scenarios.items():
        scenarios[name] = replace(cfg, seed=seed)

    all_results = {}
    for name in ("S1", "S2", "S3", "S4"):
        all_results[name] = run_scenario(sim, dq_spec, sarc_spec, green_engines, scenarios[name])
    metrics = build_metrics(sim, all_results, source_sha256_unchanged=True)

    pooled_lines = []
    for name in ("S1", "S2", "S3", "S4"):
        pooled_lines.extend(all_results[name]["results"]["remediate_regate"]["lines"])
    ch5 = evaluate_ch5(pooled_lines, load_weights())

    return {
        "ch1_violations": metrics["ch1_violations"],
        "ch2_divergent_decisions": metrics["ch2_divergent_decisions"],
        "ch2_direction_counts": metrics["ch2_direction_counts"],
        "label_only_differences": metrics["label_only_differences"],
        "ch3_false_hold": metrics["ch3_false_hold"],
        "ch4_union_ok": metrics["ch4_matrix"]["union_ok"],
        "ch5_max_violations": ch5["max_violations"],
        "ch5_supported": ch5["ch5_supported"],
    }


def _run_ch6(sim, dq_spec, sarc_spec, green_engines, seed: int) -> Dict[str, Any]:
    scenarios = build_contamination_scenarios(sim, seed=seed)  # calibrated once, at SEED
    out: Dict[str, Any] = {}
    for scenario_name, workflow_key in (("CONTAM-W1", "W1"), ("CONTAM-W2", "W2")):
        scenario = replace(scenarios[scenario_name], seed=seed)
        out[workflow_key] = {}
        for strategy_name, factory in BUFFER_STRATEGIES.items():
            result = run_scenario(
                sim, dq_spec, sarc_spec, green_engines, scenario,
                buffer_factory=factory, modes=("remediate_regate",),
            )
            stats = compute_poisoned_substitutions(
                result["plan"], result["results"]["remediate_regate"]["lines"]
            )
            out[workflow_key][strategy_name] = {
                "substitutions": stats["substitutions"],
                "poisoned_substitutions": stats["poisoned_substitutions"],
                "poisoned_mean_abs_value_delta": stats["poisoned_mean_abs_value_delta"],
            }
    return out


def run_seed(sim, dq_spec, sarc_spec, green_engines, seed: int) -> Dict[str, Any]:
    result = _run_ch1_to_ch5(sim, dq_spec, sarc_spec, green_engines, seed)
    result["seed"] = seed
    result["ch6"] = _run_ch6(sim, dq_spec, sarc_spec, green_engines, seed)
    return result


def run_sweep(data_path: str = "data/open_retail_daily.csv") -> None:
    SWEEP_DIR.mkdir(parents=True, exist_ok=True)
    seeds = load_seeds()
    sim = RetailSimulation(data_path)
    dq_spec, sarc_spec, green_engines = build_engines(sim)

    for seed in seeds:
        seed_path = SWEEP_DIR / f"seed_{seed}.json"
        if seed_path.exists():
            print(f"seed {seed}: already computed, skipping", flush=True)
            continue
        print(f"seed {seed}: running ...", flush=True)
        result = run_seed(sim, dq_spec, sarc_spec, green_engines, seed)
        seed_path.write_text(json.dumps(result, indent=2))
        print(f"seed {seed}: done", flush=True)


def aggregate_sweep() -> Dict[str, Any]:
    seeds = load_seeds()
    per_seed = []
    for seed in seeds:
        seed_path = SWEEP_DIR / f"seed_{seed}.json"
        if not seed_path.exists():
            raise FileNotFoundError(f"missing sweep result for seed {seed}: run run_sweep() first")
        per_seed.append(json.loads(seed_path.read_text()))

    ch1_ok = [r["ch1_violations"] == 0 for r in per_seed]
    ch2_ok = [
        r["ch2_divergent_decisions"] > 0
        and r["ch2_direction_counts"]["single_pass_admits_then_violates"] >= 1
        for r in per_seed
    ]
    ch3_ok = [r["ch3_false_hold"] == 0.0 for r in per_seed]
    ch4_ok = [r["ch4_union_ok"] for r in per_seed]
    ch5_ok = [r["ch5_supported"] for r in per_seed]

    summary: Dict[str, Any] = {
        "n_seeds": len(per_seed),
        "seeds": seeds,
        "ch1_violations_total": sum(r["ch1_violations"] for r in per_seed),
        "ch1_supported_seed_count": sum(ch1_ok),
        "ch2_divergent_decisions": mean_ci95([r["ch2_divergent_decisions"] for r in per_seed]),
        "label_only_differences": mean_ci95([r["label_only_differences"] for r in per_seed]),
        "ch2_supported_seed_count": sum(ch2_ok),
        "ch3_false_hold": mean_ci95([r["ch3_false_hold"] for r in per_seed]),
        "ch3_supported_seed_count": sum(ch3_ok),
        "ch4_union_ok_seed_count": sum(ch4_ok),
        "ch5_max_violations": mean_ci95([r["ch5_max_violations"] for r in per_seed]),
        "ch5_supported_seed_count": sum(ch5_ok),
    }

    ch6_summary: Dict[str, Any] = {}
    ch6_all_ok: List[bool] = []
    for workflow in ("W1", "W2"):
        ch6_summary[workflow] = {}
        for strategy in BUFFER_STRATEGIES:
            counts = [r["ch6"][workflow][strategy]["poisoned_substitutions"] for r in per_seed]
            deltas = [r["ch6"][workflow][strategy]["poisoned_mean_abs_value_delta"] for r in per_seed]
            ch6_summary[workflow][strategy] = {
                "poisoned_substitutions": mean_ci95(counts),
                "poisoned_mean_abs_value_delta": mean_ci95(deltas),
            }
        plain_counts = [r["ch6"][workflow]["plain"]["poisoned_substitutions"] for r in per_seed]
        plain_ok = [c >= 1 for c in plain_counts]
        ch6_summary[workflow]["plain_has_poisoning_every_seed"] = all(plain_ok)
        ch6_all_ok.extend(plain_ok)
        for strategy in ("quarantine", "median_of_3"):
            mitigated_counts = [r["ch6"][workflow][strategy]["poisoned_substitutions"] for r in per_seed]
            strictly_lower = [m < p for m, p in zip(mitigated_counts, plain_counts)]
            ch6_summary[workflow][f"{strategy}_strictly_lower_every_seed"] = all(strictly_lower)
            ch6_all_ok.extend(strictly_lower)
    summary["ch6"] = ch6_summary

    # CH8 (robustness across 30 seeds x workflows, prereg/hypotheses.md):
    # for every hypothesis with a registered decision rule evaluated in
    # this sweep, did that rule hold in every seed (and, for CH6, every
    # workflow) it was checked on. CH7 is formal-track only (Phase 4) and
    # is not included here.
    summary["ch8_robustness"] = {
        "ch1_robust": all(ch1_ok),
        "ch2_robust": all(ch2_ok),
        "ch3_robust": all(ch3_ok),
        "ch4_robust": all(ch4_ok),
        "ch5_robust": all(ch5_ok),
        "ch6_robust": all(ch6_all_ok),
        "all_robust": all(ch1_ok) and all(ch2_ok) and all(ch3_ok) and all(ch4_ok) and all(ch5_ok) and all(ch6_all_ok),
    }

    SWEEP_SUMMARY_PATH.parent.mkdir(parents=True, exist_ok=True)
    SWEEP_SUMMARY_PATH.write_text(json.dumps(summary, indent=2))
    return summary


if __name__ == "__main__":
    run_sweep()
    summary = aggregate_sweep()
    print(json.dumps(summary, indent=2))
