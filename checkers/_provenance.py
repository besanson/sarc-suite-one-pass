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
Shared provenance helper for checkers/ (round-two independent review,
finding R2-N1/R2-F1(a)): every checker's output JSON is stamped with the
git HEAD commit at generation time, under the key
"generated_at_head_sha". This makes staleness -- a committed checker
artifact whose content was actually produced at an earlier commit than
the one it now sits alongside -- machine-detectable rather than
something only a manual `git diff` after a rerun surfaces.

This is a generation-time provenance stamp, distinct from any HEAD-
derived randomness a checker might otherwise use. As of the round-two
response, no checker seeds its own random probes from HEAD any longer
(see prereg/probe-seeds.json and its "dated" note) -- HEAD-derived
sampling remains a reviewer tool, not something this artifact's own
published numbers depend on.
"""
from __future__ import annotations

import subprocess


def head_sha() -> str:
    return subprocess.run(
        ["git", "rev-parse", "HEAD"], capture_output=True, text=True, check=True
    ).stdout.strip()
