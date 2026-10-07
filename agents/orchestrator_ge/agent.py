"""
Gemini Enterprise / Vertex AI Agent Engine - Root Orchestrator Agent
Coordinates 2 Remote Specialist Sub-Agents via the Agent-to-Agent (A2A) Protocol:
  1. Transaction & Risk Analytics Agent (A2A) -> BigQuery MCP
  2. Compliance & Customer Portfolio Agent (A2A) -> BigQuery MCP
"""
import os
from google.adk.agents import LlmAgent
from google.adk.agents.remote_a2a_agent import RemoteA2aAgent

PROJECT_ID = os.getenv("GCP_PROJECT_ID", "cvisco-agentic-demo")
A2A_TX_RISK_URL = os.getenv(
    "A2A_TX_RISK_URL", "http://localhost:8000/a2a/transaction-risk/.well-known/agent.json"
)
A2A_COMPLIANCE_URL = os.getenv(
    "A2A_COMPLIANCE_URL", "http://localhost:8000/a2a/compliance-portfolio/.well-known/agent.json"
)

# Remote A2A Specialist Agent 1: Transaction & Fraud Velocity Analytics
transaction_risk_a2a_agent = RemoteA2aAgent(
    name="transaction_risk_a2a_agent",
    description=(
        "Specialist A2A Agent for real-time banking transaction risk scoring, "
        "SWIFT/SEPA anomaly detection, velocity spikes, and fraud typologies "
        "(Cross-Border Structuring, Account Takeover, Synthetic Identity). "
        "Interfaces with BigQuery via MCP."
    ),
    agent_card=A2A_TX_RISK_URL,
)

# Remote A2A Specialist Agent 2: AML Compliance, KYC, PEP & Customer Portfolio
compliance_portfolio_a2a_agent = RemoteA2aAgent(
    name="compliance_portfolio_a2a_agent",
    description=(
        "Specialist A2A Agent for AML/KYC compliance status, Politically Exposed Persons (PEP), "
        "OFAC/EU sanctions screening, SAR filing status (EU AMLD6, FATF, PSD3), and "
        "wealth/corporate portfolio exposure. Interfaces with BigQuery via MCP."
    ),
    agent_card=A2A_COMPLIANCE_URL,
)

# Root Multi-Agent deployed on Vertex AI Agent Engine & registered in Gemini Enterprise
root_agent = LlmAgent(
    name="fsi_enterprise_orchestrator",
    model="gemini-2.5-pro",
    description=(
        "Enterprise Financial Crime & Risk Orchestrator on Gemini Enterprise, "
        "protected upstream by Apigee AI Gateway and Google Cloud Model Armor."
    ),
    instruction="""You are the Chief Financial Crime & Risk Orchestrator running on Google Cloud Gemini Enterprise.
All incoming user requests have already been inspected by Apigee X and Google Cloud Model Armor for Prompt Injection, Jailbreak, and Sensitive Data Protection (SDP).

For every analytical or operational investigation:
1. Delegate transaction-level risk, SWIFT/SEPA wire anomalies, and velocity checks to `transaction_risk_a2a_agent` over the A2A protocol.
2. Delegate KYC status, PEP screening, OFAC sanctions, EU AMLD6 / PSD3 alerts, and customer AUM/credit exposure checks to `compliance_portfolio_a2a_agent` over the A2A protocol.
3. Synthesize findings from both A2A sub-agents into a structured executive risk briefing citing exact transaction IDs, customer IDs, EUR exposures, and regulatory frameworks retrieved from BigQuery via MCP.
Never fabricate records or bypass compliance policies.""",
    sub_agents=[transaction_risk_a2a_agent, compliance_portfolio_a2a_agent],
)
