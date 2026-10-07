#!/usr/bin/env bash
# ==============================================================================
# Full Deployment Script for Argolis Project: cvisco-agentic-demo
# Account: admin@cviscontino.altostrat.com
# ==============================================================================
set -euo pipefail

cd "$(dirname "$0")"
PROJECT_ID="${PROJECT_ID:-cvisco-agentic-demo}"
REGION="${REGION:-europe-west1}"
SERVICE_NAME="${SERVICE_NAME:-agentic-fsi-demo}"

echo "==> [1/2] Provisioning BigQuery Dataset/Tables & Cloud Model Armor Template on ${PROJECT_ID}..."
./.venv/bin/python deploy_argolis.py

echo "==> [2/2] Deploying Full-Stack Demo Application (FastAPI + React + A2A + BQ MCP) to Cloud Run..."
CLOUDSDK_AUTH_CREDENTIAL_FILE_OVERRIDE="${HOME}/.config/gcloud/application_default_credentials.json" \
CLOUDSDK_METRICS_ENVIRONMENT="${CLOUDSDK_METRICS_ENVIRONMENT:+$CLOUDSDK_METRICS_ENVIRONMENT }datacloud.jetski" \
gcloud run deploy "${SERVICE_NAME}" \
  --source=. \
  --region="${REGION}" \
  --project="${PROJECT_ID}" \
  --no-invoker-iam-check \
  --quiet

echo "==> Deployment completed on project ${PROJECT_ID}!"
