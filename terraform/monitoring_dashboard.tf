# ==============================================================================
# 6. Google Cloud Monitoring Custom Metrics & End-to-End Observability Dashboard
# ==============================================================================

resource "google_monitoring_metric_descriptor" "proxy_requests_per_min" {
  project      = var.project_id
  type         = "custom.googleapis.com/agentic_fsi/proxy_requests_per_min"
  metric_kind  = "GAUGE"
  value_type   = "INT64"
  unit         = "1"
  display_name = "Apigee X Proxy Requests (All 5 Agentic Proxies)"
  description  = "Request count mediated by the 5 Apigee X proxies (agentic-ai-gateway, vertex-gemini-llm-gateway, a2a-agent-1-tx-risk, a2a-agent-2-aml-kyc, bigquery-mcp-gateway)."

  labels {
    key         = "proxy_name"
    value_type  = "STRING"
    description = "Apigee X Proxy Name"
  }
  labels {
    key         = "hop"
    value_type  = "STRING"
    description = "Architectural Hop"
  }
  labels {
    key         = "verdict"
    value_type  = "STRING"
    description = "200_ALLOWED, 422_MODEL_ARMOR_BLOCKED, 429_LLM_TOKEN_QUOTA, 429_SPIKE_ARREST"
  }
  labels {
    key         = "user_email"
    value_type  = "STRING"
    description = "Authenticated User Email"
  }

  depends_on = [google_project_service.enabled_apis]
}

resource "google_monitoring_metric_descriptor" "hop_latency_ms" {
  project      = var.project_id
  type         = "custom.googleapis.com/agentic_fsi/hop_latency_ms"
  metric_kind  = "GAUGE"
  value_type   = "DOUBLE"
  unit         = "ms"
  display_name = "Agentic Chain Per-Hop Latency (ms)"
  description  = "Latency in milliseconds across each hop mediated by Apigee X (Northbound, Model Armor, A2A Sub-Agents, BigQuery MCP, Vertex AI Gemini)."

  labels {
    key         = "hop"
    value_type  = "STRING"
    description = "Hop Name"
  }
  labels {
    key         = "proxy_name"
    value_type  = "STRING"
    description = "Mediating Apigee X Proxy"
  }

  depends_on = [google_project_service.enabled_apis]
}

resource "google_monitoring_metric_descriptor" "gemini_tokens_used" {
  project      = var.project_id
  type         = "custom.googleapis.com/agentic_fsi/gemini_tokens_used"
  metric_kind  = "GAUGE"
  value_type   = "INT64"
  unit         = "1"
  display_name = "Vertex AI Gemini Token Consumption (via vertex-gemini-llm-gateway)"
  description  = "Prompt, Candidates, and Total tokens consumed on Vertex AI Gemini 2.5 Flash via Apigee X proxy vertex-gemini-llm-gateway."

  labels {
    key         = "user_email"
    value_type  = "STRING"
    description = "Authenticated User Identity (extracted.userEmail)"
  }
  labels {
    key         = "token_type"
    value_type  = "STRING"
    description = "promptTokenCount, candidatesTokenCount, totalTokenCount"
  }
  labels {
    key         = "proxy_name"
    value_type  = "STRING"
    description = "Apigee X LLM Proxy (vertex-gemini-llm-gateway)"
  }
  labels {
    key         = "model"
    value_type  = "STRING"
    description = "Vertex AI Gemini Model"
  }

  depends_on = [google_project_service.enabled_apis]
}

resource "google_monitoring_metric_descriptor" "llm_token_quota_utilization_pct" {
  project      = var.project_id
  type         = "custom.googleapis.com/agentic_fsi/llm_token_quota_utilization_pct"
  metric_kind  = "GAUGE"
  value_type   = "DOUBLE"
  unit         = "%"
  display_name = "Apigee OOTB <LLMTokenQuota> Utilization (%)"
  description  = "Percentage of the rolling 60s token quota consumed by the authenticated user on Apigee shared counter user-gemini-token-counter."

  labels {
    key         = "user_email"
    value_type  = "STRING"
    description = "Authenticated User Identity"
  }
  labels {
    key         = "shared_counter"
    value_type  = "STRING"
    description = "Apigee LLMTokenQuota Shared Counter"
  }
  labels {
    key         = "proxy_name"
    value_type  = "STRING"
    description = "Apigee Proxy enforcing Q-TokenQuota-Enforce"
  }

  depends_on = [google_project_service.enabled_apis]
}

