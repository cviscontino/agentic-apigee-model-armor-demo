#!/usr/bin/env python3
"""
Register A2A Agents, MCP Servers/Tools, REST Gateway, and Apigee Deployments
in Apigee API Hub (projects/cvisco-agentic-demo/locations/us-central1) so they
appear under Apigee -> APIs (APIs, Agents, MCP Servers, MCP Tools) in the GCP Console.
"""
import base64
import json
import subprocess
import httpx

PROJECT_ID = "cvisco-agentic-demo"
APIHUB_LOCATION = "us-central1"
BASE_URL = f"https://apihub.googleapis.com/v1/projects/{PROJECT_ID}/locations/{APIHUB_LOCATION}"
CLOUD_RUN_URL = "https://agentic-fsi-demo-1070899805958.europe-west1.run.app"


def get_adc_token() -> str:
    return subprocess.check_output(
        ["gcloud", "auth", "application-default", "print-access-token"]
    ).decode().strip()


def enum_attr(val_id: str) -> dict:
    return {"enumValues": {"values": [{"id": val_id}]}}


def b64_json(obj: dict) -> str:
    return base64.b64encode(json.dumps(obj, indent=2).encode("utf-8")).decode("utf-8")


def main() -> None:
    token = get_adc_token()
    headers = {
        "Authorization": f"Bearer {token}",
        "x-goog-user-project": PROJECT_ID,
    }
    with httpx.Client(headers=headers, timeout=30.0) as client:
        r_apis = client.get(f"{BASE_URL}/apis")
        r_deps = client.get(f"{BASE_URL}/deployments")
        r_mcp_srv = client.get(f"{BASE_URL}:retrieveApiViews?view=MCP_SERVER")
        r_mcp_tools = client.get(f"{BASE_URL}:retrieveApiViews?view=MCP_TOOL")

        print("=== Apigee API Hub Summary (us-central1) ===")
        for api in r_apis.json().get("apis", []):
            api_id = api["name"].split("/")[-1]
            style = api.get("apiStyle", {}).get("enumValues", {}).get("values", [{}])[0].get("id")
            svc_type = api.get("serviceType", {}).get("enumValues", {}).get("values", [{}])[0].get("id")
            print(f" - API: {api_id:30s} | style={style:8s} | serviceType={svc_type}")
        print(f"Total Deployments: {len(r_deps.json().get('deployments', []))}")
        print(f"Total MCP Servers (MCP_SERVER view): {len(r_mcp_srv.json().get('apiViews', []))}")
        print(f"Total MCP Tools   (MCP_TOOL view):   {len(r_mcp_tools.json().get('apiViews', []))}")


if __name__ == "__main__":
    main()
