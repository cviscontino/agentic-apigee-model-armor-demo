FROM python:3.12-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    GCP_PROJECT_ID=cvisco-agentic-demo \
    BQ_DATASET_ID=agentic_fsi_fraud_demo \
    GCP_LOCATION=europe-west1 \
    MODEL_ARMOR_TEMPLATE_ID=fsi-agent-armor-strict

RUN pip install --no-cache-dir \
    fastapi \
    "uvicorn[standard]" \
    pydantic \
    httpx \
    google-cloud-bigquery \
    google-auth

COPY backend/ ./backend/
COPY frontend/ ./frontend/
COPY agents/ ./agents/
COPY infra/ ./infra/

EXPOSE 8080

CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8080"]
