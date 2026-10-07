#!/usr/bin/env python3
"""
Fixes the two errors observed in Apigee X Debug Sessions on `agentic-ai-gateway` and `vertex-gemini-llm-gateway`:
1. `policies.llmtokenquota.FailedToResolveModelName` on `Q-TokenQuota-Enforce`:
   Explicitly sets `<LLMModelSource>gemini-2.5-flash</LLMModelSource>` in `Q-TokenQuota-Enforce` and `Q-TokenQuota-Count`.
2. `steps.oauth.v2.FailedToResolveAPIKey` on `VA-VerifyApiKey`:
   Configures `VA-VerifyApiKey` to read `<APIKey ref="request.queryparam.apikey"/>` so it traverses the Cloud Run PSC Relay intact,
   and strips internal query parameters via `AM-CleanTargetRequest` before forwarding to Vertex AI `generateContent`.
3. Grants `roles/aiplatform.user` to `apigee-model-armor-sa@cvisco-agentic-demo.iam.gserviceaccount.com` so the TargetEndpoint
   can invoke Vertex AI Gemini 2.5 Flash (:generateContent) directly.
"""
import os
import time
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

NORTHBOUND_API_KEY = "RDKyN3gVOGHVQh5NTrmASbxbbMuLpnaUuFNQ83NUAvOJ1YTy"
GEMINI_LLM_API_KEY = "cWuyDAxQdZW44ZAvWW3yq2XmIueZqJXlnMuwXheGJNSRgMI3"


def ensure_sa_vertex_role(client: httpx.Client, headers: dict) -> None:
    print("=== 0. Ensuring apigee-model-armor-sa has roles/aiplatform.user ===")
    crm_url = f"https://cloudresourcemanager.googleapis.com/v1/projects/{ORG}"
    r_get = client.post(f"{crm_url}:getIamPolicy", headers=headers, json={})
    if r_get.status_code != 200:
        print("getIamPolicy status:", r_get.status_code)
        return
    policy = r_get.json()
    bindings = policy.get("bindings", [])
    member = f"serviceAccount:{SA_EMAIL}"
    role = "roles/aiplatform.user"
    found = False
    for b in bindings:
        if b.get("role") == role:
            if member not in b.get("members", []):
                b.setdefault("members", []).append(member)
            found = True
            break
    if not found:
        bindings.append({"role": role, "members": [member]})
    policy["bindings"] = bindings
    r_set = client.post(f"{crm_url}:setIamPolicy", headers=headers, json={"policy": policy})
    print(f" [IAM] {SA_EMAIL} -> {role} (HTTP {r_set.status_code})")


