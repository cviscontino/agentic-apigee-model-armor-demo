# ==============================================================================
# 5. Cloud Run Full-Stack Service, Cloud Agent Registry & Apigee API Hub
# ==============================================================================

resource "terraform_data" "build_and_deploy_cloud_run" {
  triggers_replace = [
    var.project_id,
    var.region,
    var.cloud_run_service_name,
    var.authenticated_user_email,
  ]

  provisioner "local-exec" {
    working_dir = "${path.module}/.."
    command     = <<-EOT
      gcloud run deploy "${var.cloud_run_service_name}" \
        --source=. \
        --region="${var.region}" \
        --project="${var.project_id}" \
        --service-account="${google_service_account.apigee_model_armor_sa.email}" \
        --set-env-vars="GCP_PROJECT_ID=${var.project_id},BQ_DATASET_ID=${var.bq_dataset_id},GCP_LOCATION=${var.region},MODEL_ARMOR_TEMPLATE_ID=${var.model_armor_template_id},APIGEE_ENVGROUP_HOST=${local.effective_apigee_hostname}" \
        --no-invoker-iam-check \
        --quiet
    EOT
  }

  depends_on = [
    google_project_iam_member.apigee_sa_bindings,
    google_bigquery_job.seed_fsi_demo_data,
    terraform_data.deploy_5_apigee_proxies,
  ]
}

resource "terraform_data" "register_agent_registry_and_apihub" {
  triggers_replace = [
    var.project_id,
    var.region,
    var.apihub_region,
    local.effective_apigee_hostname,
  ]

  provisioner "local-exec" {
    working_dir = "${path.module}/.."
    command     = <<-EOT
      python3 infra/register_mcp_and_agents.py
      python3 infra/apigee/enforce_apigee_proxy_mediation.py
    EOT
  }

  depends_on = [
    terraform_data.build_and_deploy_cloud_run,
    terraform_data.deploy_5_apigee_proxies,
  ]
}
