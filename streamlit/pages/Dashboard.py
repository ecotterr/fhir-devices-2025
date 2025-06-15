import streamlit as st
import pandas as pd
import requests
import base64
import time
from datetime import datetime
import csv
import re

import demoSettings
# from util.demoGetters import get_devices, get_observations, get_patients, get_valid_access_token

FHIR_BASE_URL = demoSettings.base_url
MAPPINGS_PATH = demoSettings.mappings_path

DEBUG_BASIC_AUTH = True

def get_valid_access_token():
    from Home import refresh_access_token
    expiry = st.session_state.get("token_expiry")
    if expiry and time.time() > expiry:
        return refresh_access_token()
    return st.session_state.get("access_token")

# Adding basic auth options for testing without OAuth flows. Always use OAuth in prod.
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

RESOURCE_IDS = load_resource_ids()

def get_patients():
    patient_ids = RESOURCE_IDS.get("Patient", [])
    unique_patient_ids = []
    seen = set()
    for pid in patient_ids:
        if pid not in seen:
            unique_patient_ids.append(pid)
            seen.add(pid)
        if len(unique_patient_ids) == 15:
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

##
st.title("Device Dashboard")

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

## Sidebar for patient selection
patients = get_patients()
patient_options = [
    {"id": p.get("id"), "name": get_patient_display_name(p)}
    for p in patients
]
patient_dict = {p["name"]: p["id"] for p in patient_options}
selected_name = st.sidebar.selectbox("Select Patient", list(patient_dict.keys()))
patient_id = patient_dict[selected_name]

observations = get_observations(patient_id)
devices = get_devices(patient_id)

## get Devices for Patient
st.header(f"Devices for {selected_name}")
devices = get_devices(patient_id)
if devices:
    for entry in devices:
        d = entry
        st.write(f"🔹 {d.get('type', {}).get('text', 'Device')} — ID: `{d['id']}`")
else:
    st.info("No devices found for this patient.")

## get Observations for Devices
st.header("Observations")
observations = get_observations(patient_id)

# Extract available observation types
obs_types = sorted(
    set(
        obs.get("code", {}).get("text") or
        obs.get("code", {}).get("coding", [{}])[0].get("display", "")
        for obs in observations
    )
)
selected_types = st.sidebar.multiselect("Observation Types", obs_types, default=obs_types)

# Date range filter
dates = [
    obs.get("effectiveDateTime", "")[:10]
    for obs in observations if obs.get("effectiveDateTime")
]
if dates:
    min_date, max_date = min(dates), max(dates)
    date_range = st.sidebar.date_input("Date Range", [min_date, max_date])
else:
    date_range = None

data = []
if observations:
    for obs in observations:
        value = obs.get("valueQuantity", {}).get("value")
        unit = obs.get("valueQuantity", {}).get("unit")
        effective = obs.get("effectiveDateTime")

        coding_list = obs.get("code", {}).get("coding", [])
        obs_type = coding_list[0].get("display") if coding_list else None
        obs_code = coding_list[0].get("code") if coding_list else None
        if obs_type in selected_types:
            if date_range and effective:
                if not (date_range[0] <= datetime.strptime(effective.split("T")[0],"%Y-%m-%d").date() <= date_range[1]):
                    continue
            data.append({
                "Value": value,
                "Unit": unit,
                "Timestamp": effective[:10] + '   ' + effective[11:19],
                "Type": obs_type,
                "Code": obs_code
            })
    df = pd.DataFrame(data, columns=["Value", "Unit", "Timestamp", "Type", "Code"])
    st.dataframe(
        df.sort_values("Timestamp", ascending=False),
        use_container_width=True
    )
else:
    st.info("No observations found for these devices.")

## analytics

import matplotlib.pyplot as plt
import seaborn as sns

st.subheader(f"Summary for {selected_name}")
if not df.empty:
    col1, col2, col3 = st.columns(3)
    col1.metric("Total Observations", len(df))
    col2.metric("Unique Types", df['Type'].nunique())
    col3.markdown(
        f"<span style='font-size: 0.9em; color: var(--text-color);'>"
        f"**Date Range**<br>{df['Timestamp'].min()[:10]} - {df['Timestamp'].max()[:10]}"
        f"</span>",
        unsafe_allow_html=True
    )

    # Show most recent readings
    st.markdown("### Most Recent Readings")
    st.dataframe(df.sort_values("Timestamp", ascending=False).groupby("Type").head(1).reset_index(drop=True))

    # Time series plot for selected type
    st.markdown("### Time Series")
    selected_chart_type = st.selectbox("Chart Observation Type", obs_types)
    chart_df = df[df["Type"] == selected_chart_type]
    if not chart_df.empty:
        chart_df["Timestamp"] = pd.to_datetime(chart_df["Timestamp"])
        chart_df = chart_df.sort_values("Timestamp")
        st.line_chart(chart_df.set_index("Timestamp")["Value"])

    # Distribution plot
    st.markdown("### Value Distribution")
    selected_dist_type = st.selectbox("Distribution Observation Type", obs_types, key="dist")
    dist_df = df[df["Type"] == selected_dist_type]
    if not dist_df.empty:
        fig, ax = plt.subplots()
        sns.histplot(dist_df["Value"], kde=True, ax=ax)
        ax.set_xlabel(selected_dist_type)
        st.pyplot(fig)

    # Device summary
    st.markdown("### Devices Used")
    device_types = [d.get("type", {}).get("text", "Unknown") for d in devices]
    st.bar_chart(pd.Series(device_types).value_counts())

    # Download button
    st.download_button("Download Data as CSV", df.to_csv(index=False), "observations.csv")
else:
    st.info("No observations found for the selected filters.")

with st.sidebar.expander("Analytics Info"):
    st.write("Use the filters above to explore patient data, visualize trends, and download results.")

st.sidebar.markdown("---")
st.sidebar.markdown("InterSystems Ready 2025")
st.sidebar.markdown(
    """
    <a href="https://github.com/ecotterr/fhir-devices-2025" target="_blank">
        <img src="https://github.githubassets.com/images/modules/logos_page/GitHub-Mark.png" width="32" style="vertical-align:middle; margin-right:8px;">
        <span style="font-size:1.1em; vertical-align:middle;">github.com/ecotterr</span>
    </a>
    """,
    unsafe_allow_html=True
)