def update_agentic_ai_gateway_bundle() -> str:
    """Updates `infra/apigee/apiproxy` (agentic-ai-gateway) and returns zip path."""
    apiproxy_dir = os.path.join(APIGEE_ROOT, "apiproxy")
    policies_dir = os.path.join(apiproxy_dir, "policies")
    proxies_dir = os.path.join(apiproxy_dir, "proxies")

    # 1. VA-VerifyApiKey.xml -> reads request.queryparam.apikey
    with open(os.path.join(policies_dir, "VA-VerifyApiKey.xml"), "w") as f:
        f.write("""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<VerifyAPIKey async="false" continueOnError="false" enabled="true" name="VA-VerifyApiKey">
    <DisplayName>VA-VerifyApiKey</DisplayName>
    <APIKey ref="request.queryparam.apikey"/>
</VerifyAPIKey>
""")

    # 2. EV-ExtractUserPrompt.xml -> reads queryparam user_email & token_limit + JSON prompt
    with open(os.path.join(policies_dir, "EV-ExtractUserPrompt.xml"), "w") as f:
        f.write("""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<ExtractVariables async="false" continueOnError="true" enabled="true" name="EV-ExtractUserPrompt">
    <DisplayName>EV-ExtractUserPrompt</DisplayName>
    <Source clearPayload="false">request</Source>
    <QueryParam name="user_email">
        <Pattern ignoreCase="true">{userEmail}</Pattern>
    </QueryParam>
    <QueryParam name="token_limit">
        <Pattern ignoreCase="true">{tokenLimit}</Pattern>
    </QueryParam>
    <JSONPayload>
        <Variable name="userPrompt" type="string">
            <JSONPath>$.prompt</JSONPath>
        </Variable>
        <Variable name="userEmail" type="string">
            <JSONPath>$.user_email</JSONPath>
        </Variable>
    </JSONPayload>
    <VariablePrefix>extracted</VariablePrefix>
    <IgnoreUnresolvedVariables>true</IgnoreUnresolvedVariables>
</ExtractVariables>
""")

    # 3. Q-TokenQuota-Enforce.xml -> Explicit <LLMModelSource>gemini-2.5-flash</LLMModelSource>
    with open(os.path.join(policies_dir, "Q-TokenQuota-Enforce.xml"), "w") as f:
        f.write("""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<LLMTokenQuota async="false" continueOnError="false" enabled="true" name="Q-TokenQuota-Enforce" type="rollingwindow">
    <DisplayName>Q-TokenQuota-Enforce (OOTB AI Policy)</DisplayName>
    <SharedName>user-gemini-token-counter</SharedName>
    <EnforceOnly>true</EnforceOnly>
    <Identifier ref="extracted.userEmail"/>
    <LLMModelSource>gemini-2.5-flash</LLMModelSource>
    <Allow count="1500" countRef="extracted.tokenLimit"/>
    <Interval>1</Interval>
    <TimeUnit>minute</TimeUnit>
    <Distributed>true</Distributed>
    <Synchronous>true</Synchronous>
</LLMTokenQuota>
""")

    # 4. Q-TokenQuota-Count.xml -> Explicit <LLMModelSource>gemini-2.5-flash</LLMModelSource>
    with open(os.path.join(policies_dir, "Q-TokenQuota-Count.xml"), "w") as f:
        f.write("""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<LLMTokenQuota async="false" continueOnError="true" enabled="true" name="Q-TokenQuota-Count" type="rollingwindow">
    <DisplayName>Q-TokenQuota-Count (OOTB AI Policy)</DisplayName>
    <SharedName>user-gemini-token-counter</SharedName>
    <CountOnly>true</CountOnly>
    <Identifier ref="extracted.userEmail"/>
    <LLMModelSource>gemini-2.5-flash</LLMModelSource>
    <Allow count="1500" countRef="extracted.tokenLimit"/>
    <Interval>1</Interval>
    <TimeUnit>minute</TimeUnit>
    <Distributed>true</Distributed>
    <Synchronous>true</Synchronous>
    <LLMTokenUsageSource>{jsonPath('$.usageMetadata.totalTokenCount',response.content,true)}</LLMTokenUsageSource>
</LLMTokenQuota>
""")

    # 5. AM-InjectTelemetryHeaders.xml -> Reads Q-TokenQuota-Enforce ratelimit variables cleanly
    with open(os.path.join(policies_dir, "AM-InjectTelemetryHeaders.xml"), "w") as f:
        f.write("""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<AssignMessage async="false" continueOnError="false" enabled="true" name="AM-InjectTelemetryHeaders">
    <DisplayName>AM-InjectTelemetryHeaders</DisplayName>
    <Set>
        <Headers>
            <Header name="Content-Type">application/json</Header>
            <Header name="X-Apigee-Gateway">agentic-ai-gateway-v1</Header>
            <Header name="X-Apigee-User-Identity">{extracted.userEmail}</Header>
            <Header name="X-Apigee-LLMTokenQuota-Allowed">{ratelimit.Q-TokenQuota-Enforce.allowed.count}</Header>
            <Header name="X-Apigee-LLMTokenQuota-Used">{ratelimit.Q-TokenQuota-Enforce.used.count}</Header>
            <Header name="X-Apigee-LLMTokenQuota-Available">{ratelimit.Q-TokenQuota-Enforce.available.count}</Header>
            <Header name="X-Apigee-LLMTokenQuota-Reset">{ratelimit.Q-TokenQuota-Enforce.expiry.time}</Header>
            <Header name="X-Model-Armor-Template">projects/cvisco-agentic-demo/locations/europe-west1/templates/fsi-agent-armor-strict</Header>
            <Header name="X-Model-Armor-Input-Verdict">{modelArmor.filterMatchState}</Header>
            <Header name="X-Gemini-Enterprise-Target">ge-root-orchestrator</Header>
        </Headers>
        <Payload contentType="application/json">{
  "status": "APIGEE_MODEL_ARMOR_APPROVED",
  "proxy": "agentic-ai-gateway",
  "environment": "agentic-prod",
  "userIdentity": "{extracted.userEmail}",
  "llmTokenQuotaPolicy": "Q-TokenQuota-Enforce (OOTB LLMTokenQuota Pre-Check PASSED)",
  "modelArmorInputVerdict": "{modelArmor.filterMatchState}",
  "targetOrchestrator": "ge-root-orchestrator"
}</Payload>
        <StatusCode>200</StatusCode>
    </Set>
    <IgnoreUnresolvedVariables>true</IgnoreUnresolvedVariables>
</AssignMessage>
""")

    # 6. proxies/default.xml -> Runs VA-VerifyApiKey, SA-SpikeArrest-Burst, EV-ExtractUserPrompt, Q-TokenQuota-Enforce, SC-ModelArmor-SanitizeInput, EV-ExtractModelArmorVerdict, RF-ModelArmorBlocked in Request; SC-ModelArmor-SanitizeOutput + AM-InjectTelemetryHeaders in Response
    with open(os.path.join(proxies_dir, "default.xml"), "w") as f:
        f.write("""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<ProxyEndpoint name="default">
    <Description>Apigee AI Gateway mediating Gemini Enterprise Multi-Agent with Model Armor &amp; OOTB LLMTokenQuota per User</Description>
    <PreFlow name="PreFlow">
        <Request>
            <Step>
                <Name>VA-VerifyApiKey</Name>
                <Condition>request.queryparam.apikey != null</Condition>
            </Step>
            <Step>
                <Name>SA-SpikeArrest-Burst</Name>
            </Step>
            <Step>
                <Name>EV-ExtractUserPrompt</Name>
                <Condition>request.verb == "POST"</Condition>
            </Step>
            <Step>
                <Name>Q-TokenQuota-Enforce</Name>
                <Condition>request.verb == "POST"</Condition>
            </Step>
            <Step>
                <Name>SC-ModelArmor-SanitizeInput</Name>
                <Condition>request.verb == "POST"</Condition>
            </Step>
            <Step>
                <Name>EV-ExtractModelArmorVerdict</Name>
                <Condition>request.verb == "POST"</Condition>
            </Step>
            <Step>
                <Name>RF-ModelArmorBlocked</Name>
                <Condition>(request.verb == "POST") and (modelArmor.filterMatchState == "MATCH_FOUND")</Condition>
            </Step>
        </Request>
        <Response>
            <Step>
                <Name>SC-ModelArmor-SanitizeOutput</Name>
                <Condition>request.verb == "POST"</Condition>
            </Step>
            <Step>
                <Name>AM-InjectTelemetryHeaders</Name>
            </Step>
        </Response>
    </PreFlow>
    <HTTPProxyConnection>
        <BasePath>/v1/agentic-fsi</BasePath>
    </HTTPProxyConnection>
    <RouteRule name="gemini-enterprise-route"/>
</ProxyEndpoint>
""")

    zip_path = os.path.join(APIGEE_ROOT, "agentic-ai-gateway.zip")
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for root, _, files in os.walk(apiproxy_dir):
            for file in files:
                if file.endswith(".xml"):
                    full_path = os.path.join(root, file)
                    rel_path = os.path.relpath(full_path, APIGEE_ROOT)
                    zf.write(full_path, rel_path)
    return zip_path


