#!/usr/bin/env python3
"""
Creates and populates a full End-to-End Cloud Monitoring Custom Dashboard
in project `cvisco-agentic-demo` to monitor the entire Zero-Trust Agentic Chain:
  1. Apigee X Northbound Proxy (`agentic-ai-gateway` - /v1/agentic-fsi)
  2. Apigee X Vertex AI Gemini Proxy (`vertex-gemini-llm-gateway` - /v1/llm/gemini) + OOTB `<LLMTokenQuota>` (admin@cviscontino.altostrat.com)
  3. Cloud Model Armor (`fsi-agent-armor-strict` across Input, A2A, MCP SQL, and Output)
  4. Apigee X East-West A2A Proxies (`a2a-agent-1-tx-risk` & `a2a-agent-2-aml-kyc`) -> A2A Sub-Agents 1 & 2
  5. Apigee X Southbound MCP Proxy (`bigquery-mcp-gateway` - /v1/mcp/bigquery) -> BigQuery Remote MCP Server
  6. Native Cloud Run & BigQuery Infrastructure Metrics + Live Logs Panel
"""
import datetime
import json
import math
import time
import httpx
import google.auth
import google.auth.transport.requests

PROJECT_ID = "cvisco-agentic-demo"
DASHBOARD_DISPLAY_NAME = "Zero-Trust Agentic FSI Mesh — Apigee X (5 Proxies + LLMTokenQuota), Model Armor, A2A, BigQuery MCP & Gemini"


def get_headers() -> dict:
    creds, _ = google.auth.default(scopes=["https://www.googleapis.com/auth/cloud-platform"])
    creds.refresh(google.auth.transport.requests.Request())
    return {
        "Authorization": f"Bearer {creds.token}",
        "x-goog-user-project": PROJECT_ID,
        "Content-Type": "application/json",
    }


METRIC_DESCRIPTORS = [
    {
        "type": "custom.googleapis.com/agentic_fsi/proxy_requests_per_min",
        "displayName": "Apigee X Proxy Requests (All 5 Agentic Proxies)",
        "description": "Request count mediated by the 5 Apigee X proxies (agentic-ai-gateway, vertex-gemini-llm-gateway, a2a-agent-1-tx-risk, a2a-agent-2-aml-kyc, bigquery-mcp-gateway).",
        "metricKind": "GAUGE",
        "valueType": "INT64",
        "unit": "1",
        "labels": [
            {"key": "proxy_name", "valueType": "STRING", "description": "Apigee X Proxy Name"},
            {"key": "hop", "valueType": "STRING", "description": "Architectural Hop"},
            {"key": "verdict", "valueType": "STRING", "description": "200_ALLOWED, 422_MODEL_ARMOR_BLOCKED, 429_LLM_TOKEN_QUOTA, 429_SPIKE_ARREST"},
            {"key": "user_email", "valueType": "STRING", "description": "Authenticated User Email"},
        ],
    },
    {
        "type": "custom.googleapis.com/agentic_fsi/hop_latency_ms",
        "displayName": "Agentic Chain Per-Hop Latency (ms)",
        "description": "Latency in milliseconds across each hop mediated by Apigee X (Northbound, Model Armor, A2A Sub-Agents, BigQuery MCP, Vertex AI Gemini).",
        "metricKind": "GAUGE",
        "valueType": "DOUBLE",
        "unit": "ms",
        "labels": [
            {"key": "hop", "valueType": "STRING", "description": "Hop Name"},
            {"key": "proxy_name", "valueType": "STRING", "description": "Mediating Apigee X Proxy"},
        ],
    },
    {
        "type": "custom.googleapis.com/agentic_fsi/gemini_tokens_used",
        "displayName": "Vertex AI Gemini Token Consumption (via vertex-gemini-llm-gateway)",
        "description": "Prompt, Candidates, and Total tokens consumed on Vertex AI Gemini 2.5 Flash via Apigee X proxy vertex-gemini-llm-gateway.",
        "metricKind": "GAUGE",
        "valueType": "INT64",
        "unit": "1",
        "labels": [
            {"key": "user_email", "valueType": "STRING", "description": "Authenticated User Identity (extracted.userEmail)"},
            {"key": "token_type", "valueType": "STRING", "description": "promptTokenCount, candidatesTokenCount, totalTokenCount"},
            {"key": "proxy_name", "valueType": "STRING", "description": "Apigee X LLM Proxy (vertex-gemini-llm-gateway)"},
            {"key": "model", "valueType": "STRING", "description": "Vertex AI Gemini Model"},
        ],
    },
    {
        "type": "custom.googleapis.com/agentic_fsi/llm_token_quota_utilization_pct",
        "displayName": "Apigee OOTB <LLMTokenQuota> Utilization (%)",
        "description": "Percentage of the rolling 60s token quota consumed by admin@cviscontino.altostrat.com on Apigee shared counter user-gemini-token-counter.",
        "metricKind": "GAUGE",
        "valueType": "DOUBLE",
        "unit": "%",
        "labels": [
            {"key": "user_email", "valueType": "STRING", "description": "Authenticated User Identity"},
            {"key": "shared_counter", "valueType": "STRING", "description": "Apigee LLMTokenQuota Shared Counter"},
            {"key": "proxy_name", "valueType": "STRING", "description": "Apigee Proxy enforcing Q-TokenQuota-Enforce"},
        ],
    },
    {
        "type": "custom.googleapis.com/agentic_fsi/model_armor_inspections",
        "displayName": "Cloud Model Armor Inspections & Threat Blocks",
        "description": "Count of Cloud Model Armor inspections (fsi-agent-armor-strict) across Input, A2A, MCP SQL, and Output hops by verdict and threat detector.",
        "metricKind": "GAUGE",
        "valueType": "INT64",
        "unit": "1",
        "labels": [
            {"key": "hop_phase", "valueType": "STRING", "description": "Northbound_Input, EastWest_A2A, Southbound_MCP_SQL, Northbound_Output"},
            {"key": "verdict", "valueType": "STRING", "description": "NO_MATCH_FOUND or MATCH_FOUND_*"},
            {"key": "detector", "valueType": "STRING", "description": "CLEAN, PI_AND_JAILBREAK, SDP_PII_IBAN, MALICIOUS_URI_SQLI, RAI_AMLD6"},
        ],
    },
    {
        "type": "custom.googleapis.com/agentic_fsi/a2a_subagent_tasks",
        "displayName": "A2A Sub-Agent Tasks Dispatched (via Apigee A2A Proxies)",
        "description": "JSON-RPC 2.0 tasks/send calls mediated by Apigee proxies a2a-agent-1-tx-risk and a2a-agent-2-aml-kyc.",
        "metricKind": "GAUGE",
        "valueType": "INT64",
        "unit": "1",
        "labels": [
            {"key": "agent_id", "valueType": "STRING", "description": "Target A2A Sub-Agent ID"},
            {"key": "apigee_proxy", "valueType": "STRING", "description": "Mediating Apigee X Proxy"},
            {"key": "status", "valueType": "STRING", "description": "COMPLETED_VIA_APIGEE or BLOCKED"},
        ],
    },
    {
        "type": "custom.googleapis.com/agentic_fsi/bq_mcp_queries",
        "displayName": "BigQuery Remote MCP Read-Only Queries (via bigquery-mcp-gateway)",
        "description": "MCP tools/call (execute_sql_readonly) mediated by Apigee proxy bigquery-mcp-gateway against BigQuery dataset agentic_fsi_fraud_demo.",
        "metricKind": "GAUGE",
        "valueType": "INT64",
        "unit": "1",
        "labels": [
            {"key": "caller_agent", "valueType": "STRING", "description": "Calling A2A Sub-Agent"},
            {"key": "table", "valueType": "STRING", "description": "Target BigQuery Table"},
            {"key": "apigee_proxy", "valueType": "STRING", "description": "bigquery-mcp-gateway"},
        ],
    },
]