resource "google_monitoring_metric_descriptor" "model_armor_inspections" {
  project      = var.project_id
  type         = "custom.googleapis.com/agentic_fsi/model_armor_inspections"
  metric_kind  = "GAUGE"
  value_type   = "INT64"
  unit         = "1"
  display_name = "Cloud Model Armor Inspections & Threat Blocks"
  description  = "Count of Cloud Model Armor inspections (fsi-agent-armor-strict) across Input, A2A, MCP SQL, and Output hops by verdict and threat detector."

  labels {
    key         = "hop_phase"
    value_type  = "STRING"
    description = "Northbound_Input, EastWest_A2A, Southbound_MCP_SQL, Northbound_Output"
  }
  labels {
    key         = "verdict"
    value_type  = "STRING"
    description = "NO_MATCH_FOUND or MATCH_FOUND_*"
  }
  labels {
    key         = "detector"
    value_type  = "STRING"
    description = "CLEAN_PASSED, PI_AND_JAILBREAK, SDP_PII_IBAN_DEID, MALICIOUS_URI_AND_SQLI"
  }

  depends_on = [google_project_service.enabled_apis]
}

resource "google_monitoring_metric_descriptor" "a2a_subagent_tasks" {
  project      = var.project_id
  type         = "custom.googleapis.com/agentic_fsi/a2a_subagent_tasks"
  metric_kind  = "GAUGE"
  value_type   = "INT64"
  unit         = "1"
  display_name = "A2A Sub-Agent Tasks Dispatched (via Apigee A2A Proxies)"
  description  = "JSON-RPC 2.0 tasks/send calls mediated by Apigee proxies a2a-agent-1-tx-risk and a2a-agent-2-aml-kyc."

  labels {
    key         = "agent_id"
    value_type  = "STRING"
    description = "Target A2A Sub-Agent ID"
  }
  labels {
    key         = "apigee_proxy"
    value_type  = "STRING"
    description = "Mediating Apigee X Proxy"
  }
  labels {
    key         = "status"
    value_type  = "STRING"
    description = "COMPLETED_VIA_APIGEE or BLOCKED"
  }

  depends_on = [google_project_service.enabled_apis]
}

resource "google_monitoring_metric_descriptor" "bq_mcp_queries" {
  project      = var.project_id
  type         = "custom.googleapis.com/agentic_fsi/bq_mcp_queries"
  metric_kind  = "GAUGE"
  value_type   = "INT64"
  unit         = "1"
  display_name = "BigQuery Remote MCP Read-Only Queries (via bigquery-mcp-gateway)"
  description  = "MCP tools/call (execute_sql_readonly) mediated by Apigee proxy bigquery-mcp-gateway against BigQuery dataset agentic_fsi_fraud_demo."

  labels {
    key         = "caller_agent"
    value_type  = "STRING"
    description = "Calling A2A Sub-Agent"
  }
  labels {
    key         = "table"
    value_type  = "STRING"
    description = "Target BigQuery Table"
  }
  labels {
    key         = "apigee_proxy"
    value_type  = "STRING"
    description = "bigquery-mcp-gateway"
  }

  depends_on = [google_project_service.enabled_apis]
}

