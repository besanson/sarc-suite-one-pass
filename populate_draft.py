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
Populate the paper draft with generated numbers.

SEED = 26313
"""
import json
import re
from pathlib import Path
from typing import Dict


def populate_draft(draft_path: str, slots: Dict[str, str], output_path: str):
    """
    Read draft_path, replace [GENERATED: key] slots with values from slots dict.
    Write to output_path.
    """
    with open(draft_path) as f:
        content = f.read()

    original_content = content
    unfilled = []

    # Find all [GENERATED: key] slots
    slot_pattern = re.compile(r'\[GENERATED:\s*([^\]]+)\]')

    def replace_slot(match):
        key = match.group(1).strip()
        if key in slots:
            return slots[key]
        else:
            unfilled.append(key)
            return match.group(0)  # Leave as-is if not found

    content = slot_pattern.sub(replace_slot, content)

    # Write output
    with open(output_path, "w") as f:
        f.write(content)

    print(f"✓ Populated {len(slots) - len(unfilled)} slots")
    if unfilled:
        print(f"⚠ {len(unfilled)} unfilled slots: {unfilled}")
    else:
        print(f"✓ Zero unfilled slots")

    # Verify that only slots changed: walk the matches left-to-right and
    # confirm every non-slot byte-span is identical between original and
    # modified, and every slot span became exactly its substituted value
    # (a plain regex-strip comparison is NOT sufficient here, since it
    # compares "original with placeholders removed" against "modified with
    # values already inserted" — two structurally different strings that
    # can never match).
    only_slots_changed = True
    pos_orig = 0
    pos_mod = 0
    for match in slot_pattern.finditer(original_content):
        before = original_content[pos_orig:match.start()]
        if content[pos_mod:pos_mod + len(before)] != before:
            only_slots_changed = False
            break
        pos_mod += len(before)
        key = match.group(1).strip()
        value = slots.get(key, match.group(0))
        if content[pos_mod:pos_mod + len(value)] != value:
            only_slots_changed = False
            break
        pos_mod += len(value)
        pos_orig = match.end()
    else:
        tail = original_content[pos_orig:]
        only_slots_changed = content[pos_mod:] == tail

    if only_slots_changed:
        print(f"✓ Diff shows only slot substitutions")
    else:
        print(f"⚠ Diff shows additional changes beyond slots")

    return unfilled
