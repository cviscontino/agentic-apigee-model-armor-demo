import os
import zipfile
import httpx
import google.auth
import google.auth.transport.requests

ORG = "cvisco-agentic-demo"
BASE_URL = f"https://apigee.googleapis.com/v1/organizations/{ORG}"
SA_EMAIL = f"apigee-model-armor-sa@{ORG}.iam.gserviceaccount.com"
APIGEE_ROOT = "/Users/cviscontino/jetski_projects/agentic-apigee-model-armor-demo/infra/apigee"
GEMINI_TARGET_URL = (
    f"https://europe-west1-aiplatform.googleapis.com/v1/projects/{ORG}"
    "/locations/europe-west1/publishers/google/models/gemini-2.5-flash:generateContent"
)
ARMOR_TPL_URL = (
    f"https://modelarmor.europe-west1.rep.googleapis.com/v1/projects/{ORG}"
    "/locations/europe-west1/templates/fsi-agent-armor-strict"
)


def create_gemini_llm_proxy_bundle() -> str:
    proxy_name = "vertex-gemini-llm-gateway"
    proxy_dir = os.path.join(APIGEE_ROOT, proxy_name)
    apiproxy_dir = os.path.join(proxy_dir, "apiproxy")
    os.makedirs(os.path.join(apiproxy_dir, "proxies"), exist_ok=True)
    os.makedirs(os.path.join(apiproxy_dir, "targets"), exist_ok=True)
    os.makedirs(os.path.join(apiproxy_dir, "policies"), exist_ok=True)

    with open(os.path.join(apiproxy_dir, f"{proxy_name}.xml"), "w") as f:
        f.write(f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<APIProxy revision="1" name="{proxy_name}">
    <DisplayName>Vertex AI Gemini 2.5 LLM Proxy (OOTB LLMTokenQuota — admin@cviscontino.altostrat.com)</DisplayName>
    <Description>Apigee X AI Gateway Proxy to Vertex AI Gemini 2.5 Flash (:generateContent) with Out-of-the-Box LLMTokenQuota (EnforceOnly + CountOnly on $.usageMetadata.totalTokenCount) for admin@cviscontino.altostrat.com and Cloud Model Armor</Description>
    <BasePaths>/v1/llm/gemini</BasePaths>
    <Policies>
        <Policy>VA-VerifyApiKey</Policy>
        <Policy>EV-ExtractUserIdentity</Policy>
        <Policy>Q-TokenQuota-Enforce</Policy>
        <Policy>SC-ModelArmor-SanitizeInput</Policy>
        <Policy>Q-TokenQuota-Count</Policy>
        <Policy>AM-InjectGeminiQuotaHeaders</Policy>
    </Policies>
    <ProxyEndpoints>
        <ProxyEndpoint>default</ProxyEndpoint>
    </ProxyEndpoints>
    <TargetEndpoints>
        <TargetEndpoint>vertex-ai-gemini-target</TargetEndpoint>
    </TargetEndpoints>
</APIProxy>
""")

    with open(os.path.join(apiproxy_dir, "proxies", "default.xml"), "w") as f:
        f.write("""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<ProxyEndpoint name="default">
    <Description>Apigee X AI Proxy for Vertex AI Gemini with OOTB LLMTokenQuota for admin@cviscontino.altostrat.com</Description>
    <PreFlow name="PreFlow">
        <Request>
            <Step>
                <Name>VA-VerifyApiKey</Name>
            </Step>
            <Step>
                <Name>EV-ExtractUserIdentity</Name>
            </Step>
            <Step>
                <Name>Q-TokenQuota-Enforce</Name>
            </Step>
            <Step>
                <Name>SC-ModelArmor-SanitizeInput</Name>
            </Step>
        </Request>
        <Response>
            <Step>
                <Name>Q-TokenQuota-Count</Name>
            </Step>
            <Step>
                <Name>AM-InjectGeminiQuotaHeaders</Name>
            </Step>
        </Response>
    </PreFlow>
    <Flows/>
    <PostFlow name="PostFlow">
        <Request/>
        <Response/>
    </PostFlow>
    <HTTPProxyConnection>
        <BasePath>/v1/llm/gemini</BasePath>
    </HTTPProxyConnection>
    <RouteRule name="default">
        <TargetEndpoint>vertex-ai-gemini-target</TargetEndpoint>
    </RouteRule>
</ProxyEndpoint>
""")

    with open(os.path.join(apiproxy_dir, "targets", "vertex-ai-gemini-target.xml"), "w") as f:
        f.write(f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<TargetEndpoint name="vertex-ai-gemini-target">
    <Description>Vertex AI Gemini 2.5 Flash (:generateContent) in europe-west1</Description>
    <PreFlow name="PreFlow">
        <Request/>
        <Response/>
    </PreFlow>
    <HTTPTargetConnection>
        <URL>{GEMINI_TARGET_URL}</URL>
        <Authentication>
            <GoogleAccessToken>
                <Scopes>
                    <Scope>https://www.googleapis.com/auth/cloud-platform</Scope>
                </Scopes>
            </GoogleAccessToken>
        </Authentication>
    </HTTPTargetConnection>
</TargetEndpoint>
""")

    policies = {
        "VA-VerifyApiKey.xml": """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<VerifyAPIKey async="false" continueOnError="true" enabled="true" name="VA-VerifyApiKey">
    <DisplayName>VA-VerifyApiKey</DisplayName>
    <APIKey ref="request.header.x-api-key"/>
</VerifyAPIKey>
""",
        "EV-ExtractUserIdentity.xml": """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<ExtractVariables async="false" continueOnError="true" enabled="true" name="EV-ExtractUserIdentity">
    <DisplayName>EV-ExtractUserIdentity</DisplayName>
    <Source clearPayload="false">request</Source>
    <Header name="X-User-Email">
        <Pattern ignoreCase="true">{userEmail}</Pattern>
    </Header>
    <JSONPayload>
        <Variable name="userPrompt" type="string">
            <JSONPath>$.contents[0].parts[0].text</JSONPath>
        </Variable>
        <Variable name="userEmail" type="string">
            <JSONPath>$.user_email</JSONPath>
        </Variable>
    </JSONPayload>
    <VariablePrefix>extracted</VariablePrefix>
</ExtractVariables>
""",
        "Q-TokenQuota-Enforce.xml": """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<LLMTokenQuota async="false" continueOnError="false" enabled="true" name="Q-TokenQuota-Enforce" type="rollingwindow">
    <DisplayName>Q-TokenQuota-Enforce</DisplayName>
    <SharedName>user-gemini-token-counter</SharedName>
    <EnforceOnly>true</EnforceOnly>
    <UseQuotaConfigInAPIProduct stepName="VA-VerifyApiKey">
        <DefaultConfig>
            <Allow>1500</Allow>
            <Interval>1</Interval>
            <TimeUnit>minute</TimeUnit>
        </DefaultConfig>
    </UseQuotaConfigInAPIProduct>
    <Distributed>true</Distributed>
    <Synchronous>true</Synchronous>
    <Identifier ref="extracted.userEmail"/>
</LLMTokenQuota>
""",
        "Q-TokenQuota-Count.xml": """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<LLMTokenQuota async="false" continueOnError="false" enabled="true" name="Q-TokenQuota-Count" type="rollingwindow">
    <DisplayName>Q-TokenQuota-Count</DisplayName>
    <SharedName>user-gemini-token-counter</SharedName>
    <CountOnly>true</CountOnly>
    <UseQuotaConfigInAPIProduct stepName="VA-VerifyApiKey">
        <DefaultConfig>
            <Allow>1500</Allow>
            <Interval>1</Interval>
            <TimeUnit>minute</TimeUnit>
        </DefaultConfig>
    </UseQuotaConfigInAPIProduct>
    <Distributed>true</Distributed>
    <Synchronous>true</Synchronous>
    <Identifier ref="extracted.userEmail"/>
    <LLMTokenUsageSource>{jsonPath('$.usageMetadata.totalTokenCount',response.content,true)}</LLMTokenUsageSource>
    <LLMModelSource>{jsonPath('$.modelVersion',response.content,true)}</LLMModelSource>
</LLMTokenQuota>
""",
        "SC-ModelArmor-SanitizeInput.xml": f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<ServiceCallout async="false" continueOnError="true" enabled="true" name="SC-ModelArmor-SanitizeInput">
    <DisplayName>SC-ModelArmor-SanitizeInput</DisplayName>
    <Request clearPayload="true" variable="armorGeminiInputReq">
        <Set>
            <Headers>
                <Header name="Content-Type">application/json</Header>
            </Headers>
            <Payload contentType="application/json">{{
  "userPromptData": {{
    "text": "{{extracted.userPrompt}}"
  }}
}}</Payload>
            <Verb>POST</Verb>
        </Set>
        <IgnoreUnresolvedVariables>true</IgnoreUnresolvedVariables>
    </Request>
    <Response>armorGeminiInputResp</Response>
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
        "AM-InjectGeminiQuotaHeaders.xml": """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<AssignMessage async="false" continueOnError="false" enabled="true" name="AM-InjectGeminiQuotaHeaders">
    <DisplayName>AM-InjectGeminiQuotaHeaders</DisplayName>
    <Set>
        <Headers>
            <Header name="X-Apigee-Gateway">cvisco-agentic-demo-apigee-x</Header>
            <Header name="X-Apigee-Proxy">vertex-gemini-llm-gateway</Header>
            <Header name="X-Apigee-User-Identity">{extracted.userEmail}</Header>
            <Header name="X-Apigee-LLMTokenQuota-Allowed">{ratelimit.Q-TokenQuota-Count.allowed.count}</Header>
            <Header name="X-Apigee-LLMTokenQuota-Used">{ratelimit.Q-TokenQuota-Count.used.count}</Header>
            <Header name="X-Apigee-LLMTokenQuota-Available">{ratelimit.Q-TokenQuota-Count.available.count}</Header>
        </Headers>
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
    zip_path = create_gemini_llm_proxy_bundle()
    creds, _ = google.auth.default(scopes=["https://www.googleapis.com/auth/cloud-platform"])
    creds.refresh(google.auth.transport.requests.Request())
    headers = {"Authorization": f"Bearer {creds.token}"}

    proxy_name = "vertex-gemini-llm-gateway"
    with httpx.Client(timeout=60.0) as client:
        print(f"--- 1. Importing {proxy_name} to Apigee X ({ORG}) ---")
        with open(zip_path, "rb") as f:
            r_imp = client.post(
                f"{BASE_URL}/apis",
                params={"name": proxy_name, "action": "import"},
                headers=headers,
                files={"file": (os.path.basename(zip_path), f, "application/zip")},
            )
        print("Import status:", r_imp.status_code, r_imp.text)
        rev = r_imp.json().get("revision", "1") if r_imp.status_code == 200 else "1"

        print(f"--- 2. Deploying {proxy_name} rev {rev} to 'agentic-prod' ---")
        r_dep = client.post(
            f"{BASE_URL}/environments/agentic-prod/apis/{proxy_name}/revisions/{rev}/deployments",
            params={"override": "true", "serviceAccount": SA_EMAIL},
            headers=headers,
        )
        print("Deploy status:", r_dep.status_code, r_dep.text)

        print("--- 3. Updating API Product 'ge-multiagent-northbound-product' and creating 'vertex-gemini-llm-product' ---")
        prod_gemini = {
            "name": "vertex-gemini-llm-product",
            "displayName": "4. Vertex AI Gemini 2.5 LLM Product (OOTB LLMTokenQuota — admin@cviscontino.altostrat.com)",
            "description": "Mediates calls to Vertex AI Gemini 2.5 Flash (:generateContent) with Apigee Out-of-the-Box LLMTokenQuota (1500 tokens/min for admin@cviscontino.altostrat.com)",
            "approvalType": "auto",
            "environments": ["agentic-prod"],
            "proxies": ["vertex-gemini-llm-gateway", "agentic-ai-gateway"],
            "apiResources": ["/", "/**"],
            "quota": "50000",
            "quotaInterval": "1",
            "quotaTimeUnit": "hour",
        }
        r_p = client.post(f"{BASE_URL}/apiproducts", headers=headers, json=prod_gemini)
        if r_p.status_code == 409:
            r_p = client.put(f"{BASE_URL}/apiproducts/{prod_gemini['name']}", headers=headers, json=prod_gemini)
        print("Product vertex-gemini-llm-product:", r_p.status_code)


if __name__ == "__main__":
    main()
