import streamlit as st
import pandas as pd
import numpy as np
import os
from authlib.integrations.requests_client import OAuth2Session
from urllib.parse import urlencode, urlparse, parse_qs

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
    st.write(params)
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
    st.write(token)
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

# --- Streamlit UI ---
st.title('Device Management Application')
if "user" in st.session_state and st.sidebar.button("Force Log Out / Reset Login"):
    st.session_state.clear()
    st.rerun()

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
    if st.button("Log out"):
        st.session_state.clear()
        st.rerun()
else:
    st.markdown(f'<a href="{get_authorize_url()}" target="_self"><button>Log in to continue</button></a>', unsafe_allow_html=True)
