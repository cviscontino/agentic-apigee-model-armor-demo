#!/usr/bin/env python3
"""
Packages and deploys `agentic-ai-gateway` and `vertex-gemini-llm-gateway` with Out-of-the-Box
`<LLMTokenQuota>` policies (`LLMTokenQuota-Enforce` + `LLMTokenQuota-Count`) where the user token
budget for `admin@cviscontino.altostrat.com` (1,500 tokens/minute) is defined directly inside the
Apigee `<LLMTokenQuota>` policy via `<Class ref="extracted.userEmail">`.
Also verifies both proxies in live Apigee X Debug Sessions.
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

NORTHBOUND_API_KEY = "RDKyN3gVOGHVQh5NTrmASbxbbMuLpnaUuFNQ83NUAvOJ1YTy"
GEMINI_LLM_API_KEY = "cWuyDAxQdZW44ZAvWW3yq2XmIueZqJXlnMuwXheGJNSRgMI3"


def build_zip(bundle_root: str, zip_name: str) -> str:
    apiproxy_dir = os.path.join(bundle_root, "apiproxy")
    zip_path = os.path.join(APIGEE_ROOT, zip_name)
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for root, _, files in os.walk(apiproxy_dir):
            for file in files:
                if file.endswith(".xml"):
                    full_path = os.path.join(root, file)
                    rel_path = os.path.relpath(full_path, bundle_root)
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
    if r_imp.status_code != 200:
        print(f" [{proxy_name}] Import failed ({r_imp.status_code}): {r_imp.text}")
        raise RuntimeError(r_imp.text)
    rev = str(r_imp.json().get("revision", "1"))
    print(f" [{proxy_name}] Imported revision {rev} (HTTP {r_imp.status_code})")
    r_dep = client.post(
        f"{BASE_URL}/environments/agentic-prod/apis/{proxy_name}/revisions/{rev}/deployments",
        params={"override": "true", "serviceAccount": SA_EMAIL},
        headers=headers,
    )
    print(f" [{proxy_name}] Deployed revision {rev} to agentic-prod (HTTP {r_dep.status_code})")
    return rev


def main():
    creds, _ = google.auth.default(scopes=["https://www.googleapis.com/auth/cloud-platform"])
    creds.refresh(google.auth.transport.requests.Request())
    headers = {"Authorization": f"Bearer {creds.token}"}

    z_north = build_zip(APIGEE_ROOT, "agentic-ai-gateway.zip")
    z_gemini = build_zip(os.path.join(APIGEE_ROOT, "vertex-gemini-llm-gateway"), "vertex-gemini-llm-gateway.zip")

    with httpx.Client(timeout=60.0) as client:
        rev_north = deploy_proxy(client, headers, "agentic-ai-gateway", z_north)
        rev_gemini = deploy_proxy(client, headers, "vertex-gemini-llm-gateway", z_gemini)

        print("\nWaiting 6 seconds for Apigee runtime synchronization...")
        time.sleep(6.0)

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
                "path": f"/v1/agentic-fsi?apikey={NORTHBOUND_API_KEY}&user_email=admin@cviscontino.altostrat.com",
                "method": "POST",
                "payload": {"prompt": "Audit Wire Transfer risk", "user_email": "admin@cviscontino.altostrat.com"},
            },
        ).json()
        print("Test 1 (/v1/agentic-fsi) response:", r1.get("status_code"), "allowed=", r1.get("headers", {}).get("x-apigee-llmtokenquota-allowed"))

        r2 = client.post(
            relay_url,
            json={
                "path": f"/v1/llm/gemini?apikey={GEMINI_LLM_API_KEY}&user_email=admin@cviscontino.altostrat.com",
                "method": "POST",
                "payload": {
                    "contents": [{"role": "user", "parts": [{"text": "Synthesize a 2-sentence FSI AML summary."}]}],
                    "generationConfig": {"temperature": 0.2, "maxOutputTokens": 120},
                },
            },
        ).json()
        print("Test 2 (/v1/llm/gemini) response:", r2.get("status_code"), "allowed=", r2.get("headers", {}).get("x-apigee-llmtokenquota-allowed"), "used=", r2.get("headers", {}).get("x-apigee-llmtokenquota-used"), "avail=", r2.get("headers", {}).get("x-apigee-llmtokenquota-available"))

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
                        err_keys = {k: v for k, v in props.items() if any(w in k.lower() for w in ["error", "fault", "used.count", "available.count", "allowed.count", "class"])}
                        if ar in ("Error", "Abort") or pid == "Error" or step_name or err_keys:
                            print(f"  [Tx {tid}] Point={pid:14s} | Action={str(ar):10s} | Step={step_name:30s} | Info={err_keys}")


if __name__ == "__main__":
    main()
