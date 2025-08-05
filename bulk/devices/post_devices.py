import requests
import json
import base64
import demoSettings
from concurrent.futures import ThreadPoolExecutor, as_completed

FHIR_BASE = demoSettings.base_url
USERNAME = demoSettings.username
PASSWORD = demoSettings.password

THREAD_COUNT = 12

# Load resources
with open("C:\SRC\GS2025\Developing on FHIR 2025\\bulk\devices\\fhir_output\devices.json") as f:
    devices = json.load(f)

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

# Post Devices
print("Posting Devices...")

with ThreadPoolExecutor(max_workers=THREAD_COUNT) as executor:
    futures = [executor.submit(post_resource, device) for device in devices]
    for future in as_completed(futures):
        pass