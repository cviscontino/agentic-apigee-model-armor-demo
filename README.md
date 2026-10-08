# Google Cloud Zero-Trust Agentic Architecture Demo
**Apigee X (5 AI Proxies + Out-of-the-Box `<LLMTokenQuota>`) • Cloud Model Armor • Gemini Enterprise (Multi-Agent) • A2A Protocol • BigQuery Remote MCP • Vertex AI Gemini 2.5**

Progetto dimostrativo Full-Stack per **Customer Engineer (CE) Google Cloud** nel verticale **Financial Services & Anti-Money Laundering (AML) / Fraud Analytics**.

---

## 🏛️ Architettura Zero-Trust End-to-End (Nessuna Invocazione Diretta)

Tutte le comunicazioni tra Client, Agenti A2A, Server MCP BigQuery e modello Vertex AI Gemini transitano **obbligatoriamente** attraverso **5 API Proxy dedicati su Apigee X** (`agentic-prod`):

| Hop | Flusso | Proxy Apigee X | BasePath | Policy & Sicurezza Attive |
| :--- | :--- | :--- | :--- | :--- |
| **Hop 1 (Northbound)** | Client $\rightarrow$ Gemini Enterprise Root Orchestrator | **`agentic-ai-gateway`** | `/v1/agentic-fsi` | `VA-VerifyApiKey` + `SA-SpikeArrest-Burst` + `LLMTokenQuota-Enforce` + `SC-ModelArmor-SanitizeInput/Output` |
| **Hop 2a (East-West A2A)** | Root Orchestrator $\rightarrow$ Agent 1 (Transaction & Risk) | **`a2a-agent-1-tx-risk`** | `/v1/a2a/agent-1` | `SA-A2A-SpikeArrest` + `SC-ModelArmor-SanitizeA2AInput/Output` + `AM-InjectA2AGovernanceHeaders` |
| **Hop 2b (East-West A2A)** | Root Orchestrator $\rightarrow$ Agent 2 (Compliance & AML/KYC) | **`a2a-agent-2-aml-kyc`** | `/v1/a2a/agent-2` | `SA-A2A-SpikeArrest` + `SC-ModelArmor-SanitizeA2AInput/Output` + `AM-InjectA2AGovernanceHeaders` |
| **Hop 3 (Southbound MCP)** | Agent 1 & Agent 2 $\rightarrow$ BigQuery Remote MCP Server | **`bigquery-mcp-gateway`** | `/v1/mcp/bigquery` | `SC-ModelArmor-InspectSQL` + Read-Only SQL (`execute_sql_readonly`) + `apigee-model-armor-sa` OAuth2 |
| **Hop 4 (Southbound LLM)** | Root Orchestrator $\rightarrow$ Vertex AI Gemini 2.5 Flash | **`vertex-gemini-llm-gateway`** | `/v1/llm/gemini` | Policy OOTB **`<LLMTokenQuota>`** (`LLMTokenQuota-Enforce` + `LLMTokenQuota-Count` con `<Class ref="extracted.userEmail"><Allow class="admin@cviscontino.altostrat.com" count="1500"/></Class>`) |

---

## 🚀 Installazione Automatica con Terraform (Per Colleghi Google Cloud)

La cartella [`terraform/`](./terraform) contiene l'infrastruttura completa Infrastructure-as-Code per replicare la demo su qualsiasi progetto Google Cloud / Argolis.

### Cosa viene provisionato da Terraform:
1. **API Google Cloud & Service Account IAM** ([`terraform/apis_and_iam.tf`](./terraform/apis_and_iam.tf)): abilita Apigee, API Hub, Cloud Agent Registry, Model Armor, DLP, Vertex AI, BigQuery, Cloud Run e Cloud Monitoring; crea `apigee-model-armor-sa` con i ruoli minimi necessari.
2. **Dataset & Tabelle BigQuery FSI/AML** ([`terraform/bigquery.tf`](./terraform/bigquery.tf)): crea il dataset `agentic_fsi_fraud_demo` e popola `customer_portfolios`, `transactions_ledger` e `aml_compliance_alerts`.
3. **Template Cloud Model Armor** ([`terraform/model_armor.tf`](./terraform/model_armor.tf)): crea `fsi-agent-armor-strict` con filtri Prompt Injection / Jailbreak, SDP (IBAN/PII), Malicious URI e Responsible AI.
4. **Mesh Apigee X (5 Proxy, 4 API Product, Developer & 4 App)** ([`terraform/apigee_mesh.tf`](./terraform/apigee_mesh.tf)): importa e deploya i 5 bundle XML dei proxy Apigee X, inclusa la policy Out-of-the-Box `<LLMTokenQuota>` associata all'utente configurato.
5. **Servizio Cloud Run, Cloud Agent Registry & Apigee API Hub** ([`terraform/cloud_run_and_registries.tf`](./terraform/cloud_run_and_registries.tf)): deploya il backend FastAPI + React SPA su Cloud Run e registra gli Agenti A2A e il Server MCP BigQuery con gli URL dei Proxy Apigee X.
6. **Custom Dashboard in Cloud Monitoring** ([`terraform/monitoring_dashboard.tf`](./terraform/monitoring_dashboard.tf)): crea i 7 `MetricDescriptor` personalizzati (`custom.googleapis.com/agentic_fsi/...`) e la Custom Dashboard end-to-end.

### Passaggi di Deploy con Terraform:

```bash
# 1. Autenticazione su Google Cloud
gcloud auth login
gcloud auth application-default login

# 2. Configurazione variabili Terraform
cd terraform
cp terraform.tfvars.example terraform.tfvars
# Modifica terraform.tfvars inserendo il tuo `project_id` e la tua `authenticated_user_email`

# 3. Inizializzazione e Apply
terraform init
terraform apply
```

Al termine di `terraform apply`, verranno stampati in output:
- `apigee_proxy_endpoints`: i 5 endpoint mediati da Apigee X
- `cloud_monitoring_custom_dashboard_url`: il link diretto alla Custom Dashboard su Cloud Monitoring
- `apigee_developer_app_consumer_keys`: le Consumer Key generate per le 4 Developer App

---

## 💻 Avvio Rapido in Locale

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
```

- **Agentic Cockpit UI**: `http://localhost:8000`
- **Anteprima Interattiva Architettura (Dendrite + Draw.io)**: `http://localhost:8000/architecture`
