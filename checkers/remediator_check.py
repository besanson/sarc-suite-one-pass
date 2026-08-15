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

Off-grid probe (promoted per independent review, review/REVIEW.md
Section 5: "144/200 HEAD-derived off-grid points were non-confluent").
The declared grid above is a finite lattice of round numbers; the
independent review additionally probed continuous-valued points off that
lattice and found non-confluence there too, strengthening CH7's result
beyond the pre-registered grid. This module reruns that class of probe
itself (not a byte-for-byte replay of the reviewer's own run, which this
artifact cannot reproduce without their RNG draws): draw N continuous
points strictly inside the grid's outer bounds (never on a grid
coordinate), and check confluence on each with the same real remediation
functions.

The probe's seed was originally HEAD-derived (sha256 of the current git
commit), which made its published non-confluent count drift with every
commit -- the round-two independent review (review-r2/REVIEW-R2.md,
finding R2-N1) caught the response commit's paper reporting 140/200
while a plain rerun at the same commit produced 145/200, since a
`make formal` rerun after further commits landed re-derives the seed
from a different HEAD. The seed is now a fixed constant declared in
prereg/probe-seeds.json (dated after prereg-v1, since the probe itself
postdates prereg-v1 -- see that file's note), so the published count is
commit-stable. HEAD-derived randomness remains a reviewer's own tool for
independent adversarial probing, not this artifact's seeding source.

Each run of this checker also stamps its own output with
`generated_at_head_sha` (checkers/_provenance.py) -- the git HEAD
current when the checker actually ran -- so a committed checker artifact
whose content predates the commit it sits alongside (staleness) is
machine-detectable, per the same review finding.

SEED = 26313 (both the declared grid, which is exhaustive and doesn't
need a seed, and the off-grid probe below, which now uses the fixed
seed from prereg/probe-seeds.json -- coincidentally the same value as
this artifact's first registered sweep seed, not a re-use of sweep
state)
"""
from __future__ import annotations

import itertools
import json
from dataclasses import replace
from pathlib import Path
from typing import Any, Dict, List, Optional
import random

from checkers._provenance import head_sha, inputs_hash
from composition import ActionContext, _maybe_downroute, _remediated_context
from suite_sim import CARBON_PER_UNIT, COST_MULTIPLIER

OUT_PATH = Path("out/checkers/remediator_check.json")
PROBE_SEEDS_PATH = Path("prereg/probe-seeds.json")

# Round-three response (finding R3-F1): this checker's own generating
# inputs -- source, the two composition functions it reuses directly
# (via composition.py), suite_sim.py for the CARBON_PER_UNIT/
# COST_MULTIPLIER constants both remediation orders are computed with,
# and prereg/probe-seeds.json, this checker's actual off-grid-probe seed
# source (unlike compensation_check.py's, this one really does change
# the checker's committed result if edited). engines.lock is included
# uniformly across every checker's stamp (see checkers/_provenance.py).
INPUT_FILES = [
    Path("checkers/remediator_check.py"),
    Path("checkers/_provenance.py"),
    Path("composition.py"),
    Path("suite_sim.py"),
    Path("prereg/probe-seeds.json"),
    Path("engines.lock"),
]

QTY_GRID = [10.0, 50.0, 100.0]
CORRUPTED_COST_GRID = [5.0, 10.0, 20.0]
GOVERNED_COST_GRID = [5.0, 10.0, 20.0]
COST_BUDGET_GRID = [60.0, 300.0, 1e12]
CARBON_BUDGET_GRID = [10.0, 50.0, 1e12]


def load_off_grid_probe_spec(path: Path = PROBE_SEEDS_PATH) -> Dict[str, Any]:
    return json.loads(path.read_text())["ch7_off_grid_probe"]


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


def random_off_grid_points(n: int, seed: int) -> List[Dict[str, float]]:
    """N continuous-valued points strictly inside the declared grid's
    outer bounds, never landing on a grid coordinate -- deterministic
    given seed (a fixed constant from prereg/probe-seeds.json in normal
    use, not HEAD-derived -- see this module's docstring and that
    file's dated note), so the probe is reproducible AND commit-stable,
    while still not itself part of the pre-registered fixed grid.
    Mirrors the independent review's own off-grid probe methodology
    (review/REVIEW.md Section 5)."""
    rng = random.Random(seed)
    points = []
    for _ in range(n):
        points.append({
            "qty": rng.uniform(min(QTY_GRID) + 0.01, max(QTY_GRID) - 0.01),
            "corrupted_unit_cost": rng.uniform(min(CORRUPTED_COST_GRID) + 0.01, max(CORRUPTED_COST_GRID) - 0.01),
            "governed_unit_cost": rng.uniform(min(GOVERNED_COST_GRID) + 0.01, max(GOVERNED_COST_GRID) - 0.01),
            "cost_budget": rng.uniform(min(COST_BUDGET_GRID) + 0.01, 1000.0),
            "carbon_budget": rng.uniform(min(CARBON_BUDGET_GRID) + 0.01, 1000.0),
        })
    return points


def _off_grid_probe(points: List[Dict[str, float]]) -> Dict[str, Any]:
    non_confluent: List[Dict[str, Any]] = []
    for p in points:
        a = _order_a_substitute_then_downroute(
            p["qty"], p["corrupted_unit_cost"], p["governed_unit_cost"], p["cost_budget"], p["carbon_budget"]
        )
        b = _order_b_downroute_then_substitute(
            p["qty"], p["corrupted_unit_cost"], p["governed_unit_cost"], p["cost_budget"], p["carbon_budget"]
        )
        agree = _close(a.proposed_qty, b.proposed_qty) and _close(a.order_value, b.order_value)
        if not agree:
            non_confluent.append({
                **p,
                "order_a_substitute_then_downroute": {"qty": a.proposed_qty, "order_value": a.order_value},
                "order_b_downroute_then_substitute": {"qty": b.proposed_qty, "order_value": b.order_value},
            })
    return {
        "n_probes": len(points),
        "non_confluent_count": len(non_confluent),
        "confluent_count": len(points) - len(non_confluent),
        "sample_non_confluent": non_confluent[0] if non_confluent else None,
    }


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

    probe_spec = load_off_grid_probe_spec()
    off_grid_points = random_off_grid_points(probe_spec["n_probes"], probe_spec["seed"])
    off_grid = _off_grid_probe(off_grid_points)

    result: Dict[str, Any] = {
        "grid_points_checked": grid_points,
        "confluent": confluent,
        "counterexample_count": len(counterexamples),
        "ch7_registered_outcome": "confluent" if confluent else "non_confluent",
        "sample_counterexample": counterexamples[0] if counterexamples else None,
        "all_counterexamples": counterexamples,
        "generated_at_head_sha": head_sha(),
        "inputs_hash": inputs_hash(INPUT_FILES),
        "off_grid_probe": {
            "seed": probe_spec["seed"],
            "seed_source": "prereg/probe-seeds.json (fixed, commit-stable -- round-two review finding R2-N1)",
            **off_grid,
            "attribution": (
                "Promoted per independent review, review/REVIEW.md Section 5 "
                "(\"144/200 HEAD-derived off-grid points were non-confluent\"); "
                "this artifact's own rerun uses a fixed declared seed (not "
                "HEAD-derived, since round two) and will not in general "
                "reproduce that exact count, but tests the same class of "
                "continuous off-grid points and is stable across commits."
            ),
        },
        "note": (
            "confluent across the finite grid: order of remediation does not "
            "matter, either order is safe to register as canonical."
            if confluent else
            "non-confluent: at least one concrete instance exists where "
            "substitute-then-downroute and downroute-then-substitute reach "
            "different final actions. This is the formal justification for "
            "prereg/w2-workflow.md's fixed ordering (evidence gate first, "
            "then resource gate) rather than leaving the order unspecified. "
            "The off-grid probe (see off_grid_probe) strengthens this result "
            "beyond the pre-registered grid, per the independent review."
        ),
    }
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(json.dumps(result, indent=2))
    return result


if __name__ == "__main__":
    result = run()
    print(json.dumps({k: v for k, v in result.items() if k != "all_counterexamples"}, indent=2))
