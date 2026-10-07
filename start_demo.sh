#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
echo "Avvio GCP Agentic Architecture Demo (Apigee + Model Armor + GE + A2A + BigQuery MCP) su http://localhost:8000 ..."
exec ./.venv/bin/uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
