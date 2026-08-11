#!/usr/bin/env bash
set -euo pipefail

# Purpose: Execute Python under arm64 on Apple Silicon (when possible).
#
# Usage:
#   scripts/python_arm64.sh -m pytest tests/
#   scripts/python_arm64.sh scripts/run_all_tests.sh
#
# On macOS arm64-capable machines, runs via `arch -arm64`.
# Otherwise runs the resolved Python normally.

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

use_repo_venv=false
python_bin="venv/bin/python"

if [[ -x "$ROOT_DIR/$python_bin" ]]; then
  use_repo_venv=true
  resolved_python="$python_bin"
else
  resolved_python="$(command -v python3 || echo python3)"
fi

if [[ "$use_repo_venv" == "true" ]]; then
  cd "$ROOT_DIR"
fi

if [[ ! -x "$resolved_python" ]]; then
  echo "ERROR: Python executable not found or not executable: $resolved_python" >&2
  exit 2
fi

if [[ "$(uname -s)" == "Darwin" ]]; then
  apple_arm_capable="$(sysctl -in hw.optional.arm64 2>/dev/null || echo 0)"
  if [[ "$apple_arm_capable" == "1" ]]; then
    exec arch -arm64 "$resolved_python" "$@"
  fi
fi

exec "$resolved_python" "$@"
