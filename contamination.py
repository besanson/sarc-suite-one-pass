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
CH6 (prereg/contamination.md): the poisoned-substitution metric and the
two governed-buffer mitigation adapters.

Both mitigation classes are duck-typed to sarc_dq.gate.GovernedBuffer's
put(key, value)/substitute(key) -> value|None interface and implemented
entirely in this repo — the engine's own GovernedBuffer is never
subclassed or modified.

The poisoned-substitution metric is computed purely from ground-truth
DecisionPlan labels (suite_sim.DecisionPlan.injected_defect) and the
already-produced remediate_regate Evidence Set lines, never by reaching
into gate/buffer internals — matching prereg/contamination.md's "This is
computable purely from run_log.jsonl's ground-truth labels" requirement.

SEED = 26313
"""
from __future__ import annotations

import math
from collections import defaultdict
from typing import Any, Dict, List, Optional, Sequence

UNCOVERED_CLASSES = ("plausible_outlier", "plausible_outlier_high")


# ---------------------------------------------------------------------------
# Mitigation 1: quarantine window.
# ---------------------------------------------------------------------------


class QuarantineWindowBuffer:
    """A buffer write becomes eligible for substitution only after K=3
    subsequent *consistent* (identical-value) admitted writes for that
    SKU. Until eligible, substitution falls back to the prior eligible
    value (or None, if none exists yet — the real gate's own
    no-buffer-substitute rule then falls back to block).
    """

    K = 3

    def __init__(self, values: Optional[Dict[str, float]] = None) -> None:
        self._eligible: Dict[str, float] = {}
        self._streak: Dict[str, List[float]] = defaultdict(list)
        for key, value in (values or {}).items():
            # Seed values are the engine's declared known-good state, so
            # they start eligible immediately (matches GovernedBuffer's
            # own seeding behavior).
            self._streak[key] = [value] * self.K
            self._eligible[key] = value

    def put(self, key: str, value: float) -> None:
        streak = self._streak[key]
        if streak and streak[-1] == value:
            streak.append(value)
        else:
            streak[:] = [value]
        if len(streak) >= self.K:
            self._eligible[key] = value

    def substitute(self, key: str) -> Optional[float]:
        return self._eligible.get(key)


# ---------------------------------------------------------------------------
# Mitigation 2: median-of-3.
# ---------------------------------------------------------------------------


class MedianOf3Buffer:
    """Substitute the median of the last three eligible buffer values for
    a SKU, instead of a single scalar — keeps a short rolling history per
    SKU rather than one governed value.
    """

    def __init__(self, values: Optional[Dict[str, float]] = None) -> None:
        self._history: Dict[str, List[float]] = defaultdict(list)
        for key, value in (values or {}).items():
            self._history[key] = [value]

    def put(self, key: str, value: float) -> None:
        history = self._history[key]
        history.append(value)
        del history[:-3]

    def substitute(self, key: str) -> Optional[float]:
        history = self._history.get(key)
        if not history:
            return None
        ordered = sorted(history)
        return ordered[len(ordered) // 2]


# ---------------------------------------------------------------------------
# Poisoned-substitution metric.
# ---------------------------------------------------------------------------


def compute_poisoned_substitutions(
    plan: Sequence[Any], lines: Sequence[Dict[str, Any]]
) -> Dict[str, Any]:
    """plan and lines are the matching (same order, same length)
    DecisionPlan list and remediate_regate Evidence Set lines for one
    scenario/seed/buffer-strategy run.

    A decision is a *buffer write* iff its dq gate verdict is "admit" —
    composition.evaluate_dq only ever calls buffer.put on an admit,
    whether that admit came from the original evidence (phase 1) or the
    remediated evidence (phase 2). The written value is the substituted
    value when evidence_substitution triggered on this same decision
    (phase 2 admits the remediated/clean value), else the original
    evidence's value (composition passes evidence[0], whose unit_cost is
    exactly the plan's own read_cost).

    A decision is a *substitution* iff remediation.evidence_substitution
    is not None (dq phase 1 returned quarantine_substitute).

    For the plain (unmitigated) buffer, "the buffer value used" is always
    the single most recent write. The mitigation adapters do not follow
    that rule internally (a quarantined value may be several writes
    stale; a median-of-3 value may be the middle of three writes) — so
    "traces back to a prior admitted decision" is resolved by matching
    the *value actually used* (evidence_substitution.substituted_value,
    already present in the Evidence Set line — not a gate-internal
    lookup) against the write history, walking backward from strictly
    before decision d and taking the most recent write whose written
    value equals it. A substitution is *poisoned* iff that traced-back
    write came from a decision whose injected_defect was an
    uncovered-by-DQ class (plausible_outlier or plausible_outlier_high)
    — prereg/contamination.md.
    """
    write_history: Dict[str, List[tuple]] = defaultdict(list)  # sku -> [(decision_id, injected_defect, written_value)]
    poisoned_events: List[Dict[str, Any]] = []
    substitutions = 0

    for p, line in zip(plan, lines):
        sku = p.sku
        sub = line["remediation"]["evidence_substitution"]

        if sub is not None:
            substitutions += 1
            used_value = sub["substituted_value"]
            history = write_history[sku]
            traced = next((e for e in reversed(history) if e[2] == used_value), None)
            if traced is None and history:
                traced = history[-1]  # best-effort: value didn't match exactly (unexpected)
            if traced is not None and traced[1] in UNCOVERED_CLASSES:
                delta = abs(used_value - p.true_cost)
                poisoned_events.append(
                    {
                        "decision_id": p.decision_id,
                        "sku": sku,
                        "poisoning_decision_id": traced[0],
                        "poisoning_defect": traced[1],
                        "substituted_value": used_value,
                        "true_cost": p.true_cost,
                        "abs_value_delta": delta,
                    }
                )

        if line["gates"]["dq"]["verdict"] == "admit":
            written_value = sub["substituted_value"] if sub is not None else p.read_cost
            write_history[sku].append((p.decision_id, p.injected_defect, written_value))

    deltas = [event["abs_value_delta"] for event in poisoned_events]
    # Order-stable per round-two independent review finding R2-N3
    # ("poisoned_mean_abs_value_delta" differed by one ULP between two
    # replays of the same seed): math.fsum over explicitly sorted
    # deltas, not naive sum()/len(), so the result is independent of
    # whatever order poisoned_events happened to be appended in.
    mean_delta = math.fsum(sorted(deltas)) / len(deltas) if deltas else 0.0

    return {
        "substitutions": substitutions,
        "poisoned_substitutions": len(poisoned_events),
        "poisoned_mean_abs_value_delta": mean_delta,
        "poisoned_events": poisoned_events,
    }
