#!/bin/bash
# ClawCodex Secure — MCP stdio wrapper for Cline
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
WORKSPACE="${CLAWCODEX_WORKSPACE:-/home/jstur/development}"
CONFIG="${SCRIPT_DIR}/config/permission-hardened.json"
VENV_PYTHON="${SCRIPT_DIR}/.venv/bin/python3"

# Source API keys from career-ops/.env
if [ -f /home/jstur/development/career-ops/.env ]; then
  set -a
  source /home/jstur/development/career-ops/.env
  set +a
fi

[ -f "$CONFIG" ] || { echo '{"jsonrpc":"2.0","error":{"code":-32000,"message":"Config not found"}}' >&2; exit 1; }
[ -x "$VENV_PYTHON" ] || { echo '{"jsonrpc":"2.0","error":{"code":-32000,"message":"Virtualenv not found"}}' >&2; exit 1; }
[ -n "${OPENROUTER_API_KEY:-}" ] || { echo '{"jsonrpc":"2.0","error":{"code":-32000,"message":"OPENROUTER_API_KEY not set"}}' >&2; exit 1; }

exec "$VENV_PYTHON" -m src.cli \
  mcp serve \
  --workspace "$WORKSPACE" \
  --config "$CONFIG" \
  --permission-mode plan
