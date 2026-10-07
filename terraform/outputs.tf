# ==============================================================================
# 7. Terraform Outputs — Endpoints, Consumer Keys & Console URLs
# ==============================================================================

output "apigee_runtime_service_account" {
  description = "Service Account used by the 5 Apigee X API Proxies."
  value       = google_service_account.apigee_model_armor_sa.email
}

output "bigquery_dataset_id" {
  description = "BigQuery Dataset queried via Apigee X Proxy 5 (bigquery-mcp-gateway)."
  value       = "${var.project_id}.${google_bigquery_dataset.fsi_fraud_demo.dataset_id}"
}

output "model_armor_template_name" {
  description = "Cloud Model Armor template resource path."
  value       = "projects/${var.project_id}/locations/${var.region}/templates/${var.model_armor_template_id}"
}

output "apigee_proxy_endpoints" {
  description = "Zero-Trust Apigee X Proxy URLs mediating all Agentic, LLM, A2A, and BigQuery MCP traffic."
  value = {
    hop_1_northbound_root      = "https://${local.effective_apigee_hostname}/v1/agentic-fsi"
    hop_2a_a2a_agent_1_tx_risk = "https://${local.effective_apigee_hostname}/v1/a2a/agent-1"
    hop_2b_a2a_agent_2_aml_kyc = "https://${local.effective_apigee_hostname}/v1/a2a/agent-2"
    hop_3_southbound_bq_mcp    = "https://${local.effective_apigee_hostname}/v1/mcp/bigquery"
    hop_4_vertex_gemini_llm    = "https://${local.effective_apigee_hostname}/v1/llm/gemini"
  }
}

output "apigee_developer_app_consumer_keys" {
  description = "Consumer API Keys generated for the 4 Apigee Developer Apps."
  sensitive   = true
  value = {
    agentic_cockpit_client_app    = try(google_apigee_developer_app.agentic_cockpit_client_app.credentials[0].consumer_key, "")
    ge_root_vertex_gemini_llm_app = try(google_apigee_developer_app.ge_root_vertex_gemini_llm_app.credentials[0].consumer_key, "")
    ge_root_orchestrator_a2a_app  = try(google_apigee_developer_app.ge_root_orchestrator_a2a_app.credentials[0].consumer_key, "")
    a2a_subagents_bq_mcp_app      = try(google_apigee_developer_app.a2a_subagents_bq_mcp_app.credentials[0].consumer_key, "")
  }
}

output "cloud_monitoring_custom_dashboard_url" {
  description = "Direct Google Cloud Console URL for the End-to-End Agentic Observability Dashboard."
  value       = "https://console.cloud.google.com/monitoring/dashboards/builder/${reverse(split("/", google_monitoring_dashboard.agentic_fsi_mesh.id))[0]}?project=${var.project_id}&duration=PT1H"
}
