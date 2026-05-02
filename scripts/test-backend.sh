#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."

if command -v uv >/dev/null 2>&1; then
  uv run --with pytest --with pytest-asyncio python -m pytest "$@"
else
  python3 -m pytest "$@"
fi
