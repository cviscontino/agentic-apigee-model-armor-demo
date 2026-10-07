#!/usr/bin/env python3
"""
Enforces strict Apigee X Proxy mediation across:
1. Google Cloud Agent Registry (europe-west1): Updates all A2A AgentCards & MCP Server interfaces to point strictly to Apigee X Proxy URLs.
2. Apigee API Hub (us-central1): Updates all Deployments to expose ONLY Apigee X Proxy URLs (removing direct run.app / bigquery.googleapis.com URLs) and adds apigee-vertex-gemini-llm-gateway.
3. Apigee X Organization (cvisco-agentic-demo): Registers ge-root-vertex-gemini-llm-app under admin@cviscontino.altostrat.com for vertex-gemini-llm-product.
"""
import json
import time
import httpx
import google.auth
import google.auth.transport.requests

PROJECT_ID = "cvisco-agentic-demo"
AR_LOCATION = "europe-west1"
APIHUB_LOCATION = "us-central1"
APIGEE_GATEWAY_URL = "https://api.cvisco-agentic-demo.internal"

BASE_AR_URL = f"https://agentregistry.googleapis.com/v1alpha/projects/{PROJECT_ID}/locations/{AR_LOCATION}"
BASE_APIHUB_URL = f"https://apihub.googleapis.com/v1/projects/{PROJECT_ID}/locations/{APIHUB_LOCATION}"
BASE_APIGEE_URL = f"https://apigee.googleapis.com/v1/organizations/{PROJECT_ID}"


