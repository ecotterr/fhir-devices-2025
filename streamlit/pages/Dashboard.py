import streamlit as st
import pandas as pd
from datetime import datetime

import demoSettings
import Utils as Utils

FHIR_BASE_URL = demoSettings.base_url
MAPPINGS_PATH = demoSettings.mappings_path

DEBUG_BASIC_AUTH = True

st.title("Device Dashboard")

## Sidebar for patient selection
patient_id, selected_name = Utils.render_sidebar_patient_select()

observations = Utils.get_observations(patient_id)
devices = Utils.get_devices(patient_id)

## get Devices for Patient
st.header(f"Devices for {selected_name}")
if devices:
    for entry in devices:
        d = entry
        st.write(f"* {d.get('type', {}).get('text', 'Device')} — ID: `{d['id']}`")
else:
    st.info("No devices found for this patient.")

## get Observations for Devices
st.header("Observations")
selected_types = Utils.render_sidebar_observations_select(patient_id)

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
    selected_chart_type = st.selectbox("Chart Observation Type", selected_types)
    chart_df = df[df["Type"] == selected_chart_type]
    if not chart_df.empty:
        chart_df["Timestamp"] = pd.to_datetime(chart_df["Timestamp"])
        chart_df = chart_df.sort_values("Timestamp")
        st.line_chart(chart_df.set_index("Timestamp")["Value"])

    # Distribution plot
    st.markdown("### Value Distribution")
    selected_dist_type = st.selectbox("Distribution Observation Type", selected_types, key="dist")
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

Utils.render_sidebar_bottom()