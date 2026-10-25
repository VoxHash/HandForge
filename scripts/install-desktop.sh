#!/usr/bin/env bash
# Install HandForge into the user application menu (FreeDesktop .desktop + icons).
# Prefers the project .venv console scripts after `pip install -e .`.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
if [[ -x "${ROOT}/.venv/bin/handforge" ]]; then
  exec "${ROOT}/.venv/bin/handforge" install-desktop "$@"
fi
if command -v handforge >/dev/null 2>&1; then
  exec handforge install-desktop "$@"
fi
echo "handforge not found. Create .venv and run: pip install -e ." >&2
exit 1
