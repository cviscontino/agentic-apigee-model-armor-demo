# ==============================================================================
# 1. Google Cloud APIs & Zero-Trust IAM Service Account
# ==============================================================================

locals {
  effective_apigee_hostname = var.apigee_hostname != "" ? var.apigee_hostname : "api.${var.project_id}.internal"

  required_apis = [
    "apigee.googleapis.com",
    "apihub.googleapis.com",
    "agentregistry.googleapis.com",
    "modelarmor.googleapis.com",
    "dlp.googleapis.com",
    "aiplatform.googleapis.com",
    "bigquery.googleapis.com",
    "run.googleapis.com",
    "cloudbuild.googleapis.com",
    "artifactregistry.googleapis.com",
    "monitoring.googleapis.com",
    "logging.googleapis.com",
    "compute.googleapis.com",
    "servicenetworking.googleapis.com",
  ]

  apigee_sa_roles = [
    "roles/modelarmor.admin",
    "roles/aiplatform.user",
    "roles/bigquery.dataViewer",
    "roles/bigquery.jobUser",
    "roles/run.invoker",
    "roles/monitoring.metricWriter",
    "roles/logging.logWriter",
  ]
}

resource "google_project_service" "enabled_apis" {
  for_each           = toset(local.required_apis)
  project            = var.project_id
  service            = each.value
  disable_on_destroy = false
}

resource "google_service_account" "apigee_model_armor_sa" {
  project      = var.project_id
  account_id   = "apigee-model-armor-sa"
  display_name = "Apigee X + Cloud Model Armor + Vertex AI Gemini + BigQuery MCP Runtime SA"
  description  = "Zero-Trust Service Account used by the 5 Apigee X Proxies to invoke Cloud Model Armor, Vertex AI Gemini 2.5 Flash, A2A Sub-Agents, and BigQuery Remote MCP."
  depends_on   = [google_project_service.enabled_apis]
}

resource "google_project_iam_member" "apigee_sa_bindings" {
  for_each = toset(local.apigee_sa_roles)
  project  = var.project_id
  role     = each.value
  member   = "serviceAccount:${google_service_account.apigee_model_armor_sa.email}"
}