def build_timeseries_batch(ts_iso: str, step_idx: int) -> list[dict]:
    """Builds a batch of distinct TimeSeries for a single timestamp `ts_iso`."""
    res = {"type": "global", "labels": {"project_id": PROJECT_ID}}
    wave = int(3 + 2 * math.sin(step_idx * 0.7))
    prompt_tok = 460 + (step_idx % 4) * 55
    cand_tok = 390 + (step_idx % 3) * 65
    tot_tok = prompt_tok + cand_tok
    quota_pct = min(100.0, round(((tot_tok * (1 + (step_idx % 2))) / 1500.0) * 100.0, 1))

    def pt_int(val: int) -> list[dict]:
        return [{"interval": {"endTime": ts_iso}, "value": {"int64Value": str(val)}}]

    def pt_dbl(val: float) -> list[dict]:
        return [{"interval": {"endTime": ts_iso}, "value": {"doubleValue": float(val)}}]

    series = [
        # 1. Proxy Requests across all 5 Apigee X Proxies
        {
            "metric": {
                "type": "custom.googleapis.com/agentic_fsi/proxy_requests_per_min",
                "labels": {
                    "proxy_name": "Proxy 1: agentic-ai-gateway (/v1/agentic-fsi)",
                    "hop": "Hop 1: Northbound Root",
                    "verdict": "200_ALLOWED",
                    "user_email": "admin@cviscontino.altostrat.com",
                },
            },
            "resource": res,
            "points": pt_int(wave + 2),
        },
        {
            "metric": {
                "type": "custom.googleapis.com/agentic_fsi/proxy_requests_per_min",
                "labels": {
                    "proxy_name": "Proxy 2: vertex-gemini-llm-gateway (/v1/llm/gemini)",
                    "hop": "Hop 4: Southbound Gemini LLM",
                    "verdict": "200_ALLOWED",
                    "user_email": "admin@cviscontino.altostrat.com",
                },
            },
            "resource": res,
            "points": pt_int(wave + 2),
        },
        {
            "metric": {
                "type": "custom.googleapis.com/agentic_fsi/proxy_requests_per_min",
                "labels": {
                    "proxy_name": "Proxy 3: a2a-agent-1-tx-risk (/v1/a2a/agent-1)",
                    "hop": "Hop 2a: East-West A2A Agent 1",
                    "verdict": "200_ALLOWED",
                    "user_email": "admin@cviscontino.altostrat.com",
                },
            },
            "resource": res,
            "points": pt_int(wave + 2),
        },
        {
            "metric": {
                "type": "custom.googleapis.com/agentic_fsi/proxy_requests_per_min",
                "labels": {
                    "proxy_name": "Proxy 4: a2a-agent-2-aml-kyc (/v1/a2a/agent-2)",
                    "hop": "Hop 2b: East-West A2A Agent 2",
                    "verdict": "200_ALLOWED",
                    "user_email": "admin@cviscontino.altostrat.com",
                },
            },
            "resource": res,
            "points": pt_int(wave + 2),
        },
        {
            "metric": {
                "type": "custom.googleapis.com/agentic_fsi/proxy_requests_per_min",
                "labels": {
                    "proxy_name": "Proxy 5: bigquery-mcp-gateway (/v1/mcp/bigquery)",
                    "hop": "Hop 3: Southbound BigQuery MCP",
                    "verdict": "200_ALLOWED",
                    "user_email": "admin@cviscontino.altostrat.com",
                },
            },
            "resource": res,
            "points": pt_int((wave + 2) * 2),
        },
        {
            "metric": {
                "type": "custom.googleapis.com/agentic_fsi/proxy_requests_per_min",
                "labels": {
                    "proxy_name": "Proxy 1: agentic-ai-gateway (/v1/agentic-fsi)",
                    "hop": "Hop 1: Northbound Root",
                    "verdict": "422_MODEL_ARMOR_BLOCKED",
                    "user_email": "admin@cviscontino.altostrat.com",
                },
            },
            "resource": res,
            "points": pt_int(1 + (step_idx % 2)),
        },
        {
            "metric": {
                "type": "custom.googleapis.com/agentic_fsi/proxy_requests_per_min",
                "labels": {
                    "proxy_name": "Proxy 2: vertex-gemini-llm-gateway (/v1/llm/gemini)",
                    "hop": "Hop 4: Southbound Gemini LLM",
                    "verdict": "429_LLM_TOKEN_QUOTA",
                    "user_email": "admin@cviscontino.altostrat.com",
                },
            },
            "resource": res,
            "points": pt_int(1 if step_idx % 3 == 0 else 0),
        },

        # 2. Hop Latencies (ms)
        {
            "metric": {
                "type": "custom.googleapis.com/agentic_fsi/hop_latency_ms",
                "labels": {
                    "hop": "1. Apigee Northbound PreFlow + TokenQuota Check",
                    "proxy_name": "agentic-ai-gateway",
                },
            },
            "resource": res,
            "points": pt_dbl(round(11.4 + (step_idx % 3) * 1.8, 1)),
        },
        {
            "metric": {
                "type": "custom.googleapis.com/agentic_fsi/hop_latency_ms",
                "labels": {
                    "hop": "2. Cloud Model Armor Inspection (Input + Output)",
                    "proxy_name": "agentic-ai-gateway",
                },
            },
            "resource": res,
            "points": pt_dbl(round(68.0 + (step_idx % 4) * 6.5, 1)),
        },
        {
            "metric": {
                "type": "custom.googleapis.com/agentic_fsi/hop_latency_ms",
                "labels": {
                    "hop": "3. East-West A2A Sub-Agents (Agent 1 & Agent 2)",
                    "proxy_name": "a2a-agent-1-tx-risk & a2a-agent-2-aml-kyc",
                },
            },
            "resource": res,
            "points": pt_dbl(round(145.0 + (step_idx % 5) * 12.0, 1)),
        },
        {
            "metric": {
                "type": "custom.googleapis.com/agentic_fsi/hop_latency_ms",
                "labels": {
                    "hop": "4. Southbound BigQuery Remote MCP (execute_sql_readonly)",
                    "proxy_name": "bigquery-mcp-gateway",
                },
            },
            "resource": res,
            "points": pt_dbl(round(420.0 + (step_idx % 4) * 38.0, 1)),
        },
        {
            "metric": {
                "type": "custom.googleapis.com/agentic_fsi/hop_latency_ms",
                "labels": {
                    "hop": "5. Vertex AI Gemini 2.5 Flash (:generateContent)",
                    "proxy_name": "vertex-gemini-llm-gateway",
                },
            },
            "resource": res,
            "points": pt_dbl(round(890.0 + (step_idx % 5) * 65.0, 1)),
        },

        # 3. Vertex AI Gemini Token Consumption (via vertex-gemini-llm-gateway)
        {
            "metric": {
                "type": "custom.googleapis.com/agentic_fsi/gemini_tokens_used",
                "labels": {
                    "user_email": "admin@cviscontino.altostrat.com",
                    "token_type": "1_promptTokenCount",
                    "proxy_name": "vertex-gemini-llm-gateway",
                    "model": "gemini-2.5-flash",
                },
            },
            "resource": res,
            "points": pt_int(prompt_tok),
        },
        {
            "metric": {
                "type": "custom.googleapis.com/agentic_fsi/gemini_tokens_used",
                "labels": {
                    "user_email": "admin@cviscontino.altostrat.com",
                    "token_type": "2_candidatesTokenCount",
                    "proxy_name": "vertex-gemini-llm-gateway",
                    "model": "gemini-2.5-flash",
                },
            },
            "resource": res,
            "points": pt_int(cand_tok),
        },
        {
            "metric": {
                "type": "custom.googleapis.com/agentic_fsi/gemini_tokens_used",
                "labels": {
                    "user_email": "admin@cviscontino.altostrat.com",
                    "token_type": "3_totalTokenCount ($.usageMetadata.totalTokenCount)",
                    "proxy_name": "vertex-gemini-llm-gateway",
                    "model": "gemini-2.5-flash",
                },
            },
            "resource": res,
            "points": pt_int(tot_tok),
        },

        # 4. OOTB <LLMTokenQuota> Rolling Window Utilization (%)
        {
            "metric": {
                "type": "custom.googleapis.com/agentic_fsi/llm_token_quota_utilization_pct",
                "labels": {
                    "user_email": "admin@cviscontino.altostrat.com",
                    "shared_counter": "user-gemini-token-counter",
                    "proxy_name": "vertex-gemini-llm-gateway",
                },
            },
            "resource": res,
            "points": pt_dbl(quota_pct),
        },

        # 5. Cloud Model Armor Verdicts & Threat Categories
        {
            "metric": {
                "type": "custom.googleapis.com/agentic_fsi/model_armor_inspections",
                "labels": {
                    "hop_phase": "All_4_Hops (Input + A2A + MCP + Output)",
                    "verdict": "NO_MATCH_FOUND (Clean)",
                    "detector": "CLEAN_PASSED",
                },
            },
            "resource": res,
            "points": pt_int((wave + 2) * 4),
        },
        {
            "metric": {
                "type": "custom.googleapis.com/agentic_fsi/model_armor_inspections",
                "labels": {
                    "hop_phase": "Northbound_Input",
                    "verdict": "MATCH_FOUND (Blocked 422)",
                    "detector": "PI_AND_JAILBREAK",
                },
            },
            "resource": res,
            "points": pt_int(1 if step_idx % 2 == 0 else 2),
        },
        {
            "metric": {
                "type": "custom.googleapis.com/agentic_fsi/model_armor_inspections",
                "labels": {
                    "hop_phase": "Northbound_Input & Output",
                    "verdict": "MATCH_FOUND (Blocked/Masked)",
                    "detector": "SDP_PII_IBAN_DEID",
                },
            },
            "resource": res,
            "points": pt_int(1),
        },
        {
            "metric": {
                "type": "custom.googleapis.com/agentic_fsi/model_armor_inspections",
                "labels": {
                    "hop_phase": "Southbound_MCP_SQL",
                    "verdict": "MATCH_FOUND (Blocked 422)",
                    "detector": "MALICIOUS_URI_AND_SQLI",
                },
            },
            "resource": res,
            "points": pt_int(1 if step_idx % 3 == 0 else 0),
        },

        # 6. East-West A2A Sub-Agent Tasks (via Proxies 3 & 4)
        {
            "metric": {
                "type": "custom.googleapis.com/agentic_fsi/a2a_subagent_tasks",
                "labels": {
                    "agent_id": "agent-1-tx-risk-analytics",
                    "apigee_proxy": "Proxy 3: a2a-agent-1-tx-risk (/v1/a2a/agent-1)",
                    "status": "COMPLETED_VIA_APIGEE",
                },
            },
            "resource": res,
            "points": pt_int(wave + 2),
        },
        {
            "metric": {
                "type": "custom.googleapis.com/agentic_fsi/a2a_subagent_tasks",
                "labels": {
                    "agent_id": "agent-2-compliance-aml-kyc",
                    "apigee_proxy": "Proxy 4: a2a-agent-2-aml-kyc (/v1/a2a/agent-2)",
                    "status": "COMPLETED_VIA_APIGEE",
                },
            },
            "resource": res,
            "points": pt_int(wave + 2),
        },

        # 7. Southbound BigQuery Remote MCP Queries (via Proxy 5: bigquery-mcp-gateway)
        {
            "metric": {
                "type": "custom.googleapis.com/agentic_fsi/bq_mcp_queries",
                "labels": {
                    "caller_agent": "agent-1-tx-risk-analytics",
                    "table": "transactions_ledger",
                    "apigee_proxy": "Proxy 5: bigquery-mcp-gateway (/v1/mcp/bigquery)",
                },
            },
            "resource": res,
            "points": pt_int(wave + 2),
        },
        {
            "metric": {
                "type": "custom.googleapis.com/agentic_fsi/bq_mcp_queries",
                "labels": {
                    "caller_agent": "agent-2-compliance-aml-kyc",
                    "table": "customer_portfolios & aml_compliance_alerts",
                    "apigee_proxy": "Proxy 5: bigquery-mcp-gateway (/v1/mcp/bigquery)",
                },
            },
            "resource": res,
            "points": pt_int(wave + 2),
        },
    ]
    return series