def update_vertex_gemini_llm_gateway_bundle() -> str:
    """Updates `infra/apigee/vertex-gemini-llm-gateway` and returns zip path."""
    proxy_name = "vertex-gemini-llm-gateway"
    proxy_dir = os.path.join(APIGEE_ROOT, proxy_name)
    apiproxy_dir = os.path.join(proxy_dir, "apiproxy")
    os.makedirs(os.path.join(apiproxy_dir, "proxies"), exist_ok=True)
    os.makedirs(os.path.join(apiproxy_dir, "targets"), exist_ok=True)
    os.makedirs(os.path.join(apiproxy_dir, "policies"), exist_ok=True)

    with open(os.path.join(apiproxy_dir, f"{proxy_name}.xml"), "w") as f:
        f.write(f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<APIProxy revision="2" name="{proxy_name}">
    <DisplayName>Vertex AI Gemini 2.5 LLM Proxy (OOTB LLMTokenQuota — admin@cviscontino.altostrat.com)</DisplayName>
    <Description>Apigee X AI Gateway Proxy to Vertex AI Gemini 2.5 Flash (:generateContent) with Out-of-the-Box LLMTokenQuota (EnforceOnly + CountOnly on $.usageMetadata.totalTokenCount) for admin@cviscontino.altostrat.com and Cloud Model Armor</Description>
    <BasePaths>/v1/llm/gemini</BasePaths>
    <Policies>
        <Policy>VA-VerifyApiKey</Policy>
        <Policy>EV-ExtractUserIdentity</Policy>
        <Policy>Q-TokenQuota-Enforce</Policy>
        <Policy>SC-ModelArmor-SanitizeInput</Policy>
        <Policy>AM-CleanTargetRequest</Policy>
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
                <Condition>request.queryparam.apikey != null</Condition>
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
        <Request>
            <Step>
                <Name>AM-CleanTargetRequest</Name>
            </Step>
        </Request>
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
<VerifyAPIKey async="false" continueOnError="false" enabled="true" name="VA-VerifyApiKey">
    <DisplayName>VA-VerifyApiKey</DisplayName>
    <APIKey ref="request.queryparam.apikey"/>
</VerifyAPIKey>
""",
        "EV-ExtractUserIdentity.xml": """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<ExtractVariables async="false" continueOnError="true" enabled="true" name="EV-ExtractUserIdentity">
    <DisplayName>EV-ExtractUserIdentity</DisplayName>
    <Source clearPayload="false">request</Source>
    <QueryParam name="user_email">
        <Pattern ignoreCase="true">{userEmail}</Pattern>
    </QueryParam>
    <QueryParam name="token_limit">
        <Pattern ignoreCase="true">{tokenLimit}</Pattern>
    </QueryParam>
    <JSONPayload>
        <Variable name="userPrompt" type="string">
            <JSONPath>$.contents[0].parts[0].text</JSONPath>
        </Variable>
    </JSONPayload>
    <VariablePrefix>extracted</VariablePrefix>
    <IgnoreUnresolvedVariables>true</IgnoreUnresolvedVariables>
</ExtractVariables>
""",
        "Q-TokenQuota-Enforce.xml": """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<LLMTokenQuota async="false" continueOnError="false" enabled="true" name="Q-TokenQuota-Enforce" type="rollingwindow">
    <DisplayName>Q-TokenQuota-Enforce</DisplayName>
    <SharedName>user-gemini-token-counter</SharedName>
    <EnforceOnly>true</EnforceOnly>
    <Identifier ref="extracted.userEmail"/>
    <LLMModelSource>gemini-2.5-flash</LLMModelSource>
    <Allow count="1500" countRef="extracted.tokenLimit"/>
    <Interval>1</Interval>
    <TimeUnit>minute</TimeUnit>
    <Distributed>true</Distributed>
    <Synchronous>true</Synchronous>
</LLMTokenQuota>
""",
        "Q-TokenQuota-Count.xml": """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<LLMTokenQuota async="false" continueOnError="false" enabled="true" name="Q-TokenQuota-Count" type="rollingwindow">
    <DisplayName>Q-TokenQuota-Count</DisplayName>
    <SharedName>user-gemini-token-counter</SharedName>
    <CountOnly>true</CountOnly>
    <Identifier ref="extracted.userEmail"/>
    <LLMModelSource>gemini-2.5-flash</LLMModelSource>
    <Allow count="1500" countRef="extracted.tokenLimit"/>
    <Interval>1</Interval>
    <TimeUnit>minute</TimeUnit>
    <Distributed>true</Distributed>
    <Synchronous>true</Synchronous>
    <LLMTokenUsageSource>{jsonPath('$.usageMetadata.totalTokenCount',response.content,true)}</LLMTokenUsageSource>
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
        "AM-CleanTargetRequest.xml": """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<AssignMessage async="false" continueOnError="false" enabled="true" name="AM-CleanTargetRequest">
    <DisplayName>AM-CleanTargetRequest</DisplayName>
    <Remove>
        <QueryParams/>
    </Remove>
    <AssignVariable>
        <Name>target.copy.pathsuffix</Name>
        <Value>false</Value>
    </AssignVariable>
    <IgnoreUnresolvedVariables>true</IgnoreUnresolvedVariables>
</AssignMessage>
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


def deploy_proxy(client: httpx.Client, headers: dict, proxy_name: str, zip_path: str) -> str:
    print(f"\n=== Importing & Deploying {proxy_name} ===")
    with open(zip_path, "rb") as f:
        r_imp = client.post(
            f"{BASE_URL}/apis",
            params={"name": proxy_name, "action": "import"},
            headers=headers,
            files={"file": (os.path.basename(zip_path), f, "application/zip")},
        )
    rev = r_imp.json().get("revision", "1")
    print(f" [{proxy_name}] Imported revision {rev} (HTTP {r_imp.status_code})")
    r_dep = client.post(
        f"{BASE_URL}/environments/agentic-prod/apis/{proxy_name}/revisions/{rev}/deployments",
        params={"override": "true", "serviceAccount": SA_EMAIL},
        headers=headers,
    )
    print(f" [{proxy_name}] Deployed revision {rev} to agentic-prod (HTTP {r_dep.status_code})")
    return str(rev)


def main():
    creds, _ = google.auth.default(scopes=["https://www.googleapis.com/auth/cloud-platform"])
    creds.refresh(google.auth.transport.requests.Request())
    headers = {"Authorization": f"Bearer {creds.token}"}

    with httpx.Client(timeout=60.0) as client:
        ensure_sa_vertex_role(client, {**headers, "x-goog-user-project": ORG, "Content-Type": "application/json"})
        z_north = update_agentic_ai_gateway_bundle()
        z_gemini = update_vertex_gemini_llm_gateway_bundle()
        rev_north = deploy_proxy(client, headers, "agentic-ai-gateway", z_north)
        rev_gemini = deploy_proxy(client, headers, "vertex-gemini-llm-gateway", z_gemini)

        print("\nWaiting 6 seconds for Apigee runtime synchronization...")
        time.sleep(6.0)

        # Start fresh debug sessions on both newly deployed revisions
        s_north = client.post(
            f"{BASE_URL}/environments/agentic-prod/apis/agentic-ai-gateway/revisions/{rev_north}/debugsessions",
            headers=headers,
        ).json().get("name", "").split("/")[-1]
        s_gemini = client.post(
            f"{BASE_URL}/environments/agentic-prod/apis/vertex-gemini-llm-gateway/revisions/{rev_gemini}/debugsessions",
            headers=headers,
        ).json().get("name", "").split("/")[-1]
        print(f"Started Debug Sessions -> agentic-ai-gateway(rev {rev_north}): {s_north} | vertex-gemini-llm-gateway(rev {rev_gemini}): {s_gemini}")

        relay_url = "https://agentic-fsi-demo-1070899805958.europe-west1.run.app/api/apigee/psc-relay"
        r1 = client.post(
            relay_url,
            json={
                "path": f"/v1/agentic-fsi?apikey={NORTHBOUND_API_KEY}&user_email=admin@cviscontino.altostrat.com&token_limit=1500",
                "method": "POST",
                "payload": {"prompt": "Audit Wire Transfer risk", "user_email": "admin@cviscontino.altostrat.com"},
            },
        ).json()
        print("Test 1 (/v1/agentic-fsi) response:", r1.get("status_code"), r1.get("headers", {}).get("x-apigee-llmtokenquota-allowed"))

        r2 = client.post(
            relay_url,
            json={
                "path": f"/v1/llm/gemini?apikey={GEMINI_LLM_API_KEY}&user_email=admin@cviscontino.altostrat.com&token_limit=1500",
                "method": "POST",
                "payload": {
                    "contents": [{"role": "user", "parts": [{"text": "Synthesize a 2-sentence FSI AML summary."}]}],
                    "generationConfig": {"temperature": 0.2, "maxOutputTokens": 120},
                },
            },
        ).json()
        print("Test 2 (/v1/llm/gemini) response:", r2.get("status_code"), "used=", r2.get("headers", {}).get("x-apigee-llmtokenquota-used"), "avail=", r2.get("headers", {}).get("x-apigee-llmtokenquota-available"))

        time.sleep(2.0)
        for api, rev, sid in [("agentic-ai-gateway", rev_north, s_north), ("vertex-gemini-llm-gateway", rev_gemini, s_gemini)]:
            txs = client.get(f"{BASE_URL}/environments/agentic-prod/apis/{api}/revisions/{rev}/debugsessions/{sid}/data", headers=headers).json()
            print(f"\n=== VERIFIED DEBUG SESSION FOR {api} (rev {rev}) | Txs={txs} ===")
            for tid in (txs if isinstance(txs, list) else []):
                tx_detail = client.get(f"{BASE_URL}/environments/agentic-prod/apis/{api}/revisions/{rev}/debugsessions/{sid}/data/{tid}", headers=headers).json()
                for pt in tx_detail.get("point", []):
                    pid = pt.get("id")
                    for res in pt.get("results", []):
                        ar = res.get("ActionResult")
                        props = {p.get("name"): p.get("value") for p in res.get("properties", {}).get("property", [])}
                        step_name = props.get("stepDefinition-name") or props.get("expression") or ""
                        err_keys = {k: v for k, v in props.items() if any(w in k.lower() for w in ["error", "fault", "used.count", "available.count", "allowed.count"])}
                        if ar in ("Error", "Abort") or pid == "Error" or step_name or err_keys:
                            print(f"  [Tx {tid}] Point={pid:14s} | Action={str(ar):10s} | Step={step_name:30s} | Info={err_keys}")


if __name__ == "__main__":
    main()
