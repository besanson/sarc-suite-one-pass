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
SARC Suite One-Pass Demo: decision stream, economics, and the declared
per-class defect injector.

SEED = 26313
"""
from __future__ import annotations

import csv
import random
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional

from sarc_dq.records import EvidenceRecord, RecordMetadata

SEED = 26313
WARMUP = 35
INJECTION_PROBABILITY = 0.02
COST_MULTIPLIER = 1.2  # est_cost_eur = order_value * COST_MULTIPLIER
CARBON_PER_UNIT = 0.5  # est_carbon_g = proposed_qty * CARBON_PER_UNIT
TRUE_COST_RATIO = 0.6  # true unit cost = median observed price * TRUE_COST_RATIO
TRAILING_WINDOW = 28
NEWSVENDOR_QUANTILE = 0.75

# R7: fixed iteration order, per-class independent probability, at most one
# class fires per decision (first-fires-wins in this order).
DEFECT_CLASSES = [
    "stale_master_data",
    "superseded_golden_record",
    "cross_source_contradiction",
    "schema_drift",
    "missing_mandatory_field",
    "lineage_missing",
    "plausible_outlier",
    "plausible_outlier_high",  # prereg/contamination.md: a second, independent
    # declared-uncovered class (identical corruption recipe) added at the
    # same 0.02 per-class rate specifically to make the buffer-contamination
    # study (CH6) easy to trigger without perturbing the original seven
    # classes' own per-class rates.
]


@dataclass(frozen=True)
class DecisionPlan:
    decision_id: int
    day: int
    date: str
    sku: str
    role: str
    proposed_qty: float
    true_cost: float
    read_cost: float
    evidence_records: List[EvidenceRecord]
    injected_defect: Optional[str]
    workflow: str = "W1"


class RetailSimulation:
    """Loads the derived retail data and builds the deterministic decision plan."""

    def __init__(self, data_path: str = "data/open_retail_daily.csv"):
        self.data_path = Path(data_path)
        self.rows = self._load_rows()
        self.dates = sorted({r["date"] for r in self.rows})
        self.skus = sorted({r["sku"] for r in self.rows})
        self.qty_by_sku_date: Dict[str, Dict[str, float]] = defaultdict(dict)
        for r in self.rows:
            self.qty_by_sku_date[r["sku"]][r["date"]] = r["qty"]
        self.sku_true_cost: Dict[str, float] = self._compute_true_costs()

    def _load_rows(self) -> List[Dict[str, object]]:
        rows = []
        with open(self.data_path, newline="") as f:
            for row in csv.DictReader(f):
                rows.append(
                    {
                        "sku": row["sku"],
                        "date": row["date"],
                        "qty": float(row["qty"]),
                        "unit_price": float(row["unit_price"]),
                    }
                )
        return rows

    def _compute_true_costs(self) -> Dict[str, float]:
        prices_by_sku: Dict[str, List[float]] = defaultdict(list)
        for r in self.rows:
            prices_by_sku[r["sku"]].append(r["unit_price"])
        costs = {}
        for sku, prices in prices_by_sku.items():
            prices = sorted(prices)
            median_price = prices[len(prices) // 2]
            costs[sku] = median_price * TRUE_COST_RATIO
        return costs

    def _proposed_qty(self, sku: str, date_idx: int) -> float:
        """Trailing-window quantile of recent daily quantities (economics
        formula unchanged from the original design; not among the enumerated
        repair defects)."""
        window_dates = self.dates[max(0, date_idx - TRAILING_WINDOW + 1) : date_idx + 1]
        recent = [self.qty_by_sku_date[sku][d] for d in window_dates if d in self.qty_by_sku_date[sku]]
        if not recent:
            return 1.0
        recent.sort()
        idx = min(int(NEWSVENDOR_QUANTILE * len(recent)), len(recent) - 1)
        return recent[idx]

    # -- decision plan (deterministic given seed) ---------------------------

    def generate_plan(
        self,
        seed: int,
        unauthorized_role_rate: float,
        authorized_roles: List[str],
        unauthorized_role: str = "agent-unauthorized",
        workflow: str = "W1",
        commitment_period_days: int = 1,
    ) -> List[DecisionPlan]:
        """workflow/commitment_period_days implement W2 (prereg/w2-workflow.md):
        a decision commits once every commitment_period_days days per SKU
        (7 for W2's weekly commitment) instead of daily. The newsvendor
        quantile rule itself is unchanged — W2 just evaluates it less
        often, anchored at the start of each commitment window."""
        rng = random.Random(seed)
        plan: List[DecisionPlan] = []
        decision_id = 0
        for date_idx, date in enumerate(self.dates):
            if date_idx < WARMUP:
                continue
            if (date_idx - WARMUP) % commitment_period_days != 0:
                continue
            for sku in self.skus:
                if date not in self.qty_by_sku_date[sku]:
                    continue
                true_cost = self.sku_true_cost[sku]
                qty = self._proposed_qty(sku, date_idx)
                read_cost, evidence_records, defect = self._inject(rng, sku, date_idx, true_cost)
                role = (
                    unauthorized_role
                    if rng.random() < unauthorized_role_rate
                    else rng.choice(authorized_roles)
                )
                plan.append(
                    DecisionPlan(
                        decision_id=decision_id,
                        day=date_idx,
                        date=date,
                        sku=sku,
                        role=role,
                        proposed_qty=qty,
                        true_cost=true_cost,
                        read_cost=read_cost,
                        evidence_records=evidence_records,
                        injected_defect=defect,
                        workflow=workflow,
                    )
                )
                decision_id += 1
        return plan

    def _inject(self, rng: random.Random, sku: str, day: int, true_cost: float):
        chosen: Optional[str] = None
        for cls in DEFECT_CLASSES:
            if rng.random() < INJECTION_PROBABILITY:
                chosen = cls
                break

        if chosen is None:
            record = EvidenceRecord(
                record_id=f"{sku}-primary",
                payload={"sku": sku, "unit_cost": true_cost, "currency": "GBP"},
                metadata=RecordMetadata(
                    source="erp.pricing", as_of_day=day, retrieved_day=day, version=2,
                    lineage=("supplier_feed:SKU",),
                ),
            )
            return true_cost, [record], None

        if chosen == "stale_master_data":
            staleness = rng.randint(45, 150)
            corrupted = true_cost * rng.uniform(0.55, 0.9)
            record = EvidenceRecord(
                record_id=f"{sku}-primary",
                payload={"sku": sku, "unit_cost": corrupted, "currency": "GBP"},
                metadata=RecordMetadata(
                    source="erp.pricing", as_of_day=day - staleness, retrieved_day=day,
                    version=2, lineage=("supplier_feed:SKU",),
                ),
            )
            return corrupted, [record], chosen

        if chosen == "superseded_golden_record":
            v2 = EvidenceRecord(
                record_id=f"{sku}-golden",
                payload={"sku": sku, "unit_cost": true_cost, "currency": "GBP"},
                metadata=RecordMetadata(
                    source="erp.pricing", as_of_day=day, retrieved_day=day, version=2,
                    lineage=("supplier_feed:SKU",),
                ),
            )
            v1 = EvidenceRecord(
                record_id=f"{sku}-golden",
                payload={"sku": sku, "unit_cost": true_cost * rng.uniform(0.7, 0.95), "currency": "GBP"},
                metadata=RecordMetadata(
                    source="erp.pricing", as_of_day=day - 10, retrieved_day=day, version=1,
                    lineage=("supplier_feed:SKU",),
                ),
            )
            return true_cost, [v2, v1], chosen

        if chosen == "cross_source_contradiction":
            deviation = rng.choice([1.03, 1.05, 0.95, 0.97])
            primary = EvidenceRecord(
                record_id=f"{sku}-primary",
                payload={"sku": sku, "unit_cost": true_cost, "currency": "GBP"},
                metadata=RecordMetadata(
                    source="erp.pricing", as_of_day=day, retrieved_day=day, version=2,
                    lineage=("supplier_feed:SKU",),
                ),
            )
            alt = EvidenceRecord(
                record_id=f"{sku}-primary",
                payload={"sku": sku, "unit_cost": true_cost * deviation, "currency": "GBP"},
                metadata=RecordMetadata(
                    source="supplier_api", as_of_day=day, retrieved_day=day, version=2,
                    lineage=("api.supplier",),
                ),
            )
            return true_cost, [primary, alt], chosen

        if chosen == "schema_drift":
            record = EvidenceRecord(
                record_id=f"{sku}-primary",
                payload={"sku": sku, "unit_cost": str(true_cost), "currency": "GBP"},
                metadata=RecordMetadata(
                    source="erp.pricing", as_of_day=day, retrieved_day=day, version=2,
                    lineage=("supplier_feed:SKU",),
                ),
            )
            return true_cost, [record], chosen

        if chosen == "missing_mandatory_field":
            record = EvidenceRecord(
                record_id=f"{sku}-primary",
                payload={"sku": sku, "unit_cost": true_cost},
                metadata=RecordMetadata(
                    source="erp.pricing", as_of_day=day, retrieved_day=day, version=2,
                    lineage=("supplier_feed:SKU",),
                ),
            )
            return true_cost, [record], chosen

        if chosen == "lineage_missing":
            record = EvidenceRecord(
                record_id=f"{sku}-primary",
                payload={"sku": sku, "unit_cost": true_cost, "currency": "GBP"},
                metadata=RecordMetadata(
                    source="", as_of_day=day, retrieved_day=day, version=2, lineage=(),
                ),
            )
            return true_cost, [record], chosen

        if chosen in ("plausible_outlier", "plausible_outlier_high"):
            # Identical corruption recipe (Appendix B): unit_cost x 2.5,
            # clean fresh metadata, clean lineage. plausible_outlier_high
            # is a second independent class at the same rate (prereg/
            # contamination.md) so the buffer-contamination study has a
            # dedicated, isolable injection axis; it is not a *different*
            # defect mechanically, only a separately-counted one.
            corrupted = true_cost * 2.5
            record = EvidenceRecord(
                record_id=f"{sku}-primary",
                payload={"sku": sku, "unit_cost": corrupted, "currency": "GBP"},
                metadata=RecordMetadata(
                    source="erp.pricing", as_of_day=day, retrieved_day=day, version=2,
                    lineage=("supplier_feed:SKU",),
                ),
            )
            return corrupted, [record], chosen

        raise AssertionError(f"unhandled defect class {chosen!r}")  # pragma: no cover

    # -- scenario economics calibration (generated, not guessed) ------------

    def calibrate(self, plan: List[DecisionPlan]) -> Dict[str, float]:
        """Compute the true distribution of order economics over a plan so
        scenario budgets/caps can be derived rather than hand-picked."""
        order_values = sorted(p.proposed_qty * p.read_cost for p in plan)
        est_costs = sorted(v * COST_MULTIPLIER for v in order_values)
        est_carbons = sorted(p.proposed_qty * CARBON_PER_UNIT for p in plan)

        def pct(seq, q):
            idx = min(int(q * len(seq)), len(seq) - 1)
            return seq[idx]

        return {
            "max_order_value": order_values[-1],
            "max_est_cost": est_costs[-1],
            "max_est_carbon": est_carbons[-1],
            "median_est_cost": pct(est_costs, 0.5),
            "median_est_carbon": pct(est_carbons, 0.5),
            "median_order_value": pct(order_values, 0.5),
        }
