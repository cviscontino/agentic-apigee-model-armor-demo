# ==============================================================================
# 4. Apigee X AI Gateway Mesh: 5 API Proxies, 4 API Products, Developer & 4 Apps
#    - Proxy 1: `agentic-ai-gateway`         (/v1/agentic-fsi)
#    - Proxy 2: `vertex-gemini-llm-gateway`  (/v1/llm/gemini) + OOTB <LLMTokenQuota>
#    - Proxy 3: `a2a-agent-1-tx-risk`        (/v1/a2a/agent-1)
#    - Proxy 4: `a2a-agent-2-aml-kyc`        (/v1/a2a/agent-2)
#    - Proxy 5: `bigquery-mcp-gateway`       (/v1/mcp/bigquery)
# ==============================================================================

resource "google_apigee_environment" "agentic_prod" {
  count           = var.create_apigee_environment ? 1 : 0
  org_id          = "organizations/${var.project_id}"
  name            = var.apigee_env_name
  display_name    = "Agentic AI Gateway Production Environment"
  description     = "Comprehensive / Extensible Apigee X Environment for <LLMTokenQuota>, Cloud Model Armor, A2A & BigQuery MCP"
  deployment_type = "PROXY"
  api_proxy_type  = "PROGRAMMABLE"
  type            = "COMPREHENSIVE"
  depends_on      = [google_project_service.enabled_apis]
}

locals {
  apigee_org_id = "organizations/${var.project_id}"
  apigee_env    = var.create_apigee_environment ? google_apigee_environment.agentic_prod[0].name : var.apigee_env_name
}

# ------------------------------------------------------------------------------
# Bundle & Deploy all 5 Apigee X API Proxies
# ------------------------------------------------------------------------------

data "archive_file" "proxy_1_agentic_ai_gateway" {
  type        = "zip"
  source_dir  = "${path.module}/../infra/apigee/apiproxy"
  output_path = "${path.module}/.build/agentic-ai-gateway.zip"
}

data "archive_file" "proxy_2_vertex_gemini_llm_gateway" {
  type        = "zip"
  source_dir  = "${path.module}/../infra/apigee/vertex-gemini-llm-gateway/apiproxy"
  output_path = "${path.module}/.build/vertex-gemini-llm-gateway.zip"
}

data "archive_file" "proxy_3_a2a_agent_1" {
  type        = "zip"
  source_dir  = "${path.module}/../infra/apigee/a2a-agent-1-tx-risk/apiproxy"
  output_path = "${path.module}/.build/a2a-agent-1-tx-risk.zip"
}

data "archive_file" "proxy_4_a2a_agent_2" {
  type        = "zip"
  source_dir  = "${path.module}/../infra/apigee/a2a-agent-2-aml-kyc/apiproxy"
  output_path = "${path.module}/.build/a2a-agent-2-aml-kyc.zip"
}

data "archive_file" "proxy_5_bigquery_mcp_gateway" {
  type        = "zip"
  source_dir  = "${path.module}/../infra/apigee/mcp-proxy/apiproxy"
  output_path = "${path.module}/.build/bigquery-mcp-gateway.zip"
}

resource "terraform_data" "deploy_5_apigee_proxies" {
  triggers_replace = [
    var.project_id,
    local.apigee_env,
    google_service_account.apigee_model_armor_sa.email,
    data.archive_file.proxy_1_agentic_ai_gateway.output_md5,
    data.archive_file.proxy_2_vertex_gemini_llm_gateway.output_md5,
    data.archive_file.proxy_3_a2a_agent_1.output_md5,
    data.archive_file.proxy_4_a2a_agent_2.output_md5,
    data.archive_file.proxy_5_bigquery_mcp_gateway.output_md5,
  ]

  provisioner "local-exec" {
    working_dir = "${path.module}/.."
    command     = <<-EOT
      python3 infra/apigee/deploy_full_apigee_mesh.py
      python3 infra/apigee/fix_and_verify_apigee_debug.py
    EOT
  }

  depends_on = [
    google_project_iam_member.apigee_sa_bindings,
    terraform_data.model_armor_template_fsi_strict,
  ]
}

# ------------------------------------------------------------------------------
# 4 Apigee API Products
# ------------------------------------------------------------------------------

resource "google_apigee_api_product" "ge_multiagent_northbound_product" {
  org_id        = local.apigee_org_id
  name          = "ge-multiagent-northbound-product"
  display_name  = "1. Gemini Enterprise Root Multi-Agent Product (Northbound)"
  description   = "Mediates Client calls to Gemini Enterprise Root Orchestrator via agentic-ai-gateway + Cloud Model Armor"
  approval_type = "auto"
  environments  = [local.apigee_env]
  proxies       = ["agentic-ai-gateway"]
  api_resources = ["/", "/**"]
  quota         = "50000"
  quota_interval  = "1"
  quota_time_unit = "hour"
  depends_on    = [terraform_data.deploy_5_apigee_proxies]
}

