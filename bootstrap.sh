#!/usr/bin/env bash
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
#
# Bootstrap: clone the three engine repos as siblings of this repo AT THE
# PINNED COMMITS recorded in engines.lock, editable-install them, and
# install the test/quality toolchain. Idempotent: safe to re-run.
#
# SEED = 26313
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$SCRIPT_DIR"
PARENT_DIR="$(dirname "$REPO_ROOT")"
LOCKFILE="$REPO_ROOT/engines.lock"

if [ ! -f "$LOCKFILE" ]; then
    echo "engines.lock not found at $LOCKFILE" >&2
    exit 1
fi

clone_or_checkout() {
    local name="$1" url="$2" sha="$3"
    local dest="$PARENT_DIR/$name"
    if [ -d "$dest/.git" ]; then
        echo "[$name] already cloned at $dest; fetching and checking out pinned commit..."
        git -C "$dest" fetch origin "$sha" --depth 1 2>/dev/null || git -C "$dest" fetch origin
        git -C "$dest" checkout --quiet "$sha"
    else
        echo "[$name] cloning $url at $sha..."
        git clone --quiet "$url" "$dest"
        git -C "$dest" checkout --quiet "$sha"
    fi
    local actual
    actual="$(git -C "$dest" rev-parse HEAD)"
    if [ "$actual" != "$sha" ]; then
        echo "[$name] FAILED to pin: expected $sha, got $actual" >&2
        exit 1
    fi
    echo "[$name] pinned at $actual"
}

# Parse engines.lock (simple "name url sha" lines, '#' comments allowed).
while IFS= read -r line; do
    line="${line%%#*}"
    line="$(echo "$line" | xargs || true)"
    [ -z "$line" ] && continue
    name=$(echo "$line" | awk '{print $1}')
    url=$(echo "$line" | awk '{print $2}')
    sha=$(echo "$line" | awk '{print $3}')
    clone_or_checkout "$name" "$url" "$sha"
done < "$LOCKFILE"

echo
echo "Installing engines (editable) + toolchain..."
pip install -q -e "$PARENT_DIR/dqSarc[gate]"
pip install -q -e "$PARENT_DIR/sarc-governance"
pip install -q -e "$PARENT_DIR/Greensarc"
pip install -q pytest hypothesis mutmut jsonschema "scipy==1.17.1"

# Round-three response (finding R3-F2(a)): Tectonic 0.17.0, pinned, is the
# canonical release toolchain for building paper-tex/main.tex and running
# `make arxiv` / `make release-check` -- it vendors its own TeX Live
# equivalent and needs no separate distro package, so it is installable on
# any machine with just curl and tar. latexmk remains a supported
# alternative for contributors who already have a full TeX Live install,
# but is not required by any gate.
TECTONIC_VERSION="0.17.0"
install_tectonic() {
    if command -v tectonic >/dev/null 2>&1; then
        local have
        have="$(tectonic --version 2>/dev/null | head -1 | awk '{print $2}')"
        if [ "$have" = "$TECTONIC_VERSION" ]; then
            echo "[tectonic] already installed at pinned version $TECTONIC_VERSION"
            return 0
        fi
        echo "[tectonic] found version $have, but $TECTONIC_VERSION is pinned; installing pinned build alongside it"
    fi

    local os arch target
    os="$(uname -s)"
    arch="$(uname -m)"
    case "$os-$arch" in
        Linux-x86_64)  target="x86_64-unknown-linux-gnu" ;;
        Linux-aarch64) target="aarch64-unknown-linux-gnu" ;;
        Darwin-x86_64) target="x86_64-apple-darwin" ;;
        Darwin-arm64)  target="aarch64-apple-darwin" ;;
        *)
            echo "[tectonic] no pinned binary for $os-$arch; install Tectonic $TECTONIC_VERSION manually (see https://tectonic-typesetting.github.io/) or use the latexmk alternative" >&2
            return 0
            ;;
    esac

    local asset="tectonic-${TECTONIC_VERSION}-${target}.tar.gz"
    local url="https://github.com/tectonic-typesetting/tectonic/releases/download/tectonic%40${TECTONIC_VERSION}/${asset}"
    local tmp
    tmp="$(mktemp -d)"
    echo "[tectonic] downloading pinned $TECTONIC_VERSION for $target..."
    curl -sSL -o "$tmp/tectonic.tar.gz" "$url"
    tar -xzf "$tmp/tectonic.tar.gz" -C "$tmp"

    local dest_dir
    if [ -w /usr/local/bin ]; then
        dest_dir="/usr/local/bin"
    else
        dest_dir="$HOME/.local/bin"
        mkdir -p "$dest_dir"
    fi
    cp "$tmp/tectonic" "$dest_dir/tectonic"
    chmod +x "$dest_dir/tectonic"
    rm -rf "$tmp"

    if ! command -v tectonic >/dev/null 2>&1; then
        echo "[tectonic] installed to $dest_dir/tectonic -- add $dest_dir to PATH" >&2
    fi
    echo "[tectonic] installed: $("$dest_dir/tectonic" --version 2>/dev/null | head -1)"
}
install_tectonic

echo
echo "Bootstrap complete."
echo "Engine commits:"
for name in dqSarc sarc-governance Greensarc; do
    echo "  $name: $(git -C "$PARENT_DIR/$name" rev-parse HEAD)"
done
