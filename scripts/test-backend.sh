#!/usr/bin/env bash
set -euo pipefail
ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT_DIR/backend"

if command -v uv >/dev/null 2>&1; then
  uv run --extra test python -m pytest "$@"
else
  python3 -m pytest "$@"
fi