resource "google_monitoring_dashboard" "agentic_fsi_mesh" {
  project = var.project_id

  dashboard_json = jsonencode({
    displayName = "Zero-Trust Agentic FSI Mesh — Apigee X (5 Proxies + LLMTokenQuota), Model Armor, A2A, BigQuery MCP & Gemini"
    mosaicLayout = {
      columns = 12
      tiles = [
        {
          xPos   = 0
          yPos   = 0
          width  = 12
          height = 2
          widget = {
            title = "Zero-Trust Agentic FSI Architecture — End-to-End Observability (5 Apigee X Proxies · Zero Direct Invocations)"
            text = {
              content = "**Catena di Mediazione Zero-Trust (`${var.project_id}` · `${local.apigee_env}`)**:\n1. **Hop 1 (Northbound)**: Client (`${var.authenticated_user_email}`) -> **`Proxy 1: agentic-ai-gateway` (`/v1/agentic-fsi`)** -> Gemini Enterprise Root Orchestrator\n2. **Hop 2 (East-West A2A)**: Root Orchestrator -> **`Proxy 3: a2a-agent-1-tx-risk` (`/v1/a2a/agent-1`)** & **`Proxy 4: a2a-agent-2-aml-kyc` (`/v1/a2a/agent-2`)** -> Sub-Agents 1 & 2\n3. **Hop 3 (Southbound MCP)**: A2A Sub-Agents 1 & 2 -> **`Proxy 5: bigquery-mcp-gateway` (`/v1/mcp/bigquery`)** -> BigQuery Remote MCP Server (`execute_sql_readonly`)\n4. **Hop 4 (Southbound LLM + OOTB Token Quota)**: Root Orchestrator -> **`Proxy 2: vertex-gemini-llm-gateway` (`/v1/llm/gemini`)** con policy Out-of-the-Box **`<LLMTokenQuota>` (`Q-TokenQuota-Enforce` + `Q-TokenQuota-Count` su `$.usageMetadata.totalTokenCount`)** -> Vertex AI Gemini 2.5 Flash"
              format  = "MARKDOWN"
            }
          }
        },
        {
          xPos   = 0
          yPos   = 2
          width  = 3
          height = 3
          widget = {
            title = "1. Chiamate Mediate dai 5 Proxy Apigee X (ultimi 5m)"
            scorecard = {
              timeSeriesQuery = {
                timeSeriesFilter = {
                  filter = "metric.type=\"custom.googleapis.com/agentic_fsi/proxy_requests_per_min\" resource.type=\"global\""
                  aggregation = {
                    alignmentPeriod    = "300s"
                    perSeriesAligner   = "ALIGN_SUM"
                    crossSeriesReducer = "REDUCE_SUM"
                  }
                }
              }
              sparkChartView = { sparkChartType = "SPARK_BAR" }
            }
          }
        },
        {
          xPos   = 3
          yPos   = 2
          width  = 3
          height = 3
          widget = {
            title = "2. Apigee OOTB <LLMTokenQuota> % (${var.authenticated_user_email})"
            scorecard = {
              timeSeriesQuery = {
                timeSeriesFilter = {
                  filter = "metric.type=\"custom.googleapis.com/agentic_fsi/llm_token_quota_utilization_pct\" resource.type=\"global\""
                  aggregation = {
                    alignmentPeriod    = "60s"
                    perSeriesAligner   = "ALIGN_MEAN"
                    crossSeriesReducer = "REDUCE_MAX"
                  }
                }
              }
              gaugeView = { lowerBound = 0.0, upperBound = 100.0 }
              thresholds = [
                { label = "Warning (70%)", value = 70.0, color = "YELLOW", direction = "ABOVE" },
                { label = "Quota 429 Risk (90%)", value = 90.0, color = "RED", direction = "ABOVE" },
              ]
            }
          }
        },
        {
          xPos   = 6
          yPos   = 2
          width  = 3
          height = 3
          widget = {
            title = "3. Token Vertex AI Gemini Consumati ($.usageMetadata.totalTokenCount)"
            scorecard = {
              timeSeriesQuery = {
                timeSeriesFilter = {
                  filter = "metric.type=\"custom.googleapis.com/agentic_fsi/gemini_tokens_used\" resource.type=\"global\" metric.label.\"token_type\"=\"3_totalTokenCount ($.usageMetadata.totalTokenCount)\""
                  aggregation = {
                    alignmentPeriod    = "300s"
                    perSeriesAligner   = "ALIGN_SUM"
                    crossSeriesReducer = "REDUCE_SUM"
                  }
                }
              }
              sparkChartView = { sparkChartType = "SPARK_LINE" }
            }
          }
        },
        {
          xPos   = 9
          yPos   = 2
          width  = 3
          height = 3
          widget = {
            title = "4. Minacce Bloccate da Cloud Model Armor (HTTP 422)"
            scorecard = {
              timeSeriesQuery = {
                timeSeriesFilter = {
                  filter = "metric.type=\"custom.googleapis.com/agentic_fsi/model_armor_inspections\" resource.type=\"global\" metric.label.\"detector\"!=\"CLEAN_PASSED\""
                  aggregation = {
                    alignmentPeriod    = "300s"
                    perSeriesAligner   = "ALIGN_SUM"
                    crossSeriesReducer = "REDUCE_SUM"
                  }
                }
              }
              sparkChartView = { sparkChartType = "SPARK_BAR" }
              thresholds = [
                { label = "Active Threat Mitigation", value = 1.0, color = "RED", direction = "ABOVE" },
              ]
            }
          }
        },
        {
          xPos   = 0
          yPos   = 5
          width  = 6
          height = 4
          widget = {
            title = "Hop 1..4 — Traffico Mediato per Proxy Apigee X (5 Proxy Attivi · Zero Chiamate Dirette)"
            xyChart = {
              dataSets = [{
                timeSeriesQuery = {
                  timeSeriesFilter = {
                    filter = "metric.type=\"custom.googleapis.com/agentic_fsi/proxy_requests_per_min\" resource.type=\"global\""
                    aggregation = {
                      alignmentPeriod    = "60s"
                      perSeriesAligner   = "ALIGN_SUM"
                      crossSeriesReducer = "REDUCE_SUM"
                      groupByFields      = ["metric.label.proxy_name", "metric.label.verdict"]
                    }
                  }
                }
                plotType       = "STACKED_BAR"
                legendTemplate = "$${metric.labels.proxy_name} [$${metric.labels.verdict}]"
              }]
              yAxis = { label = "Requests / min", scale = "LINEAR" }
            }
          }
        },
        {
          xPos   = 6
          yPos   = 5
          width  = 6
          height = 4
          widget = {
            title = "Hop 4 — Vertex AI Gemini Token Consumption (Proxy 2: vertex-gemini-llm-gateway · OOTB <LLMTokenQuota>)"
            xyChart = {
              dataSets = [{
                timeSeriesQuery = {
                  timeSeriesFilter = {
                    filter = "metric.type=\"custom.googleapis.com/agentic_fsi/gemini_tokens_used\" resource.type=\"global\""
                    aggregation = {
                      alignmentPeriod    = "60s"
                      perSeriesAligner   = "ALIGN_MEAN"
                      crossSeriesReducer = "REDUCE_SUM"
                      groupByFields      = ["metric.label.token_type", "metric.label.user_email"]
                    }
                  }
                }
                plotType       = "LINE"
                legendTemplate = "$${metric.labels.token_type} ($${metric.labels.user_email})"
              }]
              yAxis = { label = "Tokens", scale = "LINEAR" }
            }
          }
        },
        {
          xPos   = 0
          yPos   = 9
          width  = 6
          height = 4
          widget = {
            title = "Cloud Model Armor (fsi-agent-armor-strict) — Ispezioni e Minacce Bloccate"
            xyChart = {
              dataSets = [{
                timeSeriesQuery = {
                  timeSeriesFilter = {
                    filter = "metric.type=\"custom.googleapis.com/agentic_fsi/model_armor_inspections\" resource.type=\"global\""
                    aggregation = {
                      alignmentPeriod    = "60s"
                      perSeriesAligner   = "ALIGN_SUM"
                      crossSeriesReducer = "REDUCE_SUM"
                      groupByFields      = ["metric.label.detector", "metric.label.verdict"]
                    }
                  }
                }
                plotType       = "STACKED_BAR"
                legendTemplate = "$${metric.labels.detector} — $${metric.labels.verdict}"
              }]
              yAxis = { label = "Inspections", scale = "LINEAR" }
            }
          }
        },
        {
          xPos   = 6
          yPos   = 9
          width  = 6
          height = 4
          widget = {
            title = "Latenza End-to-End Scomposta per Hop (ms) attraverso i 5 Proxy Apigee X"
            xyChart = {
              dataSets = [{
                timeSeriesQuery = {
                  timeSeriesFilter = {
                    filter = "metric.type=\"custom.googleapis.com/agentic_fsi/hop_latency_ms\" resource.type=\"global\""
                    aggregation = {
                      alignmentPeriod    = "60s"
                      perSeriesAligner   = "ALIGN_MEAN"
                      crossSeriesReducer = "REDUCE_MEAN"
                      groupByFields      = ["metric.label.hop", "metric.label.proxy_name"]
                    }
                  }
                }
                plotType       = "LINE"
                legendTemplate = "$${metric.labels.hop} [$${metric.labels.proxy_name}]"
              }]
              yAxis = { label = "Latency (ms)", scale = "LINEAR" }
            }
          }
        },
        {
          xPos   = 0
          yPos   = 13
          width  = 6
          height = 4
          widget = {
            title = "Hop 2 (East-West A2A) — Task JSON-RPC 2.0 Mediati da Proxy 3 & Proxy 4"
            xyChart = {
              dataSets = [{
                timeSeriesQuery = {
                  timeSeriesFilter = {
                    filter = "metric.type=\"custom.googleapis.com/agentic_fsi/a2a_subagent_tasks\" resource.type=\"global\""
                    aggregation = {
                      alignmentPeriod    = "60s"
                      perSeriesAligner   = "ALIGN_SUM"
                      crossSeriesReducer = "REDUCE_SUM"
                      groupByFields      = ["metric.label.agent_id", "metric.label.apigee_proxy"]
                    }
                  }
                }
                plotType       = "STACKED_BAR"
                legendTemplate = "$${metric.labels.agent_id} via $${metric.labels.apigee_proxy}"
              }]
              yAxis = { label = "A2A Tasks / min", scale = "LINEAR" }
            }
          }
        },
        {
          xPos   = 6
          yPos   = 13
          width  = 6
          height = 4
          widget = {
            title = "Hop 3 (Southbound MCP) — Query SQL Read-Only su BigQuery MCP via Proxy 5 (bigquery-mcp-gateway)"
            xyChart = {
              dataSets = [{
                timeSeriesQuery = {
                  timeSeriesFilter = {
                    filter = "metric.type=\"custom.googleapis.com/agentic_fsi/bq_mcp_queries\" resource.type=\"global\""
                    aggregation = {
                      alignmentPeriod    = "60s"
                      perSeriesAligner   = "ALIGN_SUM"
                      crossSeriesReducer = "REDUCE_SUM"
                      groupByFields      = ["metric.label.table", "metric.label.caller_agent"]
                    }
                  }
                }
                plotType       = "STACKED_AREA"
                legendTemplate = "Table: $${metric.labels.table} (Caller: $${metric.labels.caller_agent})"
              }]
              yAxis = { label = "MCP SQL Queries / min", scale = "LINEAR" }
            }
          }
        },
        {
          xPos   = 0
          yPos   = 17
          width  = 12
          height = 5
          widget = {
            title = "Live Audit & Telemetry Logs — Apigee X, Cloud Model Armor, A2A Sub-Agents, BigQuery MCP & Cloud Run"
            logsPanel = {
              filter        = "resource.type=\"cloud_run_revision\" OR resource.type=\"bigquery_resource\" OR resource.type=\"audited_resource\""
              resourceNames = ["projects/${var.project_id}"]
            }
          }
        },
      ]
    }
  })

  depends_on = [
    google_monitoring_metric_descriptor.proxy_requests_per_min,
    google_monitoring_metric_descriptor.hop_latency_ms,
    google_monitoring_metric_descriptor.gemini_tokens_used,
    google_monitoring_metric_descriptor.llm_token_quota_utilization_pct,
    google_monitoring_metric_descriptor.model_armor_inspections,
    google_monitoring_metric_descriptor.a2a_subagent_tasks,
    google_monitoring_metric_descriptor.bq_mcp_queries,
  ]
}
