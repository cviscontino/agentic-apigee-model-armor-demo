import os
import zipfile
import httpx
import google.auth
import google.auth.transport.requests

ORG = "cvisco-agentic-demo"
BASE_URL = f"https://apigee.googleapis.com/v1/organizations/{ORG}"
SA_EMAIL = f"apigee-model-armor-sa@{ORG}.iam.gserviceaccount.com"
APIGEE_ROOT = "/Users/cviscontino/jetski_projects/agentic-apigee-model-armor-demo/infra/apigee"


def write_mcp_policies():
    pol_dir = os.path.join(APIGEE_ROOT, "mcp-proxy", "apiproxy", "policies")
    os.makedirs(pol_dir, exist_ok=True)

    policies = {
        "SA-MCP-RateLimit.xml": """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<SpikeArrest async="false" continueOnError="false" enabled="true" name="SA-MCP-RateLimit">
    <DisplayName>SA-MCP-RateLimit</DisplayName>
    <Rate>60pm</Rate>
    <UseEffectiveCount>true</UseEffectiveCount>
</SpikeArrest>
""",
        "EV-ExtractMCPMethodAndTool.xml": """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<ExtractVariables async="false" continueOnError="true" enabled="true" name="EV-ExtractMCPMethodAndTool">
    <DisplayName>EV-ExtractMCPMethodAndTool</DisplayName>
    <Source clearPayload="false">request</Source>
    <JSONPayload>
        <Variable name="mcp.method">
            <JSONPath>$.method</JSONPath>
        </Variable>
        <Variable name="mcp.toolName">
            <JSONPath>$.params.name</JSONPath>
        </Variable>
        <Variable name="mcp.sqlQuery">
            <JSONPath>$.params.arguments.query</JSONPath>
        </Variable>
    </JSONPayload>
</ExtractVariables>
""",
        "RF-BlockMutatingMCPTool.xml": """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<RaiseFault async="false" continueOnError="false" enabled="true" name="RF-BlockMutatingMCPTool">
    <DisplayName>RF-BlockMutatingMCPTool</DisplayName>
    <FaultResponse>
        <Set>
            <StatusCode>403</StatusCode>
            <ReasonPhrase>Forbidden by Apigee MCP Tool Governance</ReasonPhrase>
            <Payload contentType="application/json">{
  "jsonrpc": "2.0",
  "error": {
    "code": -32600,
    "message": "Blocked by Apigee X MCP Gateway: Only read-only BigQuery MCP tools (execute_sql_readonly, get_table_info, list_table_ids, list_dataset_ids) are permitted for A2A Sub-Agents.",
    "data": {
      "attempted_tool": "{mcp.toolName}",
      "policy": "RF-BlockMutatingMCPTool"
    }
  }
}</Payload>
        </Set>
    </FaultResponse>
    <IgnoreUnresolvedVariables>true</IgnoreUnresolvedVariables>
</RaiseFault>
""",
        "SC-ModelArmor-InspectSQL.xml": """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<ServiceCallout async="false" continueOnError="false" enabled="true" name="SC-ModelArmor-InspectSQL">
    <DisplayName>SC-ModelArmor-InspectSQL</DisplayName>
    <Request clearPayload="true" variable="modelArmorSqlReq">
        <Set>
            <Headers>
                <Header name="Content-Type">application/json</Header>
            </Headers>
            <Payload contentType="application/json">{
  "userPromptData": {
    "text": "{mcp.sqlQuery}"
  }
}</Payload>
            <Verb>POST</Verb>
        </Set>
        <IgnoreUnresolvedVariables>true</IgnoreUnresolvedVariables>
    </Request>
    <Response>modelArmorSqlResp</Response>
    <HTTPTargetConnection>
        <URL>https://modelarmor.europe-west1.rep.googleapis.com/v1/projects/cvisco-agentic-demo/locations/europe-west1/templates/fsi-agent-armor-strict:sanitizeUserPrompt</URL>
        <Authentication>
            <GoogleAccessToken>
                <Scopes>
                    <Scope>https://www.googleapis.com/auth/cloud-platform</Scope>
                </Scopes>
            </GoogleAccessToken>
        </Authentication>
    </HTTPTargetConnection>
</ServiceCallout>
""",
        "AM-SetBigQueryMCPHeaders.xml": """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<AssignMessage async="false" continueOnError="false" enabled="true" name="AM-SetBigQueryMCPHeaders">
    <DisplayName>AM-SetBigQueryMCPHeaders</DisplayName>
    <Set>
        <Headers>
            <Header name="x-goog-user-project">cvisco-agentic-demo</Header>
            <Header name="X-Apigee-MCP-Server">bigquery.googleapis.com/mcp</Header>
            <Header name="X-Apigee-MCP-Tool">{mcp.toolName}</Header>
        </Headers>
    </Set>
    <IgnoreUnresolvedVariables>true</IgnoreUnresolvedVariables>
</AssignMessage>
""",
    }
    for fname, content in policies.items():
        with open(os.path.join(pol_dir, fname), "w") as f:
            f.write(content)