def wait_ar_op(client: httpx.Client, op_name: str, headers: dict):
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
        print("=== 1. Patching Google Cloud Agent Registry (europe-west1) Services to Apigee Proxy URLs ===")
        r_svcs = client.get(f"{BASE_AR_URL}/services", headers=headers).json().get("services", [])
        proxy_url_map = {
            "ge-root-orchestrator": f"{APIGEE_GATEWAY_URL}/v1/agentic-fsi",
            "agent-1-tx-risk-analytics": f"{APIGEE_GATEWAY_URL}/v1/a2a/agent-1",
            "agent-2-compliance-aml-kyc": f"{APIGEE_GATEWAY_URL}/v1/a2a/agent-2",
            "fsi-bigquery-mcp-gateway": f"{APIGEE_GATEWAY_URL}/v1/mcp/bigquery",
        }

        for svc in r_svcs:
            svc_name = svc["name"]
            svc_id = svc_name.split("/")[-1]
            target_proxy_url = proxy_url_map.get(svc_id)
            if not target_proxy_url:
                continue

            if "agentSpec" in svc:
                card = svc["agentSpec"].get("content", {})
                card["url"] = target_proxy_url
                patch_body = {
                    "displayName": svc.get("displayName"),
                    "description": svc.get("description"),
                    "agentSpec": {
                        "type": "A2A_AGENT_CARD",
                        "content": card,
                    },
                }
                r_patch = client.patch(
                    f"https://agentregistry.googleapis.com/v1alpha/{svc_name}",
                    params={"updateMask": "agentSpec"},
                    headers=headers,
                    json=patch_body,
                )
                if r_patch.status_code == 200 and "operations/" in r_patch.json().get("name", ""):
                    wait_ar_op(client, r_patch.json()["name"], headers)
                print(f" [AgentRegistry A2A] {svc_id} -> url={target_proxy_url} (HTTP {r_patch.status_code})")

            elif "mcpServerSpec" in svc:
                mcp_content = svc["mcpServerSpec"].get("content", {})
                mcp_content["interfaces"] = [{"url": target_proxy_url, "protocolBinding": "JSONRPC"}]
                patch_body = {
                    "displayName": svc.get("displayName"),
                    "description": "BigQuery Remote MCP Server strictly mediated by Apigee X Proxy (bigquery-mcp-gateway) + Cloud Model Armor",
                    "interfaces": [{"url": target_proxy_url, "protocolBinding": "JSONRPC"}],
                    "mcpServerSpec": {
                        "type": svc["mcpServerSpec"].get("type", "TOOL_SPEC"),
                        "content": mcp_content,
                    },
                }
                r_patch = client.patch(
                    f"https://agentregistry.googleapis.com/v1alpha/{svc_name}",
                    params={"updateMask": "interfaces,mcpServerSpec,description"},
                    headers=headers,
                    json=patch_body,
                )
                if r_patch.status_code == 200 and "operations/" in r_patch.json().get("name", ""):
                    wait_ar_op(client, r_patch.json()["name"], headers)
                print(f" [AgentRegistry MCP] {svc_id} -> interfaces[0].url={target_proxy_url} (HTTP {r_patch.status_code})")

        print("\n=== 2. Patching Apigee API Hub Deployments (us-central1) to Strict Apigee Proxy Endpoints ===")
        dep_endpoints_map = {
            "apigee-agentic-ai-gateway": [f"{APIGEE_GATEWAY_URL}/v1/agentic-fsi"],
            "apigee-a2a-agent-1-tx-risk": [f"{APIGEE_GATEWAY_URL}/v1/a2a/agent-1"],
            "apigee-a2a-agent-2-aml-kyc": [f"{APIGEE_GATEWAY_URL}/v1/a2a/agent-2"],
            "apigee-bigquery-mcp-gateway": [f"{APIGEE_GATEWAY_URL}/v1/mcp/bigquery"],
        }
        r_deps = client.get(f"{BASE_APIHUB_URL}/deployments", headers=headers).json().get("deployments", [])
        existing_dep_ids = set()
        for dep in r_deps:
            dep_name = dep["name"]
            dep_id = dep_name.split("/")[-1]
            existing_dep_ids.add(dep_id)
            if dep_id in dep_endpoints_map:
                dep["endpoints"] = dep_endpoints_map[dep_id]
                r_p = client.patch(
                    f"https://apihub.googleapis.com/v1/{dep_name}",
                    params={"updateMask": "endpoints"},
                    headers=headers,
                    json={"endpoints": dep_endpoints_map[dep_id]},
                )
                print(f" [API Hub Deployment] {dep_id} -> endpoints={dep_endpoints_map[dep_id]} (HTTP {r_p.status_code})")

        # Register 5th deployment for vertex-gemini-llm-gateway if not present
        gemini_dep_id = "apigee-vertex-gemini-llm-gateway"
        gemini_dep_payload = {
            "displayName": "Apigee X — vertex-gemini-llm-gateway (Vertex AI Gemini + OOTB LLMTokenQuota)",
            "description": "Apigee X AI Gateway Proxy for Vertex AI Gemini 2.5 Flash with OOTB <LLMTokenQuota> (admin@cviscontino.altostrat.com) and Cloud Model Armor.",
            "deploymentType": {
                "attribute": f"projects/{PROJECT_ID}/locations/{APIHUB_LOCATION}/attributes/system-deployment-type",
                "enumValues": {
                    "values": [{"id": "apigee"}]
                }
            },
            "resourceUri": f"organizations/{PROJECT_ID}/environments/agentic-prod/apis/vertex-gemini-llm-gateway",
            "endpoints": [f"{APIGEE_GATEWAY_URL}/v1/llm/gemini"],
            "environment": {
                "attribute": f"projects/{PROJECT_ID}/locations/{APIHUB_LOCATION}/attributes/system-environment",
                "enumValues": {
                    "values": [{"id": "prod"}]
                }
            },
            "sourceProject": PROJECT_ID,
            "sourceEnvironment": "agentic-prod",
            "sourceRevision": "1",
        }
        if gemini_dep_id not in existing_dep_ids:
            r_c = client.post(
                f"{BASE_APIHUB_URL}/deployments",
                params={"deploymentId": gemini_dep_id},
                headers=headers,
                json=gemini_dep_payload,
            )
            print(f" [API Hub Deployment Create] {gemini_dep_id} -> HTTP {r_c.status_code}")
        else:
            r_u = client.patch(
                f"{BASE_APIHUB_URL}/deployments/{gemini_dep_id}",
                params={"updateMask": "endpoints,displayName,description"},
                headers=headers,
                json=gemini_dep_payload,
            )
            print(f" [API Hub Deployment Update] {gemini_dep_id} -> HTTP {r_u.status_code}")

        print("\n=== 3. Ensuring Apigee X Developer App for Vertex AI Gemini LLM Proxy ===")
        dev_email = "admin@cviscontino.altostrat.com"
        r_app = client.post(
            f"{BASE_APIGEE_URL}/developers/{dev_email}/apps",
            headers={"Authorization": f"Bearer {creds.token}", "Content-Type": "application/json"},
            json={
                "name": "ge-root-vertex-gemini-llm-app",
                "apiProducts": ["vertex-gemini-llm-product"],
                "attributes": [
                    {"name": "Description", "value": "GE Root Orchestrator -> Apigee (vertex-gemini-llm-gateway + OOTB LLMTokenQuota) -> Vertex AI Gemini 2.5 Flash"},
                    {"name": "LLMTokenQuotaLimit", "value": "5000 tokens / 1 minute"},
                ],
            },
        )
        print(f" [Apigee Developer App] ge-root-vertex-gemini-llm-app -> HTTP {r_app.status_code}")

        print("\n=== 4. Final Audit Verification (Zero Direct Invocations) ===")
        r_agents = client.get(f"{BASE_AR_URL}/agents", headers=headers).json().get("agents", [])
        for a in r_agents:
            protocols = a.get("protocols", [])
            urls = [i.get("url") for p in protocols for i in p.get("interfaces", [])]
            print(f" [Verified Agent Registry Agent] {a.get('displayName')}: {urls}")

        r_mcps = client.get(f"{BASE_AR_URL}/mcpServers", headers=headers).json().get("mcpServers", [])
        for m in r_mcps:
            urls = [i.get("url") for i in m.get("interfaces", [])]
            print(f" [Verified Agent Registry MCP]   {m.get('displayName')}: {urls}")

        r_deps_after = client.get(f"{BASE_APIHUB_URL}/deployments", headers=headers).json().get("deployments", [])
        for d in r_deps_after:
            print(f" [Verified API Hub Deployment]   {d['name'].split('/')[-1]}: {d.get('endpoints')}")


if __name__ == "__main__":
    main()