def build_dashboard_json() -> dict:
    """Builds the 12-column Mosaic Cloud Monitoring Custom Dashboard definition."""
    return {
        "displayName": DASHBOARD_DISPLAY_NAME,
        "mosaicLayout": {
            "columns": 12,
            "tiles": [
                # Row 0: Executive Architecture Header Banner
                {
                    "xPos": 0,
                    "yPos": 0,
                    "width": 12,
                    "height": 2,
                    "widget": {
                        "title": "Zero-Trust Agentic FSI Architecture — End-to-End Observability (5 Apigee X Proxies · Zero Direct Invocations)",
                        "text": {
                            "content": (
                                "**Catena di Mediazione Zero-Trust (`cvisco-agentic-demo` · `agentic-prod`)**:\n"
                                "1. **Hop 1 (Northbound)**: Client (`admin@cviscontino.altostrat.com`) $\\rightarrow$ **`Proxy 1: agentic-ai-gateway` (`/v1/agentic-fsi`)** $\\rightarrow$ Gemini Enterprise Root Orchestrator\n"
                                "2. **Hop 2 (East-West A2A)**: Root Orchestrator $\\rightarrow$ **`Proxy 3: a2a-agent-1-tx-risk` (`/v1/a2a/agent-1`)** & **`Proxy 4: a2a-agent-2-aml-kyc` (`/v1/a2a/agent-2`)** $\\rightarrow$ Sub-Agents 1 & 2\n"
                                "3. **Hop 3 (Southbound MCP)**: A2A Sub-Agents 1 & 2 $\\rightarrow$ **`Proxy 5: bigquery-mcp-gateway` (`/v1/mcp/bigquery`)** $\\rightarrow$ BigQuery Remote MCP Server (`execute_sql_readonly`)\n"
                                "4. **Hop 4 (Southbound LLM + OOTB Token Quota)**: Root Orchestrator $\\rightarrow$ **`Proxy 2: vertex-gemini-llm-gateway` (`/v1/llm/gemini`)** con policy Out-of-the-Box **`<LLMTokenQuota>` (`Q-TokenQuota-Enforce` + `Q-TokenQuota-Count` su `$.usageMetadata.totalTokenCount`)** $\\rightarrow$ Vertex AI Gemini 2.5 Flash"
                            ),
                            "format": "MARKDOWN",
                        },
                    },
                },
                # Row 1: 4 Executive Scorecards
                {
                    "xPos": 0,
                    "yPos": 2,
                    "width": 3,
                    "height": 3,
                    "widget": {
                        "title": "1. Chiamate Mediate dai 5 Proxy Apigee X (ultimi 5m)",
                        "scorecard": {
                            "timeSeriesQuery": {
                                "timeSeriesFilter": {
                                    "filter": 'metric.type="custom.googleapis.com/agentic_fsi/proxy_requests_per_min" resource.type="global"',
                                    "aggregation": {
                                        "alignmentPeriod": "300s",
                                        "perSeriesAligner": "ALIGN_SUM",
                                        "crossSeriesReducer": "REDUCE_SUM",
                                    },
                                }
                            },
                            "sparkChartView": {"sparkChartType": "SPARK_BAR"},
                        },
                    },
                },
                {
                    "xPos": 3,
                    "yPos": 2,
                    "width": 3,
                    "height": 3,
                    "widget": {
                        "title": "2. Apigee OOTB <LLMTokenQuota> % (admin@cviscontino.altostrat.com)",
                        "scorecard": {
                            "timeSeriesQuery": {
                                "timeSeriesFilter": {
                                    "filter": 'metric.type="custom.googleapis.com/agentic_fsi/llm_token_quota_utilization_pct" resource.type="global"',
                                    "aggregation": {
                                        "alignmentPeriod": "60s",
                                        "perSeriesAligner": "ALIGN_MEAN",
                                        "crossSeriesReducer": "REDUCE_MAX",
                                    },
                                }
                            },
                            "gaugeView": {"lowerBound": 0.0, "upperBound": 100.0},
                            "thresholds": [
                                {"label": "Warning (70%)", "value": 70.0, "color": "YELLOW", "direction": "ABOVE"},
                                {"label": "Quota 429 Risk (90%)", "value": 90.0, "color": "RED", "direction": "ABOVE"},
                            ],
                        },
                    },
                },
                {
                    "xPos": 6,
                    "yPos": 2,
                    "width": 3,
                    "height": 3,
                    "widget": {
                        "title": "3. Token Vertex AI Gemini Consumati ($.usageMetadata.totalTokenCount)",
                        "scorecard": {
                            "timeSeriesQuery": {
                                "timeSeriesFilter": {
                                    "filter": 'metric.type="custom.googleapis.com/agentic_fsi/gemini_tokens_used" resource.type="global" metric.label."token_type"="3_totalTokenCount ($.usageMetadata.totalTokenCount)"',
                                    "aggregation": {
                                        "alignmentPeriod": "300s",
                                        "perSeriesAligner": "ALIGN_SUM",
                                        "crossSeriesReducer": "REDUCE_SUM",
                                    },
                                }
                            },
                            "sparkChartView": {"sparkChartType": "SPARK_LINE"},
                        },
                    },
                },
                {
                    "xPos": 9,
                    "yPos": 2,
                    "width": 3,
                    "height": 3,
                    "widget": {
                        "title": "4. Minacce Bloccate da Cloud Model Armor (HTTP 422)",
                        "scorecard": {
                            "timeSeriesQuery": {
                                "timeSeriesFilter": {
                                    "filter": 'metric.type="custom.googleapis.com/agentic_fsi/model_armor_inspections" resource.type="global" metric.label."detector"!="CLEAN_PASSED"',
                                    "aggregation": {
                                        "alignmentPeriod": "300s",
                                        "perSeriesAligner": "ALIGN_SUM",
                                        "crossSeriesReducer": "REDUCE_SUM",
                                    },
                                }
                            },
                            "sparkChartView": {"sparkChartType": "SPARK_BAR"},
                            "thresholds": [
                                {"label": "Active Threat Mitigation", "value": 1.0, "color": "RED", "direction": "ABOVE"},
                            ],
                        },
                    },
                },
                # Row 2: Apigee 5-Proxy Traffic & Vertex AI Gemini Token Quota Breakdown
                {
                    "xPos": 0,
                    "yPos": 5,
                    "width": 6,
                    "height": 4,
                    "widget": {
                        "title": "Hop 1..4 — Traffico Mediato per Proxy Apigee X (5 Proxy Attivi · Zero Chiamate Dirette)",
                        "xyChart": {
                            "dataSets": [
                                {
                                    "timeSeriesQuery": {
                                        "timeSeriesFilter": {
                                            "filter": 'metric.type="custom.googleapis.com/agentic_fsi/proxy_requests_per_min" resource.type="global"',
                                            "aggregation": {
                                                "alignmentPeriod": "60s",
                                                "perSeriesAligner": "ALIGN_SUM",
                                                "crossSeriesReducer": "REDUCE_SUM",
                                                "groupByFields": ["metric.label.proxy_name", "metric.label.verdict"],
                                            },
                                        }
                                    },
                                    "plotType": "STACKED_BAR",
                                    "legendTemplate": "${metric.labels.proxy_name} [${metric.labels.verdict}]",
                                }
                            ],
                            "yAxis": {"label": "Requests / min", "scale": "LINEAR"},
                        },
                    },
                },
                {
                    "xPos": 6,
                    "yPos": 5,
                    "width": 6,
                    "height": 4,
                    "widget": {
                        "title": "Hop 4 — Vertex AI Gemini Token Consumption (Proxy 2: vertex-gemini-llm-gateway · OOTB <LLMTokenQuota>)",
                        "xyChart": {
                            "dataSets": [
                                {
                                    "timeSeriesQuery": {
                                        "timeSeriesFilter": {
                                            "filter": 'metric.type="custom.googleapis.com/agentic_fsi/gemini_tokens_used" resource.type="global"',
                                            "aggregation": {
                                                "alignmentPeriod": "60s",
                                                "perSeriesAligner": "ALIGN_MEAN",
                                                "crossSeriesReducer": "REDUCE_SUM",
                                                "groupByFields": ["metric.label.token_type", "metric.label.user_email"],
                                            },
                                        }
                                    },
                                    "plotType": "LINE",
                                    "legendTemplate": "${metric.labels.token_type} (${metric.labels.user_email})",
                                }
                            ],
                            "yAxis": {"label": "Tokens", "scale": "LINEAR"},
                        },
                    },
                },
                # Row 3: Cloud Model Armor Threat Verdicts & End-to-End Hop Latency
                {
                    "xPos": 0,
                    "yPos": 9,
                    "width": 6,
                    "height": 4,
                    "widget": {
                        "title": "Cloud Model Armor (fsi-agent-armor-strict) — Ispezioni e Minacce Bloccate (PI/Jailbreak, SDP IBAN, SQLi/URI)",
                        "xyChart": {
                            "dataSets": [
                                {
                                    "timeSeriesQuery": {
                                        "timeSeriesFilter": {
                                            "filter": 'metric.type="custom.googleapis.com/agentic_fsi/model_armor_inspections" resource.type="global"',
                                            "aggregation": {
                                                "alignmentPeriod": "60s",
                                                "perSeriesAligner": "ALIGN_SUM",
                                                "crossSeriesReducer": "REDUCE_SUM",
                                                "groupByFields": ["metric.label.detector", "metric.label.verdict"],
                                            },
                                        }
                                    },
                                    "plotType": "STACKED_BAR",
                                    "legendTemplate": "${metric.labels.detector} — ${metric.labels.verdict}",
                                }
                            ],
                            "yAxis": {"label": "Inspections", "scale": "LINEAR"},
                        },
                    },
                },
                {
                    "xPos": 6,
                    "yPos": 9,
                    "width": 6,
                    "height": 4,
                    "widget": {
                        "title": "Latenza End-to-End Scomposta per Hop (ms) attraverso i 5 Proxy Apigee X",
                        "xyChart": {
                            "dataSets": [
                                {
                                    "timeSeriesQuery": {
                                        "timeSeriesFilter": {
                                            "filter": 'metric.type="custom.googleapis.com/agentic_fsi/hop_latency_ms" resource.type="global"',
                                            "aggregation": {
                                                "alignmentPeriod": "60s",
                                                "perSeriesAligner": "ALIGN_MEAN",
                                                "crossSeriesReducer": "REDUCE_MEAN",
                                                "groupByFields": ["metric.label.hop", "metric.label.proxy_name"],
                                            },
                                        }
                                    },
                                    "plotType": "LINE",
                                    "legendTemplate": "${metric.labels.hop} [${metric.labels.proxy_name}]",
                                }
                            ],
                            "yAxis": {"label": "Latency (ms)", "scale": "LINEAR"},
                        },
                    },
                },
                # Row 4: East-West A2A Sub-Agents & Southbound BigQuery Remote MCP
                {
                    "xPos": 0,
                    "yPos": 13,
                    "width": 6,
                    "height": 4,
                    "widget": {
                        "title": "Hop 2 (East-West A2A) — Task JSON-RPC 2.0 Mediati da Proxy 3 (a2a-agent-1-tx-risk) & Proxy 4 (a2a-agent-2-aml-kyc)",
                        "xyChart": {
                            "dataSets": [
                                {
                                    "timeSeriesQuery": {
                                        "timeSeriesFilter": {
                                            "filter": 'metric.type="custom.googleapis.com/agentic_fsi/a2a_subagent_tasks" resource.type="global"',
                                            "aggregation": {
                                                "alignmentPeriod": "60s",
                                                "perSeriesAligner": "ALIGN_SUM",
                                                "crossSeriesReducer": "REDUCE_SUM",
                                                "groupByFields": ["metric.label.agent_id", "metric.label.apigee_proxy"],
                                            },
                                        }
                                    },
                                    "plotType": "STACKED_BAR",
                                    "legendTemplate": "${metric.labels.agent_id} via ${metric.labels.apigee_proxy}",
                                }
                            ],
                            "yAxis": {"label": "A2A Tasks / min", "scale": "LINEAR"},
                        },
                    },
                },
                {
                    "xPos": 6,
                    "yPos": 13,
                    "width": 6,
                    "height": 4,
                    "widget": {
                        "title": "Hop 3 (Southbound MCP) — Query SQL Read-Only su BigQuery MCP via Proxy 5 (bigquery-mcp-gateway)",
                        "xyChart": {
                            "dataSets": [
                                {
                                    "timeSeriesQuery": {
                                        "timeSeriesFilter": {
                                            "filter": 'metric.type="custom.googleapis.com/agentic_fsi/bq_mcp_queries" resource.type="global"',
                                            "aggregation": {
                                                "alignmentPeriod": "60s",
                                                "perSeriesAligner": "ALIGN_SUM",
                                                "crossSeriesReducer": "REDUCE_SUM",
                                                "groupByFields": ["metric.label.table", "metric.label.caller_agent"],
                                            },
                                        }
                                    },
                                    "plotType": "STACKED_AREA",
                                    "legendTemplate": "Table: ${metric.labels.table} (Caller: ${metric.labels.caller_agent})",
                                }
                            ],
                            "yAxis": {"label": "MCP SQL Queries / min", "scale": "LINEAR"},
                        },
                    },
                },
                # Row 5: Native Google Cloud Infrastructure Telemetry (Cloud Run & BigQuery)
                {
                    "xPos": 0,
                    "yPos": 17,
                    "width": 6,
                    "height": 4,
                    "widget": {
                        "title": "Infrastruttura Cloud Run (agentic-fsi-demo) — Request Rate per Response Code",
                        "xyChart": {
                            "dataSets": [
                                {
                                    "timeSeriesQuery": {
                                        "timeSeriesFilter": {
                                            "filter": 'metric.type="run.googleapis.com/request_count" resource.type="cloud_run_revision"',
                                            "aggregation": {
                                                "alignmentPeriod": "60s",
                                                "perSeriesAligner": "ALIGN_RATE",
                                                "crossSeriesReducer": "REDUCE_SUM",
                                                "groupByFields": ["resource.label.service_name", "metric.label.response_code_class"],
                                            },
                                        }
                                    },
                                    "plotType": "LINE",
                                    "legendTemplate": "${resource.labels.service_name} (${metric.labels.response_code_class})",
                                }
                            ],
                            "yAxis": {"label": "Req / s", "scale": "LINEAR"},
                        },
                    },
                },
                {
                    "xPos": 6,
                    "yPos": 17,
                    "width": 6,
                    "height": 4,
                    "widget": {
                        "title": "Infrastruttura BigQuery (agentic_fsi_fraud_demo) — Query Eseguite & Scanned Bytes",
                        "xyChart": {
                            "dataSets": [
                                {
                                    "timeSeriesQuery": {
                                        "timeSeriesFilter": {
                                            "filter": 'metric.type="bigquery.googleapis.com/query/count" resource.type="bigquery_project"',
                                            "aggregation": {
                                                "alignmentPeriod": "60s",
                                                "perSeriesAligner": "ALIGN_MAX",
                                                "crossSeriesReducer": "REDUCE_SUM",
                                            },
                                        }
                                    },
                                    "plotType": "LINE",
                                    "legendTemplate": "BigQuery Active Queries",
                                }
                            ],
                            "yAxis": {"label": "Queries", "scale": "LINEAR"},
                        },
                    },
                },
                # Row 6: Live End-to-End Audit & Cloud Logging Stream
                {
                    "xPos": 0,
                    "yPos": 21,
                    "width": 12,
                    "height": 5,
                    "widget": {
                        "title": "Live Audit & Telemetry Logs — Apigee X, Cloud Model Armor, A2A Sub-Agents, BigQuery MCP & Cloud Run",
                        "logsPanel": {
                            "filter": 'resource.type="cloud_run_revision" OR resource.type="bigquery_resource" OR resource.type="audited_resource"',
                            "resourceNames": [f"projects/{PROJECT_ID}"],
                        },
                    },
                },
            ],
        },
    }


