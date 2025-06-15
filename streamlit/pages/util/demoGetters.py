import streamlit as st
import requests
import time
import base64
import csv

import demoSettings

FHIR_BASE_URL = demoSettings.base_url
MAPPINGS_PATH = demoSettings.mappings_path

DEBUG_BASIC_AUTH = True

def get_valid_access_token():
    from Home import refresh_access_token
    expiry = st.session_state.get("token_expiry")
    if expiry and time.time() > expiry:
        return refresh_access_token()
    return st.session_state.get("access_token")

if DEBUG_BASIC_AUTH:
    user_pass = "SuperUser:irisowner"
    basic_auth = base64.b64encode(user_pass.encode()).decode()
    headers = {
        "Authorization": f"Basic {basic_auth}",
        "Accept": "application/fhir+json"
    }
else:
    ACCESS_TOKEN = get_valid_access_token()
    headers = {
        "Authorization": f"Bearer {ACCESS_TOKEN}",
        "Accept": "application/fhir+json"
    }

def load_resource_ids():
    resource_ids = {}
    with open(MAPPINGS_PATH, newline='') as f:
        reader = csv.DictReader(f)
        for row in reader:
            resource_type = row['resource_type']
            resource_id = row['resource_id']
            resource_ids.setdefault(resource_type, []).append(resource_id)
    return resource_ids

def get_patients(max = 15):
    if not RESOURCE_IDS:
        RESOURCE_IDS = load_resource_ids()
    patient_ids = RESOURCE_IDS.get("Patient", [])
    unique_patient_ids = []
    seen = set()
    for pid in patient_ids:
        if pid not in seen:
            unique_patient_ids.append(pid)
            seen.add(pid)
        if len(unique_patient_ids) == max:
            break
    patients = []
    for pid in unique_patient_ids:
        url = f"{FHIR_BASE_URL}/Patient/{pid}"
        res = requests.get(url, headers=headers)
        if res.status_code == 200:
            patients.append(res.json())
        else:
            st.warning(f"Failed to fetch Patient/{pid}: {res.status_code}")
    return patients

def get_devices(pid):
    url = f"{FHIR_BASE_URL}/Device?patient=Patient/{pid}"
    res = requests.get(url, headers=headers)
    devices = []
    if res.status_code == 200:
        bundle = res.json()
        # Extract the "resource" from each entry in the bundle
        for entry in bundle.get("entry", []):
            resource = entry.get("resource")
            if resource:
                devices.append(resource)
    else:
        st.warning(f"Failed to fetch Devices for Patient/{pid}: {res.status_code}")
    return devices

def get_observations(pid):
    url = f"{FHIR_BASE_URL}/Observation?subject=Patient/{pid}"
    res = requests.get(url, headers=headers)
    observations = []
    if res.status_code == 200:
        bundle = res.json()
        # Extract the "resource" from each entry in the bundle
        for entry in bundle.get("entry", []):
            resource = entry.get("resource")
            if resource:
                observations.append(resource)
    else:
        st.warning(f"Failed to fetch Observations for Patient/{pid}: {res.status_code}")
    return observations