def write_a2a_proxy():
    a2a_root = os.path.join(APIGEE_ROOT, "a2a-proxy", "apiproxy")
    os.makedirs(os.path.join(a2a_root, "proxies"), exist_ok=True)
    os.makedirs(os.path.join(a2a_root, "targets"), exist_ok=True)
    os.makedirs(os.path.join(a2a_root, "policies"), exist_ok=True)

    with open(os.path.join(a2a_root, "a2a-subagents-gateway.xml"), "w") as f:
        f.write("""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<APIProxy revision="1" name="a2a-subagents-gateway">
    <DisplayName>A2A Sub-Agents Mesh Gateway (Agent 1 Tx Risk &amp; Agent 2 AML/KYC)</DisplayName>
    <Description>Apigee X East-West A2A Protocol Gateway mediating Agent Card discovery (/.well-known/agent.json) and JSON-RPC task execution (tasks/send) between Gemini Enterprise Root Orchestrator and the 2 specialized FSI Sub-Agents.</Description>
    <BasePaths>/v1/a2a</BasePaths>
    <Policies>
        <Policy>SA-A2A-Mesh-RateLimit</Policy>
        <Policy>AM-InjectA2ATraceHeaders</Policy>
    </Policies>
    <ProxyEndpoints>
        <ProxyEndpoint>default</ProxyEndpoint>
    </ProxyEndpoints>
    <TargetEndpoints>
        <TargetEndpoint>a2a-subagents-cloudrun</TargetEndpoint>
    </TargetEndpoints>
</APIProxy>
""")

    with open(os.path.join(a2a_root, "proxies", "default.xml"), "w") as f:
        f.write("""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<ProxyEndpoint name="default">
    <Description>A2A Protocol Proxy Endpoint for Agent 1 and Agent 2</Description>
    <PreFlow name="PreFlow">
        <Request>
            <Step>
                <Name>SA-A2A-Mesh-RateLimit</Name>
            </Step>
            <Step>
                <Name>AM-InjectA2ATraceHeaders</Name>
            </Step>
        </Request>
        <Response/>
    </PreFlow>
    <HTTPProxyConnection>
        <BasePath>/v1/a2a</BasePath>
    </HTTPProxyConnection>
    <RouteRule name="route-to-a2a-subagents">
        <TargetEndpoint>a2a-subagents-cloudrun</TargetEndpoint>
    </RouteRule>
</ProxyEndpoint>
""")

    with open(os.path.join(a2a_root, "targets", "a2a-subagents-cloudrun.xml"), "w") as f:
        f.write("""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<TargetEndpoint name="a2a-subagents-cloudrun">
    <Description>Cloud Run A2A Sub-Agents Endpoint (Agent 1: Transaction &amp; Risk, Agent 2: Compliance &amp; AML)</Description>
    <PreFlow name="PreFlow">
        <Request/>
        <Response/>
    </PreFlow>
    <HTTPTargetConnection>
        <URL>https://agentic-fsi-demo-1070899805958.europe-west1.run.app/api/a2a</URL>
    </HTTPTargetConnection>
</TargetEndpoint>
""")

    with open(os.path.join(a2a_root, "policies", "SA-A2A-Mesh-RateLimit.xml"), "w") as f:
        f.write("""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<SpikeArrest async="false" continueOnError="false" enabled="true" name="SA-A2A-Mesh-RateLimit">
    <DisplayName>SA-A2A-Mesh-RateLimit</DisplayName>
    <Rate>60pm</Rate>
    <UseEffectiveCount>true</UseEffectiveCount>
</SpikeArrest>
""")

    with open(os.path.join(a2a_root, "policies", "AM-InjectA2ATraceHeaders.xml"), "w") as f:
        f.write("""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<AssignMessage async="false" continueOnError="false" enabled="true" name="AM-InjectA2ATraceHeaders">
    <DisplayName>AM-InjectA2ATraceHeaders</DisplayName>
    <Set>
        <Headers>
            <Header name="X-A2A-Protocol-Version">0.3.0</Header>
            <Header name="X-Apigee-A2A-Mesh">cvisco-agentic-demo</Header>
        </Headers>
    </Set>
    <IgnoreUnresolvedVariables>true</IgnoreUnresolvedVariables>
</AssignMessage>
""")


