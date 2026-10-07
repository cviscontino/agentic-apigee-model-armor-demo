"""
A2A Sub-Agent 2: Compliance & Customer Portfolio Agent
Exposes an A2A-compliant server (/.well-known/agent.json + JSON-RPC tasks/send)
and queries BigQuery `customer_portfolios` and `aml_compliance_alerts`
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

compliance_portfolio_agent = LlmAgent(
    name="compliance_customer_portfolio_agent",
    model="gemini-2.5-flash",
    description=(
        "A2A Specialist Agent for KYC due diligence, Politically Exposed Persons (PEP), "
        "OFAC/EU sanctions screening, SAR regulatory alerts (EU AMLD6, FATF, PSD3), "
        "and AUM / credit exposure analysis."
    ),
    instruction=f"""You are the Compliance & Customer Portfolio A2A Agent.
Use the BigQuery MCP tools (`get_table_info`, `execute_sql_readonly`) on project `{PROJECT_ID}` and dataset `{DATASET_ID}`.
Focus on tables:
- `{PROJECT_ID}.{DATASET_ID}.customer_portfolios`
- `{PROJECT_ID}.{DATASET_ID}.aml_compliance_alerts`
Provide exact regulatory frameworks (`EU_AMLD6`, `FATF_WIRE_RULE`, `PSD3_FRAUD`), PEP status, OFAC screening status, SAR filing status, and total EUR exposure.""",
    tools=[bq_mcp_toolset],
)

# Expose as an A2A-compliant Starlette/FastAPI application
a2a_app = to_a2a(compliance_portfolio_agent, port=8002)
