import requests
import json
import base64
import demoSettings

FHIR_BASE = demoSettings.base_url
USERNAME = demoSettings.username
PASSWORD = demoSettings.password

# Load resources
with open("C:\SRC\GS2025\Developing on FHIR 2025\\bulk\devices\\fhir_output\observations.json") as f:
    observations = json.load(f)

# Prepare Basic Auth header
user_pass = f"{USERNAME}:{PASSWORD}"
basic_auth = base64.b64encode(user_pass.encode()).decode()
headers = {
    "Authorization": f"Basic {basic_auth}",
    "Content-Type": "application/fhir+json",
    "Accept": "application/fhir+json"
}

def post_resource(resource):
    url = f"{FHIR_BASE}/{resource['resourceType']}"
    resp = requests.post(url, headers=headers, json=resource)
    if resp.status_code in (200, 201):
        print(f"Posted {resource['resourceType']}/{resource.get('id', '')}: {resp.status_code}")
    else:
        print(f"Failed to post {resource['resourceType']}/{resource.get('id', '')}: {resp.status_code} {resp.text}")

# Post Observations
print("Posting Observations...")
for obs in observations:
    post_resource(obs)