def zip_proxy(folder_path: str, zip_path: str):
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        apiproxy_root = os.path.join(folder_path, "apiproxy")
        for root, _, files in os.walk(apiproxy_root):
            for file in files:
                if file.endswith(".xml"):
                    full_path = os.path.join(root, file)
                    rel_path = os.path.relpath(full_path, folder_path)
                    zf.write(full_path, rel_path)


def main():
    write_mcp_policies()
    write_a2a_proxy()

    mcp_zip = os.path.join(APIGEE_ROOT, "bigquery-mcp-gateway.zip")
    a2a_zip = os.path.join(APIGEE_ROOT, "a2a-subagents-gateway.zip")
    zip_proxy(os.path.join(APIGEE_ROOT, "mcp-proxy"), mcp_zip)
    zip_proxy(os.path.join(APIGEE_ROOT, "a2a-proxy"), a2a_zip)

    creds, _ = google.auth.default(scopes=["https://www.googleapis.com/auth/cloud-platform"])
    creds.refresh(google.auth.transport.requests.Request())
    headers = {"Authorization": f"Bearer {creds.token}"}

    with httpx.Client(timeout=60.0) as client:
        for proxy_name, zip_path in [
            ("bigquery-mcp-gateway", mcp_zip),
            ("a2a-subagents-gateway", a2a_zip),
        ]:
            print(f"\n--- Importing {proxy_name} into Apigee X ---")
            with open(zip_path, "rb") as f:
                r_imp = client.post(
                    f"{BASE_URL}/apis",
                    params={"name": proxy_name, "action": "import"},
                    headers=headers,
                    files={"file": (os.path.basename(zip_path), f, "application/zip")},
                )
            print(f"Import {proxy_name}:", r_imp.status_code, r_imp.text[:400])
            rev = r_imp.json().get("revision", "1") if r_imp.status_code == 200 else "1"

            print(f"--- Deploying {proxy_name} rev {rev} to agentic-prod ---")
            r_dep = client.post(
                f"{BASE_URL}/environments/agentic-prod/apis/{proxy_name}/revisions/{rev}/deployments",
                params={"override": "true", "serviceAccount": SA_EMAIL},
                headers=headers,
            )
            print(f"Deploy {proxy_name}:", r_dep.status_code, r_dep.text)


if __name__ == "__main__":
    main()
