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
Phase 2 latency microbenchmark: per-gate and composed per-decision cost.
Printed to the console and stored in out/quality.json under "latency".

Not a correctness check — a fixed, small, deterministic workload
(SEED = 26313) timed with time.perf_counter(). Uses the real engines,
same as everywhere else in this artifact.
"""
from __future__ import annotations

import json
import statistics
import time
from pathlib import Path

from composition import (
    ActionContext,
    build_green_engines,
    evaluate_dq,
    evaluate_green,
    evaluate_sarc_pag,
    load_sarc_spec,
)
from sarc_dq.dq_spec import load_spec as load_dq_spec
from sarc_dq.gate import GovernedBuffer, PreActionGate as DQPreActionGate
from sarc_dq.records import EvidenceRecord, RecordMetadata
from suite_sim import CARBON_PER_UNIT, COST_MULTIPLIER, RetailSimulation

N_DECISIONS = 500


def _time_calls(fn, n: int) -> dict:
    samples = []
    for _ in range(n):
        start = time.perf_counter()
        fn()
        samples.append(time.perf_counter() - start)
    samples.sort()
    return {
        "n": n,
        "mean_us": statistics.mean(samples) * 1e6,
        "median_us": statistics.median(samples) * 1e6,
        "p95_us": samples[int(0.95 * n)] * 1e6,
        "min_us": samples[0] * 1e6,
        "max_us": samples[-1] * 1e6,
    }


def run_benchmark() -> dict:
    sim = RetailSimulation()
    plan = sim.generate_plan(seed=26313, unauthorized_role_rate=0.0, authorized_roles=["agent-replenish"])[:N_DECISIONS]

    dq_spec = load_dq_spec()
    sarc_spec = load_sarc_spec("specs/authority.yaml")
    green_engines = build_green_engines(sim.sku_true_cost, CARBON_PER_UNIT, COST_MULTIPLIER)
    buffer = GovernedBuffer(values=dict(sim.sku_true_cost))
    dq_gate = DQPreActionGate(spec=dq_spec, buffer=buffer)

    from composition import CompositionEngine
    engine = CompositionEngine(
        dq_gate, sarc_spec, green_engines, CARBON_PER_UNIT, COST_MULTIPLIER,
        initial_buffer_values=dict(sim.sku_true_cost),
    )

    idx = {"i": 0}

    def next_plan():
        p = plan[idx["i"] % len(plan)]
        idx["i"] += 1
        return p

    def dq_call():
        p = next_plan()
        evaluate_dq(dq_gate, p.evidence_records)

    def sarc_call():
        p = next_plan()
        evaluate_sarc_pag(sarc_spec, "agent-replenish", ("agent-replenish",), p.proposed_qty * p.read_cost, 1e12)

    def green_call():
        p = next_plan()
        evaluate_green(green_engines, p.sku, p.proposed_qty * p.read_cost * COST_MULTIPLIER, 1e12, 1e12)

    def composed_call():
        p = next_plan()
        ctx = ActionContext(
            agent_id=f"agent-{p.sku}", role="agent-replenish", sku=p.sku, day=p.day,
            proposed_qty=p.proposed_qty, order_value=p.proposed_qty * p.read_cost,
            est_cost_eur=p.proposed_qty * p.read_cost * COST_MULTIPLIER,
            est_carbon_g=p.proposed_qty * CARBON_PER_UNIT,
        )
        engine.remediate_regate(p.decision_id, ctx, p.evidence_records, ("agent-replenish",), 1e12, 1e12, 1e12)

    results = {
        "n_decisions_in_workload": len(plan),
        "per_gate": {
            "dq": _time_calls(dq_call, N_DECISIONS),
            "sarc": _time_calls(sarc_call, N_DECISIONS),
            "green": _time_calls(green_call, N_DECISIONS),
        },
        "composed_remediate_regate": _time_calls(composed_call, N_DECISIONS),
    }
    return results


if __name__ == "__main__":
    results = run_benchmark()
    print(json.dumps(results, indent=2))

    out_dir = Path("out")
    out_dir.mkdir(exist_ok=True)
    quality_path = out_dir / "quality.json"
    quality = json.loads(quality_path.read_text()) if quality_path.exists() else {}
    quality["latency"] = results
    quality_path.write_text(json.dumps(quality, indent=2))
    print(f"\nWrote {quality_path}")
