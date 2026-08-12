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
Generated artifact manifest (R5): engine versions via importlib.metadata,
commit hashes via `git -C <repo> rev-parse HEAD`, data sha256, licences.
No hard-coded version strings.

SEED = 26313
"""
from __future__ import annotations

import importlib.metadata as importlib_metadata
import os
import subprocess
from typing import Dict, List, Optional

# Candidate local clone directories per Step 0's `git clone` instructions,
# tried in order (a fresh Step-0 follower gets the first entry; our own
# session used an alternate name for the sarc-governance clone to avoid a
# collision with this repo's own directory, hence the second candidate).
ENGINE_REPO_CANDIDATES: Dict[str, List[str]] = {
    "sarc-dq": ["../dqSarc"],
    "sarc-governance": ["../sarc-governance", "../sarc-governance-engine"],
    "green-sarc": ["../Greensarc"],
}


def _first_existing(candidates: List[str]) -> Optional[str]:
    for c in candidates:
        if os.path.isdir(c):
            return c
    return None


def _git_head(repo_dir: str) -> str:
    result = subprocess.run(
        ["git", "-C", repo_dir, "rev-parse", "HEAD"],
        capture_output=True, text=True, check=True,
    )
    return result.stdout.strip()


def _license(pkg: str) -> str:
    try:
        meta = importlib_metadata.metadata(pkg)
    except importlib_metadata.PackageNotFoundError:
        return "unknown"
    lic = meta.get("License")
    if lic and lic not in ("UNKNOWN", ""):
        return lic
    for classifier in meta.get_all("Classifier") or []:
        if classifier.startswith("License ::"):
            return classifier.split("::")[-1].strip()
    return "unknown"


def build_manifest(data_sha256: str, seed: int) -> Dict[str, object]:
    engines = {}
    for pkg in ("sarc-dq", "sarc-governance", "green-sarc"):
        version = importlib_metadata.version(pkg)
        repo_dir = _first_existing(ENGINE_REPO_CANDIDATES[pkg])
        commit = _git_head(repo_dir) if repo_dir else "unknown"
        engines[pkg] = {
            "version": version,
            "commit": commit,
            "license": _license(pkg),
        }
    return {
        "seed": seed,
        "engines": engines,
        "data_sha256": data_sha256,
        "artifact_license": "Apache-2.0",
    }
