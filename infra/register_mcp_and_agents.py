import json
import time
import httpx
import google.auth
import google.auth.transport.requests

PROJECT_ID = "cvisco-agentic-demo"
PROJECT_NUMBER = "1070899805958"
LOCATION = "europe-west1"
APIGEE_GATEWAY_URL = "https://api.cvisco-agentic-demo.internal"
BASE_AR_URL = f"https://agentregistry.googleapis.com/v1alpha/projects/{PROJECT_ID}/locations/{LOCATION}"


def wait_op(client: httpx.Client, op_name: str, headers: dict):
    for _ in range(25):
        r = client.get(f"https://agentregistry.googleapis.com/v1alpha/{op_name}", headers=headers)
        if r.status_code == 200 and r.json().get("done"):
            return r.json()
        time.sleep(1.0)
    return {}


def main():
    creds, _ = google.auth.default(scopes=["https://www.googleapis.com/auth/cloud-platform"])
    creds.refresh(google.auth.transport.requests.Request())
    headers = {
        "Authorization": f"Bearer {creds.token}",
        "x-goog-user-project": PROJECT_ID,
        "Content-Type": "application/json",
    }

    with httpx.Client(timeout=60.0) as client:
        # 1. Register Root Agent + 2 A2A Sub-Agents with protocolVersion 0.3.0 (Strictly via Apigee X Proxies)
        agents_to_register = [
            {
                "serviceId": "ge-root-orchestrator",
                "displayName": "Gemini Enterprise Root Multi-Agent Orchestrator",
                "description": "Root Supervisor Agent mediated strictly by Apigee X (agentic-ai-gateway) and Cloud Model Armor. Decomposes FSI Fraud & Compliance prompts into parallel A2A tasks.",
                "card": {
                    "name": "ge-root-orchestrator",
                    "description": "Gemini Enterprise Root Multi-Agent Orchestrator for FSI Fraud & AML (Apigee X Mediated)",
                    "url": f"{APIGEE_GATEWAY_URL}/v1/agentic-fsi",
                    "version": "1.0.0",
                    "protocolVersion": "0.3.0",
                    "capabilities": {"streaming": False, "pushNotifications": False},
                    "defaultInputModes": ["text/plain", "application/json"],
                    "defaultOutputModes": ["application/json"],
                    "skills": [
                        {
                            "id": "orchestrate-fsi-investigation",
                            "name": "FSI Multi-Agent A2A Orchestration (Apigee Mediated)",
                            "description": "Coordinates Agent 1 (via /v1/a2a/agent-1), Agent 2 (via /v1/a2a/agent-2), and Vertex AI Gemini (via /v1/llm/gemini) strictly through Apigee X Proxies.",
                            "tags": ["a2a", "orchestrator", "gemini-enterprise", "apigee", "model-armor", "llm-token-quota"],
                        }
                    ],
                },
            },
            {
                "serviceId": "agent-1-tx-risk-analytics",
                "displayName": "Agent 1 — Transaction & Risk Analytics (A2A)",
                "description": "A2A Sub-Agent mediated strictly by Apigee X Proxy (a2a-agent-1-tx-risk) for real-time transaction velocity, structuring detection, and anomaly scoring on BigQuery via bigquery-mcp-gateway.",
                "card": {
                    "name": "agent-1-tx-risk-analytics",
                    "description": "A2A Sub-Agent for Transaction & Risk Analytics mediated by Apigee X Proxy (/v1/a2a/agent-1)",
                    "url": f"{APIGEE_GATEWAY_URL}/v1/a2a/agent-1",
                    "version": "1.0.0",
                    "protocolVersion": "0.3.0",
                    "capabilities": {"streaming": False, "pushNotifications": False},
                    "defaultInputModes": ["application/json"],
                    "defaultOutputModes": ["application/json"],
                    "skills": [
                        {
                            "id": "bq-mcp-tx-anomaly-scan",
                            "name": "BigQuery MCP Transaction Anomaly Scan (Apigee Mediated)",
                            "description": "Queries cvisco-agentic-demo.agentic_fsi_fraud_demo.transactions_ledger strictly via Apigee Proxy /v1/mcp/bigquery (bigquery-mcp-gateway).",
                            "tags": ["a2a", "bigquery-mcp", "fraud-detection", "transactions", "apigee-proxy"],
                        }
                    ],
                },
            },
            {
                "serviceId": "agent-2-compliance-aml-kyc",
                "displayName": "Agent 2 — Compliance & Customer Portfolio AML/KYC (A2A)",
                "description": "A2A Sub-Agent mediated strictly by Apigee X Proxy (a2a-agent-2-aml-kyc) for AML/KYC alerts, PEP screening, and wealth portfolio risk correlation on BigQuery via bigquery-mcp-gateway.",
                "card": {
                    "name": "agent-2-compliance-aml-kyc",
                    "description": "A2A Sub-Agent for AML/KYC Compliance & Customer Portfolio mediated by Apigee X Proxy (/v1/a2a/agent-2)",
                    "url": f"{APIGEE_GATEWAY_URL}/v1/a2a/agent-2",
                    "version": "1.0.0",
                    "protocolVersion": "0.3.0",
                    "capabilities": {"streaming": False, "pushNotifications": False},
                    "defaultInputModes": ["application/json"],
                    "defaultOutputModes": ["application/json"],
                    "skills": [
                        {
                            "id": "bq-mcp-aml-portfolio-audit",
                            "name": "BigQuery MCP AML & Portfolio Audit (Apigee Mediated)",
                            "description": "Queries customer_portfolios and aml_compliance_alerts in BigQuery strictly via Apigee Proxy /v1/mcp/bigquery (bigquery-mcp-gateway).",
                            "tags": ["a2a", "bigquery-mcp", "aml", "kyc", "compliance", "apigee-proxy"],
                        }
                    ],
                },
            },
        ]

        for ag in agents_to_register:
            print(f"\n--- Registering A2A Agent: {ag['serviceId']} ---")
            payload = {
                "displayName": ag["displayName"],
                "description": ag["description"],
                "agentSpec": {
                    "type": "A2A_AGENT_CARD",
                    "content": ag["card"],
                },
            }
            r_ag = client.post(
                f"{BASE_AR_URL}/services",
                params={"serviceId": ag["serviceId"]},
                headers=headers,
                json=payload,
            )
            if r_ag.status_code == 200 and "operations/" in r_ag.json().get("name", ""):
                res = wait_op(client, r_ag.json()["name"], headers)
                print(f"{ag['serviceId']} Op Result:", json.dumps(res, indent=2)[:500])
            else:
                print(f"Create {ag['serviceId']}:", r_ag.status_code, r_ag.text[:400])

        # 2. List Agents and MCP Servers to get their exact URNs
        r_agents = client.get(f"{BASE_AR_URL}/agents", headers=headers).json().get("agents", [])
        r_mcps = client.get(f"{BASE_AR_URL}/mcpServers", headers=headers).json().get("mcpServers", [])
        print("\n--- Registered Agents in europe-west1 ---")
        agent_urns = {}
        for a in r_agents:
            print(" ->", a.get("displayName"), "|", a.get("agentId"))
            agent_urns[a.get("displayName")] = a.get("agentId")

        print("\n--- Registered MCP Servers in europe-west1 ---")
        for m in r_mcps:
            print(" ->", m.get("displayName"), "|", m.get("mcpServerId"))


if __name__ == "__main__":
    main()