resource "google_apigee_api_product" "vertex_gemini_llm_product" {
  org_id        = local.apigee_org_id
  name          = "vertex-gemini-llm-product"
  display_name  = "4. Vertex AI Gemini 2.5 LLM Product (OOTB LLMTokenQuota — ${var.authenticated_user_email})"
  description   = "Mediates calls to Vertex AI Gemini 2.5 Flash (:generateContent) with Apigee Out-of-the-Box <LLMTokenQuota> (${var.llm_token_quota_per_min} tokens/min for ${var.authenticated_user_email})"
  approval_type = "auto"
  environments  = [local.apigee_env]
  proxies       = ["vertex-gemini-llm-gateway", "agentic-ai-gateway"]
  api_resources = ["/", "/**"]
  quota         = "50000"
  quota_interval  = "1"
  quota_time_unit = "hour"
  depends_on    = [terraform_data.deploy_5_apigee_proxies]
}

resource "google_apigee_api_product" "a2a_subagents_mesh_product" {
  org_id        = local.apigee_org_id
  name          = "a2a-subagents-mesh-product"
  display_name  = "2. A2A Sub-Agents Mesh Product (Agent 1 Tx Risk & Agent 2 AML/KYC)"
  description   = "Mediates East-West A2A JSON-RPC calls from Gemini Enterprise Root Orchestrator to Agent 1 and Agent 2 via Apigee + Cloud Model Armor"
  approval_type = "auto"
  environments  = [local.apigee_env]
  proxies       = ["a2a-agent-1-tx-risk", "a2a-agent-2-aml-kyc"]
  api_resources = ["/", "/**"]
  quota         = "100000"
  quota_interval  = "1"
  quota_time_unit = "hour"
  depends_on    = [terraform_data.deploy_5_apigee_proxies]
}

resource "google_apigee_api_product" "bigquery_mcp_server_product" {
  org_id        = local.apigee_org_id
  name          = "bigquery-mcp-server-product"
  display_name  = "3. BigQuery MCP Server Product (Southbound Read-Only SQL)"
  description   = "Mediates Southbound MCP JSON-RPC 2.0 calls from A2A Sub-Agents to BigQuery Remote MCP Server via Apigee + Cloud Model Armor"
  approval_type = "auto"
  environments  = [local.apigee_env]
  proxies       = ["bigquery-mcp-gateway"]
  api_resources = ["/", "/**"]
  quota         = "100000"
  quota_interval  = "1"
  quota_time_unit = "hour"
  depends_on    = [terraform_data.deploy_5_apigee_proxies]
}

# ------------------------------------------------------------------------------
# Apigee Developer & 4 Developer Apps (Zero-Trust Identity & Consumer Keys)
# ------------------------------------------------------------------------------

resource "google_apigee_developer" "demo_developer" {
  org_id     = local.apigee_org_id
  email      = var.authenticated_user_email
  first_name = var.developer_first_name
  last_name  = var.developer_last_name
  user_name  = var.developer_username
  depends_on = [terraform_data.deploy_5_apigee_proxies]
}

resource "google_apigee_developer_app" "agentic_cockpit_client_app" {
  org_id          = local.apigee_org_id
  name            = "agentic-cockpit-client-app"
  developer_email = google_apigee_developer.demo_developer.email
  api_products    = [google_apigee_api_product.ge_multiagent_northbound_product.name]

  attributes {
    name  = "Description"
    value = "Northbound Client App -> Apigee (agentic-ai-gateway) -> GE Root Agent"
  }
}

resource "google_apigee_developer_app" "ge_root_vertex_gemini_llm_app" {
  org_id          = local.apigee_org_id
  name            = "ge-root-vertex-gemini-llm-app"
  developer_email = google_apigee_developer.demo_developer.email
  api_products    = [google_apigee_api_product.vertex_gemini_llm_product.name]

  attributes {
    name  = "Description"
    value = "GE Root Orchestrator -> Apigee (vertex-gemini-llm-gateway + OOTB LLMTokenQuota) -> Vertex AI Gemini 2.5 Flash"
  }
}

resource "google_apigee_developer_app" "ge_root_orchestrator_a2a_app" {
  org_id          = local.apigee_org_id
  name            = "ge-root-orchestrator-a2a-app"
  developer_email = google_apigee_developer.demo_developer.email
  api_products    = [google_apigee_api_product.a2a_subagents_mesh_product.name]

  attributes {
    name  = "Description"
    value = "GE Root Orchestrator -> Apigee + Model Armor -> A2A Agent 1 & Agent 2"
  }
}

resource "google_apigee_developer_app" "a2a_subagents_bq_mcp_app" {
  org_id          = local.apigee_org_id
  name            = "a2a-subagents-bq-mcp-app"
  developer_email = google_apigee_developer.demo_developer.email
  api_products    = [google_apigee_api_product.bigquery_mcp_server_product.name]

  attributes {
    name  = "Description"
    value = "A2A Sub-Agents 1 & 2 -> Apigee + Model Armor -> BigQuery MCP Server"
  }
}
