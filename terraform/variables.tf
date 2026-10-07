variable "project_id" {
  description = "Google Cloud Project ID where the Zero-Trust Agentic Demo will be deployed."
  type        = string
}

variable "region" {
  description = "Primary Google Cloud region for Cloud Run, Cloud Model Armor, Vertex AI Gemini, and Cloud Agent Registry."
  type        = string
  default     = "europe-west1"
}

variable "apihub_region" {
  description = "Google Cloud region for Apigee API Hub."
  type        = string
  default     = "us-central1"
}

variable "bq_dataset_id" {
  description = "BigQuery Dataset ID for the FSI Fraud & AML tables queried via BigQuery Remote MCP."
  type        = string
  default     = "agentic_fsi_fraud_demo"
}

variable "bq_location" {
  description = "BigQuery Dataset location (e.g. US or EU)."
  type        = string
  default     = "US"
}

variable "authenticated_user_email" {
  description = "Authenticated User / Developer email used as <Identifier> in Apigee Out-of-the-Box <LLMTokenQuota> policy and Apigee Developer Apps."
  type        = string
  default     = "cviscontino@google.com"
}

variable "developer_first_name" {
  description = "First name for the Apigee X Developer registration."
  type        = string
  default     = "Cristina"
}

variable "developer_last_name" {
  description = "Last name for the Apigee X Developer registration."
  type        = string
  default     = "Viscontino"
}

variable "developer_username" {
  description = "Username for the Apigee X Developer registration."
  type        = string
  default     = "cviscontino-ce"
}

variable "llm_token_quota_per_min" {
  description = "Default rolling 60-second Vertex AI Gemini token budget per user enforced by Apigee OOTB <LLMTokenQuota>."
  type        = number
  default     = 1500
}

variable "spike_arrest_rpm" {
  description = "Apigee SpikeArrest rate limit (requests per minute)."
  type        = number
  default     = 15
}

variable "gemini_model" {
  description = "Vertex AI Gemini model used for Executive Risk Synthesis via vertex-gemini-llm-gateway."
  type        = string
  default     = "gemini-2.5-flash"
}

variable "model_armor_template_id" {
  description = "Cloud Model Armor template ID for Prompt Injection, Jailbreak, SDP (IBAN/PII), Malicious URI, and RAI filtering."
  type        = string
  default     = "fsi-agent-armor-strict"
}

variable "apigee_env_name" {
  description = "Apigee X Environment name (must be COMPREHENSIVE / EXTENSIBLE to support <LLMTokenQuota>)."
  type        = string
  default     = "agentic-prod"
}

variable "apigee_envgroup_name" {
  description = "Apigee X Environment Group name."
  type        = string
  default     = "eval-envgroup"
}

variable "apigee_hostname" {
  description = "Internal or external hostname configured on the Apigee X Environment Group."
  type        = string
  default     = ""
}

variable "create_apigee_environment" {
  description = "Set to true if Terraform should create the Apigee Environment (`apigee_env_name`). Set to false if it already exists in your Apigee Organization."
  type        = bool
  default     = false
}

variable "cloud_run_service_name" {
  description = "Name of the Cloud Run service hosting the Agentic Cockpit UI, Root Orchestrator, and A2A Sub-Agents."
  type        = string
  default     = "agentic-fsi-demo"
}

variable "container_image" {
  description = "Container image URI for the Cloud Run service (e.g., gcr.io/<project_id>/agentic-fsi-demo:latest). Leave empty to build automatically via gcloud builds submit."
  type        = string
  default     = ""
}
