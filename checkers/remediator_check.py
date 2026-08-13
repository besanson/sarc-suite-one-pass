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
Phase 4 / V2 gate, CH7 (prereg/hypotheses.md): "with two remediation
operators active, evidence substitution and resource downroute quantity
scaling, either order-independence (confluence) holds across the
exhaustive finite model and the empirical grid, or at least one concrete
non-confluent instance exists. ... the decision rule is the checker's
output."

This module IS that decision rule. It reuses the real remediation
functions from composition.py (`_remediated_context`, `_maybe_downroute`)
directly -- it does not reimplement their arithmetic -- and applies them
in both possible orders over a finite grid of (qty, corrupted unit cost,
governed/clean unit cost, cost budget, carbon budget) combinations:

  order A (substitute then downroute) -- what composition.py's
  remediate_regate actually runs, per prereg/w2-workflow.md's fixed
  ordering ("evidence gate first, then resource gate").
  order B (downroute then substitute) -- the untried alternative order.

If both orders reach the same final (qty, order_value) on every grid
point, the operators commute and CH7 is registered as confluent. If any
grid point disagrees, that point is recorded as a concrete counterexample
and CH7 is registered as non-confluent -- which, if it occurs, is itself
the reason a FIXED order had to be pre-registered rather than left
order-independent.

SEED = 26313 (not used here -- this checker is exhaustive over a finite
grid, not sampled)
"""
from __future__ import annotations

import itertools
import json
from dataclasses import replace
from pathlib import Path
from typing import Any, Dict, List, Optional

from composition import ActionContext, _maybe_downroute, _remediated_context
from suite_sim import CARBON_PER_UNIT, COST_MULTIPLIER

OUT_PATH = Path("out/checkers/remediator_check.json")

QTY_GRID = [10.0, 50.0, 100.0]
CORRUPTED_COST_GRID = [5.0, 10.0, 20.0]
GOVERNED_COST_GRID = [5.0, 10.0, 20.0]
COST_BUDGET_GRID = [60.0, 300.0, 1e12]
CARBON_BUDGET_GRID = [10.0, 50.0, 1e12]


def _base_ctx(qty: float, unit_cost: float) -> ActionContext:
    order_value = qty * unit_cost
    return ActionContext(
        agent_id="checker", role="checker", sku="CHECKER-SKU", day=0,
        proposed_qty=qty, order_value=order_value,
        est_cost_eur=order_value * COST_MULTIPLIER, est_carbon_g=qty * CARBON_PER_UNIT,
    )


def _order_a_substitute_then_downroute(
    qty: float, corrupted_cost: float, governed_cost: float, cost_budget: float, carbon_budget: float,
) -> ActionContext:
    ctx0 = _base_ctx(qty, corrupted_cost)
    ctx1 = _remediated_context(ctx0, governed_cost, CARBON_PER_UNIT, COST_MULTIPLIER)
    ctx2, _ = _maybe_downroute(ctx1, cost_budget, carbon_budget, CARBON_PER_UNIT, COST_MULTIPLIER, "W2")
    return ctx2


def _order_b_downroute_then_substitute(
    qty: float, corrupted_cost: float, governed_cost: float, cost_budget: float, carbon_budget: float,
) -> ActionContext:
    ctx0 = _base_ctx(qty, corrupted_cost)
    ctx1, _ = _maybe_downroute(ctx0, cost_budget, carbon_budget, CARBON_PER_UNIT, COST_MULTIPLIER, "W2")
    ctx2 = _remediated_context(ctx1, governed_cost, CARBON_PER_UNIT, COST_MULTIPLIER)
    return ctx2


def _close(a: float, b: float, tol: float = 1e-9) -> bool:
    return abs(a - b) <= tol * max(1.0, abs(a), abs(b))


def run() -> Dict[str, Any]:
    grid_points = 0
    counterexamples: List[Dict[str, Any]] = []
    for qty, corrupted, governed, cost_budget, carbon_budget in itertools.product(
        QTY_GRID, CORRUPTED_COST_GRID, GOVERNED_COST_GRID, COST_BUDGET_GRID, CARBON_BUDGET_GRID
    ):
        grid_points += 1
        a = _order_a_substitute_then_downroute(qty, corrupted, governed, cost_budget, carbon_budget)
        b = _order_b_downroute_then_substitute(qty, corrupted, governed, cost_budget, carbon_budget)
        agree = _close(a.proposed_qty, b.proposed_qty) and _close(a.order_value, b.order_value)
        if not agree:
            counterexamples.append({
                "qty": qty, "corrupted_unit_cost": corrupted, "governed_unit_cost": governed,
                "cost_budget": cost_budget, "carbon_budget": carbon_budget,
                "order_a_substitute_then_downroute": {"qty": a.proposed_qty, "order_value": a.order_value},
                "order_b_downroute_then_substitute": {"qty": b.proposed_qty, "order_value": b.order_value},
            })

    confluent = len(counterexamples) == 0
    result: Dict[str, Any] = {
        "grid_points_checked": grid_points,
        "confluent": confluent,
        "counterexample_count": len(counterexamples),
        "ch7_registered_outcome": "confluent" if confluent else "non_confluent",
        "sample_counterexample": counterexamples[0] if counterexamples else None,
        "all_counterexamples": counterexamples,
        "note": (
            "confluent across the finite grid: order of remediation does not "
            "matter, either order is safe to register as canonical."
            if confluent else
            "non-confluent: at least one concrete instance exists where "
            "substitute-then-downroute and downroute-then-substitute reach "
            "different final actions. This is the formal justification for "
            "prereg/w2-workflow.md's fixed ordering (evidence gate first, "
            "then resource gate) rather than leaving the order unspecified."
        ),
    }
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(json.dumps(result, indent=2))
    return result


if __name__ == "__main__":
    result = run()
    print(json.dumps({k: v for k, v in result.items() if k != "all_counterexamples"}, indent=2))