def main():
    headers = get_headers()
    with httpx.Client(headers=headers, timeout=60.0) as client:
        print("=== 1. Creating Custom Metric Descriptors in Cloud Monitoring ===")
        for md in METRIC_DESCRIPTORS:
            r_md = client.post(
                f"https://monitoring.googleapis.com/v3/projects/{PROJECT_ID}/metricDescriptors",
                json=md,
            )
            print(f" [MetricDescriptor] {md['type']} -> HTTP {r_md.status_code}")

        print("\n=== 2. Seeding Chronological Historical TimeSeries Across All 5 Hops ===")
        now_utc = datetime.datetime.now(datetime.timezone.utc)
        # Write 8 chronological points spaced 2 minutes apart (oldest to newest)
        num_steps = 8
        for i in range(num_steps):
            minutes_ago = (num_steps - 1 - i) * 2
            ts_dt = now_utc - datetime.timedelta(minutes=minutes_ago)
            ts_iso = ts_dt.strftime("%Y-%m-%dT%H:%M:%SZ")
            batch = build_timeseries_batch(ts_iso, step_idx=i)
            r_ts = client.post(
                f"https://monitoring.googleapis.com/v3/projects/{PROJECT_ID}/timeSeries",
                json={"timeSeries": batch},
            )
            print(f" [TimeSeries Seed #{i+1}/{num_steps} @ {ts_iso}] ({len(batch)} series) -> HTTP {r_ts.status_code}")
            if r_ts.status_code != 200:
                print("   Error detail:", r_ts.text[:300])
            time.sleep(0.3)

        print("\n=== 3. Creating / Updating Cloud Monitoring Custom Dashboard ===")
        r_list = client.get(f"https://monitoring.googleapis.com/v1/projects/{PROJECT_ID}/dashboards")
        existing_dash = None
        for d in r_list.json().get("dashboards", []):
            if d.get("displayName") == DASHBOARD_DISPLAY_NAME:
                existing_dash = d
                break

        dash_body = build_dashboard_json()
        if existing_dash:
            dash_name = existing_dash["name"]
            dash_body["etag"] = existing_dash["etag"]
            r_d = client.patch(
                f"https://monitoring.googleapis.com/v1/{dash_name}",
                json=dash_body,
            )
            print(f" [Dashboard Updated] {dash_name} -> HTTP {r_d.status_code}")
            result_dash = r_d.json()
        else:
            r_d = client.post(
                f"https://monitoring.googleapis.com/v1/projects/{PROJECT_ID}/dashboards",
                json=dash_body,
            )
            print(f" [Dashboard Created] -> HTTP {r_d.status_code}")
            if r_d.status_code != 200:
                print("   Error detail:", r_d.text[:500])
            result_dash = r_d.json()

        dash_id = result_dash.get("name", "").split("/")[-1]
        console_url = f"https://console.cloud.google.com/monitoring/dashboards/builder/{dash_id}?project={PROJECT_ID}&duration=PT1H"
        print(f"\n✅ Custom Dashboard Live URL:\n{console_url}")


if __name__ == "__main__":
    main()
