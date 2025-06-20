import streamlit as st
import pandas as pd
from authlib.integrations.requests_client import OAuth2Session
from urllib.parse import urlencode, urlparse, parse_qs

import Utils

import demoSettings

AUTH0_AUTHORIZE_URL = f"https://{demoSettings.domain}/authorize"
AUTH0_TOKEN_URL = f"https://{demoSettings.domain}/oauth/token"
AUTH0_CLIENT_ID = demoSettings.client_id
AUTH0_CLIENT_SECRET = demoSettings.client_secret
AUTH0_CALLBACK_URL = "http://localhost:8501/"
AUTH0_AUDIENCE = demoSettings.audience if hasattr(demoSettings, "audience") else None
FHIR_BASE_URL = demoSettings.base_url
MAPPINGS_PATH = demoSettings.mappings_path

def get_authorize_url():
    params = {
        "client_id": AUTH0_CLIENT_ID,
        "response_type": "code",
        "redirect_uri": AUTH0_CALLBACK_URL,
        "scope": "openid profile email",
        "prompt": "login"
    }
    if AUTH0_AUDIENCE:
        params["audience"] = AUTH0_AUDIENCE
    return f"{AUTH0_AUTHORIZE_URL}?{urlencode(params)}"

def get_token(code):
    print("Exchanging code:", code)
    print("Redirect URI:", AUTH0_CALLBACK_URL)
    session = OAuth2Session(AUTH0_CLIENT_ID, AUTH0_CLIENT_SECRET, redirect_uri=AUTH0_CALLBACK_URL)
    token = session.fetch_token(
        AUTH0_TOKEN_URL,
        code=code,
        grant_type="authorization_code",
        client_secret=AUTH0_CLIENT_SECRET,
    )
    return token

def get_user_info(token):
    import requests
    headers = {"Authorization": f"Bearer {token['access_token']}"}
    resp = requests.get(f"https://{demoSettings.domain}/userinfo", headers=headers)
    return resp.json()

def refresh_access_token():
    refresh_token = st.session_state.get("refresh_token")
    if not refresh_token:
        st.error("No refresh token available. Please log in again.")
        st.stop()
    session = OAuth2Session(AUTH0_CLIENT_ID, AUTH0_CLIENT_SECRET, redirect_uri=AUTH0_CALLBACK_URL)
    token = session.refresh_token(
        AUTH0_TOKEN_URL,
        refresh_token=refresh_token,
        client_id=AUTH0_CLIENT_ID,
        client_secret=AUTH0_CLIENT_SECRET,
    )
    st.session_state["access_token"] = token["access_token"]
    if "expires_in" in token:
        import time
        st.session_state["token_expiry"] = time.time() + token["expires_in"]
    return token["access_token"]

st.title('Device Management Application')

query_params = st.query_params 

if "code" in query_params:
    code = query_params["code"]
    try:
        token = get_token(code)
        user_info = get_user_info(token)
        st.session_state["user"] = user_info
        st.session_state["access_token"] = token["access_token"] 
        if "refresh_token" in token:
            st.session_state["refresh_token"] = token["refresh_token"]
        if "expires_in" in token:
            import time
            st.session_state["token_expiry"] = time.time() + token["expires_in"]
        st.query_params.clear()  # Remove code from URL after use
        st.success(f"Logged in as {user_info['name']}")
    except Exception as e:
        st.error(f"Authentication failed: {e}")
        st.session_state.clear()
        st.query_params.clear()  # Remove code from URL on error
        st.stop()
elif "user" in st.session_state:
    user_info = st.session_state["user"]
    st.write(f"Hello, {user_info['name']}!")
else:
    st.markdown(f'<a href="{get_authorize_url()}" target="_self"><button>Log in to continue</button></a>', unsafe_allow_html=True)
    st.sidebar.markdown("Log in to view authorized patients")
    st.sidebar.markdown(f'<a href="{get_authorize_url()}" target="_self"><button>Log in to continue</button></a>', unsafe_allow_html=True)

if "user" in st.session_state:
    # Reveal the Patient dropdown (should be empty for unauthenticated user!)
    patient_id, selected_name = Utils.render_sidebar_patient_select()
    # Show total metrics
    st.markdown("## Metrics")
    all_devices = Utils.get_total_devices()
    col1, col2 = st.columns(2)
    with col1:
        st.metric(label="Total Patients", value=len(Utils.get_unique_patients()))
    with col2:
        st.metric(label="Total Devices", value=len(all_devices))
    
    st.markdown("## Devices")
    device_types = []
    for device in all_devices:
        codings = device.get("type", {}).get("coding", [])
        for coding in codings:
            display = coding.get("display", "Unknown")
            code = coding.get("code", "Unknown")
            device_types.append((display, code))
    df = pd.DataFrame(device_types, columns=["Device Type", "Device Code"])
    count_df = df.value_counts().reset_index(name="Count")
    st.table(count_df)

Utils.render_sidebar_bottom()