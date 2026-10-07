import os
import zipfile
import httpx
import google.auth
import google.auth.transport.requests

ORG = "cvisco-agentic-demo"
BASE_URL = f"https://apigee.googleapis.com/v1/organizations/{ORG}"
APIPROXY_DIR = "/Users/cviscontino/jetski_projects/agentic-apigee-model-armor-demo/infra/apigee"
ZIP_PATH = os.path.join(APIPROXY_DIR, "agentic-ai-gateway.zip")
SA_EMAIL = f"apigee-model-armor-sa@{ORG}.iam.gserviceaccount.com"

def create_bundle_zip():
    with zipfile.ZipFile(ZIP_PATH, "w", zipfile.ZIP_DEFLATED) as zf:
        apiproxy_root = os.path.join(APIPROXY_DIR, "apiproxy")
        for root, _, files in os.walk(apiproxy_root):
            for file in files:
                if file.endswith(".xml"):
                    full_path = os.path.join(root, file)
                    rel_path = os.path.relpath(full_path, APIPROXY_DIR)
                    zf.write(full_path, rel_path)
                    print(f"Added to zip: {rel_path}")

def main():
    create_bundle_zip()
    creds, _ = google.auth.default(scopes=["https://www.googleapis.com/auth/cloud-platform"])
    creds.refresh(google.auth.transport.requests.Request())
    headers = {"Authorization": f"Bearer {creds.token}"}

    with httpx.Client(timeout=60.0) as client:
        # 1. Import API Proxy Bundle
        print("\n--- 1. Importing API Proxy Bundle: agentic-ai-gateway ---")
        with open(ZIP_PATH, "rb") as f:
            files = {"file": ("agentic-ai-gateway.zip", f, "application/zip")}
            r = client.post(
                f"{BASE_URL}/apis",
                params={"name": "agentic-ai-gateway", "action": "import"},
                headers=headers,
                files=files,
            )
        print("Import status:", r.status_code, r.text)
        rev = r.json().get("revision", "1") if r.status_code == 200 else "1"

        # 2. Ensure Comprehensive Environment 'agentic-prod' exists
        print("\n--- 2. Ensuring Comprehensive Environment 'agentic-prod' exists ---")
        r_env = client.get(f"{BASE_URL}/environments/agentic-prod", headers=headers)
        if r_env.status_code == 404:
            r_create_env = client.post(
                f"{BASE_URL}/environments",
                headers=headers,
                json={
                    "name": "agentic-prod",
                    "displayName": "Agentic AI Gateway Production Environment",
                    "description": "Comprehensive Apigee X Environment for Gemini Enterprise + Model Armor + A2A Demo",
                    "deploymentType": "PROXY",
                    "apiProxyType": "PROGRAMMABLE",
                    "type": "COMPREHENSIVE",
                },
            )
            print("Create env status:", r_create_env.status_code, r_create_env.text)
        else:
            print("Environment 'agentic-prod' already exists:", r_env.status_code)

        # 3. Ensure EnvGroup 'eval-envgroup' exists and 'agentic-prod' is attached
        print("\n--- 3. Ensuring EnvGroup 'eval-envgroup' exists ---")
        r_eg = client.get(f"{BASE_URL}/envgroups/eval-envgroup", headers=headers)
        if r_eg.status_code == 404:
            r_create_eg = client.post(
                f"{BASE_URL}/envgroups",
                headers=headers,
                json={
                    "name": "eval-envgroup",
                    "hostnames": [
                        "api.cvisco-agentic-demo.internal",
                        "agentic-gateway.cvisco-agentic-demo.example.com",
                    ],
                },
            )
            print("Create envgroup status:", r_create_eg.status_code, r_create_eg.text)

        # 4. Deploy API Proxy revision to 'agentic-prod' with Service Account
        print(f"\n--- 4. Deploying agentic-ai-gateway rev {rev} to 'agentic-prod' ---")
        r_dep = client.post(
            f"{BASE_URL}/environments/agentic-prod/apis/agentic-ai-gateway/revisions/{rev}/deployments",
            params={"override": "true", "serviceAccount": SA_EMAIL},
            headers=headers,
        )
        print("Deploy status:", r_dep.status_code, r_dep.text)

if __name__ == "__main__":
    main()
