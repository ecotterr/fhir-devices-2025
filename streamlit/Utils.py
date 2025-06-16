import streamlit as st
import requests
import time
import base64
import csv
import re

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

def auth_headers():
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
    return headers

@st.cache_data
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
    resource_ids = load_resource_ids() # streamlit cache should pull the same id list into context without reading CSV
    patient_ids = resource_ids.get("Patient", [])[:max]
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
        res = requests.get(url, headers=auth_headers())
        if res.status_code == 200:
            patients.append(res.json())
        else:
            st.warning(f"Failed to fetch Patient/{pid}: {res.status_code}")
    return patients

def get_patient_display_name(patient):
    # Try to use the first name entry
    names = patient.get("name", [])
    if names:
        name = names[0]
        # Prefer 'text' if present
        if "text" in name:
            return name["text"]
        # Otherwise, build from given/family
        given = name.get("given", [])[0]
        family = name.get("family", "")
        full_name = re.sub(r'\d+', '', f"{given} {family}").strip()
        if full_name:
            return full_name
    # Fallback to ID
    return patient.get("id", "Unknown")

def get_devices(pid):
    url = f"{FHIR_BASE_URL}/Device?patient=Patient/{pid}"
    res = requests.get(url, headers=auth_headers())
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
    res = requests.get(url, headers=auth_headers())
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

def render_sidebar_patient_select():
    ## Sidebar for patient selection
    patients = get_patients()
    patient_options = [
        {"id": p.get("id"), "name": get_patient_display_name(p)}
        for p in patients
    ]
    patient_dict = {p["name"]: p["id"] for p in patient_options}
    selected_name = st.sidebar.selectbox("Select Patient", list(patient_dict.keys()))
    patient_id = patient_dict[selected_name]
    return patient_id, selected_name

def render_sidebar_observations_select(pid):
    observations = get_observations(pid)
    obs_types = sorted(
        set(
            obs.get("code", {}).get("text") or
            obs.get("code", {}).get("coding", [{}])[0].get("display", "")
            for obs in observations
        )
    )
    selected_types = st.sidebar.multiselect("Observation Types", obs_types, default=obs_types)
    return selected_types

def render_sidebar_bottom():
    st.sidebar.markdown("---")
    st.sidebar.markdown("InterSystems Ready 2025")
    st.sidebar.markdown(
    """
    <a href="https://github.com/ecotterr/fhir-devices-2025" target="_blank">
        <img src="https://github.githubassets.com/images/modules/logos_page/GitHub-Mark.png" width="32" style="vertical-align:middle; margin-right:8px;">
        <span style="font-size:1.1em; vertical-align:middle;">View on GitHub</span>
    </a>
    """,
    unsafe_allow_html=True)
