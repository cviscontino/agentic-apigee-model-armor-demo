"""
A2A Sub-Agent 1: Transaction & Risk Analytics Agent
Exposes an A2A-compliant server (/.well-known/agent.json + JSON-RPC tasks/send)
and queries BigQuery `my-ca-test-486412.agentic_fsi_fraud_demo.transactions_ledger`
exclusively via the Google Cloud BigQuery MCP Server.
"""
import os
from google.adk.agents import LlmAgent
from google.adk.tools.mcp_tool.mcp_toolset import MCPToolset, SseConnectionParams
from google.adk.a2a.utils.agent_to_a2a import to_a2a

PROJECT_ID = os.getenv("GCP_PROJECT_ID", "cvisco-agentic-demo")
DATASET_ID = os.getenv("BQ_DATASET_ID", "agentic_fsi_fraud_demo")
BQ_MCP_URL = os.getenv("BQ_MCP_SSE_URL", "https://bigquery.googleapis.com/mcp")

bq_mcp_toolset = MCPToolset(
    connection_params=SseConnectionParams(
        url=BQ_MCP_URL,
        headers={"x-goog-user-project": PROJECT_ID},
    ),
    tool_filter=["list_dataset_ids", "list_table_ids", "get_table_info", "execute_sql_readonly"],
)

transaction_risk_agent = LlmAgent(
    name="transaction_risk_analytics_agent",
    model="gemini-2.5-flash",
    description=(
        "A2A Specialist Agent for real-time banking transaction monitoring, "
        "fraud risk scores, cross-border wire structuring, and velocity anomalies."
    ),
    instruction=f"""You are the Transaction & Risk Analytics A2A Agent.
Use the BigQuery MCP tools (`get_table_info`, `execute_sql_readonly`) on project `{PROJECT_ID}` and dataset `{DATASET_ID}`.
Focus on table `{PROJECT_ID}.{DATASET_ID}.transactions_ledger`.
Always use `execute_sql_readonly` with standard GoogleSQL to compute:
- High-risk transactions (`risk_score >= 80` or `status IN ('FLAGGED', 'BLOCKED')`)
- Fraud typologies (`CROSS_BORDER_STRUCTURING`, `ACCOUNT_TAKEOVER`, `SYNTHETIC_IDENTITY`, `CARD_NOT_PRESENT_BURST`)
- Hourly transaction velocity (`velocity_1h`) and corridor exposure (`country_code`, `channel`).""",
    tools=[bq_mcp_toolset],
)

# Expose as an A2A-compliant Starlette/FastAPI application
a2a_app = to_a2a(transaction_risk_agent, port=8001)
