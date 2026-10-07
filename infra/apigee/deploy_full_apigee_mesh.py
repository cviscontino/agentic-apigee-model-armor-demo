import os
import zipfile
import httpx
import google.auth
import google.auth.transport.requests

ORG = "cvisco-agentic-demo"
BASE_URL = f"https://apigee.googleapis.com/v1/organizations/{ORG}"
SA_EMAIL = f"apigee-model-armor-sa@{ORG}.iam.gserviceaccount.com"
APIGEE_ROOT = "/Users/cviscontino/jetski_projects/agentic-apigee-model-armor-demo/infra/apigee"
CLOUD_RUN_URL = "https://agentic-fsi-demo-1070899805958.europe-west1.run.app"
ARMOR_TPL_URL = "https://modelarmor.europe-west1.rep.googleapis.com/v1/projects/cvisco-agentic-demo/locations/europe-west1/templates/fsi-agent-armor-strict"


def create_a2a_agent_proxy_bundle(proxy_name: str, display_name: str, base_path: str, target_url: str, agent_id: str) -> str:
    proxy_dir = os.path.join(APIGEE_ROOT, proxy_name)
    apiproxy_dir = os.path.join(proxy_dir, "apiproxy")
    os.makedirs(os.path.join(apiproxy_dir, "proxies"), exist_ok=True)
    os.makedirs(os.path.join(apiproxy_dir, "targets"), exist_ok=True)
    os.makedirs(os.path.join(apiproxy_dir, "policies"), exist_ok=True)

    with open(os.path.join(apiproxy_dir, f"{proxy_name}.xml"), "w") as f:
        f.write(f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<APIProxy revision="1" name="{proxy_name}">
    <DisplayName>{display_name}</DisplayName>
    <Description>Apigee X + Cloud Model Armor Mediated A2A Sub-Agent Proxy for {agent_id} ({base_path})</Description>
    <BasePaths>{base_path}</BasePaths>
    <Policies>
        <Policy>SA-A2A-SpikeArrest</Policy>
        <Policy>EV-ExtractA2ATaskPayload</Policy>
        <Policy>SC-ModelArmor-SanitizeA2AInput</Policy>
        <Policy>EV-ExtractArmorVerdict</Policy>
        <Policy>RF-ModelArmorBlockedA2A</Policy>
        <Policy>SC-ModelArmor-SanitizeA2AOutput</Policy>
        <Policy>AM-InjectA2AGovernanceHeaders</Policy>
    </Policies>
    <ProxyEndpoints>
        <ProxyEndpoint>default</ProxyEndpoint>
    </ProxyEndpoints>
    <TargetEndpoints>
        <TargetEndpoint>a2a-subagent-target</TargetEndpoint>
    </TargetEndpoints>
</APIProxy>
""")

    with open(os.path.join(apiproxy_dir, "proxies", "default.xml"), "w") as f:
        f.write(f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<ProxyEndpoint name="default">
    <Description>Apigee X + Model Armor Mediated A2A Endpoint for {agent_id}</Description>
    <PreFlow name="PreFlow">
        <Request>
            <Step>
                <Name>SA-A2A-SpikeArrest</Name>
            </Step>
            <Step>
                <Name>EV-ExtractA2ATaskPayload</Name>
                <Condition>request.verb = "POST"</Condition>
            </Step>
            <Step>
                <Name>SC-ModelArmor-SanitizeA2AInput</Name>
                <Condition>request.verb = "POST"</Condition>
            </Step>
            <Step>
                <Name>EV-ExtractArmorVerdict</Name>
                <Condition>request.verb = "POST"</Condition>
            </Step>
            <Step>
                <Name>RF-ModelArmorBlockedA2A</Name>
                <Condition>(request.verb = "POST") and (modelarmor.filterMatchState = "MATCH_FOUND")</Condition>
            </Step>
        </Request>
        <Response/>
    </PreFlow>
    <PostFlow name="PostFlow">
        <Request/>
        <Response>
            <Step>
                <Name>SC-ModelArmor-SanitizeA2AOutput</Name>
                <Condition>request.verb = "POST"</Condition>
            </Step>
            <Step>
                <Name>AM-InjectA2AGovernanceHeaders</Name>
            </Step>
        </Response>
    </PostFlow>
    <HTTPProxyConnection>
        <BasePath>{base_path}</BasePath>
    </HTTPProxyConnection>
    <RouteRule name="route-to-a2a-subagent"/>
</ProxyEndpoint>
""")

    with open(os.path.join(apiproxy_dir, "targets", "a2a-subagent-target.xml"), "w") as f:
        f.write(f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<TargetEndpoint name="a2a-subagent-target">
    <Description>Cloud Run A2A Sub-Agent Target ({agent_id})</Description>
    <PreFlow name="PreFlow">
        <Request/>
        <Response/>
    </PreFlow>
    <HTTPTargetConnection>
        <URL>{target_url}</URL>
    </HTTPTargetConnection>
</TargetEndpoint>
""")

    policies = {
        "SA-A2A-SpikeArrest.xml": """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<SpikeArrest async="false" continueOnError="false" enabled="true" name="SA-A2A-SpikeArrest">
    <DisplayName>SA-A2A-SpikeArrest</DisplayName>
    <Rate>60pm</Rate>
    <UseEffectiveCount>true</UseEffectiveCount>
</SpikeArrest>
""",
        "EV-ExtractA2ATaskPayload.xml": """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<ExtractVariables async="false" continueOnError="true" enabled="true" name="EV-ExtractA2ATaskPayload">
    <DisplayName>EV-ExtractA2ATaskPayload</DisplayName>
    <Source clearPayload="false">request</Source>
    <JSONPayload>
        <Variable name="a2a.taskText">
            <JSONPath>$.params.message.parts[0].text</JSONPath>
        </Variable>
    </JSONPayload>
</ExtractVariables>
""",
        "SC-ModelArmor-SanitizeA2AInput.xml": f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<ServiceCallout async="false" continueOnError="false" enabled="true" name="SC-ModelArmor-SanitizeA2AInput">
    <DisplayName>SC-ModelArmor-SanitizeA2AInput</DisplayName>
    <Request clearPayload="true" variable="armorA2AInputReq">
        <Set>
            <Headers>
                <Header name="Content-Type">application/json</Header>
            </Headers>
            <Payload contentType="application/json">{{
  "userPromptData": {{
    "text": "{{a2a.taskText}}"
  }}
}}</Payload>
            <Verb>POST</Verb>
        </Set>
        <IgnoreUnresolvedVariables>true</IgnoreUnresolvedVariables>
    </Request>
    <Response>armorA2AInputResp</Response>
    <HTTPTargetConnection>
        <URL>{ARMOR_TPL_URL}:sanitizeUserPrompt</URL>
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
        "EV-ExtractArmorVerdict.xml": """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<ExtractVariables async="false" continueOnError="true" enabled="true" name="EV-ExtractArmorVerdict">
    <DisplayName>EV-ExtractArmorVerdict</DisplayName>
    <Source clearPayload="false">armorA2AInputResp</Source>
    <JSONPayload>
        <Variable name="modelarmor.filterMatchState">
            <JSONPath>$.sanitizationResult.filterMatchState</JSONPath>
        </Variable>
    </JSONPayload>
</ExtractVariables>
""",
        "RF-ModelArmorBlockedA2A.xml": f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<RaiseFault async="false" continueOnError="false" enabled="true" name="RF-ModelArmorBlockedA2A">
    <DisplayName>RF-ModelArmorBlockedA2A</DisplayName>
    <FaultResponse>
        <Set>
            <StatusCode>403</StatusCode>
            <ReasonPhrase>Blocked by Apigee + Cloud Model Armor on A2A Hop</ReasonPhrase>
            <Payload contentType="application/json">{{
  "jsonrpc": "2.0",
  "error": {{
    "code": -32001,
    "message": "A2A task to {agent_id} blocked by Cloud Model Armor (fsi-agent-armor-strict)",
    "data": {{
      "verdict": "{{modelarmor.filterMatchState}}",
      "proxy": "{proxy_name}"
    }}
  }}
}}</Payload>
        </Set>
    </FaultResponse>
    <IgnoreUnresolvedVariables>true</IgnoreUnresolvedVariables>
</RaiseFault>
""",
        "SC-ModelArmor-SanitizeA2AOutput.xml": f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<ServiceCallout async="false" continueOnError="true" enabled="true" name="SC-ModelArmor-SanitizeA2AOutput">
    <DisplayName>SC-ModelArmor-SanitizeA2AOutput</DisplayName>
    <Request clearPayload="true" variable="armorA2AOutputReq">
        <Set>
            <Headers>
                <Header name="Content-Type">application/json</Header>
            </Headers>
            <Payload contentType="application/json">{{
  "modelResponseData": {{
    "text": "A2A Artifact Output Inspection"
  }}
}}</Payload>
            <Verb>POST</Verb>
        </Set>
        <IgnoreUnresolvedVariables>true</IgnoreUnresolvedVariables>
    </Request>
    <Response>armorA2AOutputResp</Response>
    <HTTPTargetConnection>
        <URL>{ARMOR_TPL_URL}:sanitizeModelResponse</URL>
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
        "AM-InjectA2AGovernanceHeaders.xml": f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<AssignMessage async="false" continueOnError="false" enabled="true" name="AM-InjectA2AGovernanceHeaders">
    <DisplayName>AM-InjectA2AGovernanceHeaders</DisplayName>
    <Set>
        <Headers>
            <Header name="Content-Type">application/json</Header>
            <Header name="X-Apigee-A2A-Proxy">{proxy_name}</Header>
            <Header name="X-Apigee-A2A-Target">{agent_id}</Header>
            <Header name="X-Model-Armor-A2A-Verdict">{{modelarmor.filterMatchState}}</Header>
        </Headers>
        <Payload contentType="application/json">{{
  "jsonrpc": "2.0",
  "id": "a2a-mediated",
  "result": {{
    "status": "APIGEE_A2A_MODEL_ARMOR_APPROVED",
    "proxy": "{proxy_name}",
    "targetAgent": "{agent_id}",
    "modelArmorVerdict": "{{modelarmor.filterMatchState}}"
  }}
}}</Payload>
        <StatusCode>200</StatusCode>
    </Set>
    <IgnoreUnresolvedVariables>true</IgnoreUnresolvedVariables>
</AssignMessage>
""",
    }
    for fname, content in policies.items():
        with open(os.path.join(apiproxy_dir, "policies", fname), "w") as f:
            f.write(content)

    zip_path = os.path.join(APIGEE_ROOT, f"{proxy_name}.zip")
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for root, _, files in os.walk(apiproxy_dir):
            for file in files:
                if file.endswith(".xml"):
                    full_path = os.path.join(root, file)
                    rel_path = os.path.relpath(full_path, proxy_dir)
                    zf.write(full_path, rel_path)
    return zip_path


def main():
    z1 = create_a2a_agent_proxy_bundle(
        proxy_name="a2a-agent-1-tx-risk",
        display_name="A2A Agent 1 — Transaction &amp; Risk Analytics (Apigee + Model Armor)",
        base_path="/v1/a2a/agent-1",
        target_url=f"{CLOUD_RUN_URL}/api/a2a/agent-1",
        agent_id="agent-1-tx-risk-analytics",
    )
    z2 = create_a2a_agent_proxy_bundle(
        proxy_name="a2a-agent-2-aml-kyc",
        display_name="A2A Agent 2 — Compliance &amp; AML/KYC Portfolio (Apigee + Model Armor)",
        base_path="/v1/a2a/agent-2",
        target_url=f"{CLOUD_RUN_URL}/api/a2a/agent-2",
        agent_id="agent-2-compliance-aml-kyc",
    )

    creds, _ = google.auth.default(scopes=["https://www.googleapis.com/auth/cloud-platform"])
    creds.refresh(google.auth.transport.requests.Request())
    headers = {"Authorization": f"Bearer {creds.token}"}

    with httpx.Client(timeout=60.0) as client:
        for proxy_name, zip_path in [
            ("a2a-agent-1-tx-risk", z1),
            ("a2a-agent-2-aml-kyc", z2),
        ]:
            print(f"\n--- Importing & Deploying {proxy_name} ---")
            with open(zip_path, "rb") as f:
                r_imp = client.post(
                    f"{BASE_URL}/apis",
                    params={"name": proxy_name, "action": "import"},
                    headers=headers,
                    files={"file": (os.path.basename(zip_path), f, "application/zip")},
                )
            print("Import:", r_imp.status_code, r_imp.text if r_imp.status_code != 200 else "")
            rev = r_imp.json().get("revision", "1") if r_imp.status_code == 200 else "1"
            r_dep = client.post(
                f"{BASE_URL}/environments/agentic-prod/apis/{proxy_name}/revisions/{rev}/deployments",
                params={"override": "true", "serviceAccount": SA_EMAIL},
                headers=headers,
            )
            print("Deploy:", r_dep.status_code, r_dep.text)

        # Now register API Products, Developer, and Developer Apps in Apigee X!
        print("\n--- Registering API Products in Apigee X ---")
        products = [
            {
                "name": "ge-multiagent-northbound-product",
                "displayName": "1. Gemini Enterprise Root Multi-Agent Product (Northbound)",
                "description": "Mediates Client calls to Gemini Enterprise Root Orchestrator via agentic-ai-gateway + Cloud Model Armor",
                "approvalType": "auto",
                "environments": ["agentic-prod"],
                "proxies": ["agentic-ai-gateway"],
                "apiResources": ["/", "/**"],
                "quota": "50000",
                "quotaInterval": "1",
                "quotaTimeUnit": "hour",
            },
            {
                "name": "a2a-subagents-mesh-product",
                "displayName": "2. A2A Sub-Agents Mesh Product (Agent 1 Tx Risk & Agent 2 AML/KYC)",
                "description": "Mediates East-West A2A JSON-RPC calls from Gemini Enterprise Root Orchestrator to Agent 1 and Agent 2 via Apigee + Cloud Model Armor",
                "approvalType": "auto",
                "environments": ["agentic-prod"],
                "proxies": ["a2a-agent-1-tx-risk", "a2a-agent-2-aml-kyc"],
                "apiResources": ["/", "/**"],
                "quota": "100000",
                "quotaInterval": "1",
                "quotaTimeUnit": "hour",
            },
            {
                "name": "bigquery-mcp-server-product",
                "displayName": "3. BigQuery MCP Server Product (Southbound Read-Only SQL)",
                "description": "Mediates Southbound MCP JSON-RPC 2.0 calls from A2A Sub-Agents to BigQuery Remote MCP Server via Apigee + Cloud Model Armor",
                "approvalType": "auto",
                "environments": ["agentic-prod"],
                "proxies": ["bigquery-mcp-gateway"],
                "apiResources": ["/", "/**"],
                "quota": "100000",
                "quotaInterval": "1",
                "quotaTimeUnit": "hour",
            },
        ]
        for p in products:
            r_p = client.post(f"{BASE_URL}/apiproducts", headers=headers, json=p)
            if r_p.status_code == 409:
                r_p = client.put(f"{BASE_URL}/apiproducts/{p['name']}", headers=headers, json=p)
            print(f"API Product {p['name']}:", r_p.status_code, r_p.text[:250])

        print("\n--- Registering Developer & 3 Agentic Apps in Apigee X ---")
        dev_email = "admin@cviscontino.altostrat.com"
        r_dev = client.post(
            f"{BASE_URL}/developers",
            headers=headers,
            json={
                "email": dev_email,
                "firstName": "Cristina",
                "lastName": "Viscontino",
                "userName": "cviscontino-ce",
            },
        )
        print("Developer:", r_dev.status_code)

        apps = [
            ("agentic-cockpit-client-app", ["ge-multiagent-northbound-product"], "Northbound Client App -> Apigee -> GE Root Agent"),
            ("ge-root-orchestrator-a2a-app", ["a2a-subagents-mesh-product"], "GE Root Orchestrator -> Apigee + Model Armor -> A2A Agent 1 & Agent 2"),
            ("a2a-subagents-bq-mcp-app", ["bigquery-mcp-server-product"], "A2A Sub-Agents 1 & 2 -> Apigee + Model Armor -> BigQuery MCP Server"),
        ]
        for app_name, prods, desc in apps:
            r_app = client.post(
                f"{BASE_URL}/developers/{dev_email}/apps",
                headers=headers,
                json={
                    "name": app_name,
                    "apiProducts": prods,
                    "attributes": [
                        {"name": "Description", "value": desc},
                        {"name": "ModelArmorTemplate", "value": "projects/cvisco-agentic-demo/locations/europe-west1/templates/fsi-agent-armor-strict"},
                    ],
                },
            )
            print(f"App {app_name}:", r_app.status_code, r_app.text[:250])


if __name__ == "__main__":
    main()
