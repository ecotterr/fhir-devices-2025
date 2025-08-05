import streamlit as st
import openai
import json

LOGGING = True

if LOGGING:
    import logging
    logging.basicConfig(
            level=logging.DEBUG,
            handlers=[
                logging.FileHandler("C:\SRC\GS2025\Developing on FHIR 2025\streamlit\pages\streamlit_logger.txt", mode='w'),
                logging.StreamHandler()
            ]                
        )
    logger = logging.getLogger(__name__)

import Utils
import demoSettings

st.title("Clinical Assistant")

patient_id, selected_name = Utils.render_sidebar_patient_select()
openai_tools = Utils.get_tools()

client = openai.OpenAI(api_key=demoSettings.openai_api_key)

if "chat_histories" not in st.session_state: ## We are storing different chat histories for each patient
    st.session_state.chat_histories = {}
if patient_id not in st.session_state.chat_histories:
    st.session_state.chat_histories[patient_id] = []

def get_current_chat_history():
    return st.session_state.chat_histories[patient_id]

def append_to_chat_history(role, content):
    if "chat_histories" not in st.session_state:
        st.session_state.chat_histories = {}
    if patient_id not in st.session_state.chat_histories:
        st.session_state.chat_histories[patient_id] = []
    st.session_state.chat_histories[patient_id].append({"role": role, "content": content})

def call_chatgpt(prompt, context=""):
    system_prompt = (
        "You are a clinical assistant with access to patient, device, and observation data. "
        "You can use the following Python functions to retrieve data: "
        "get_patients(), get_devices(patient_id), get_observations(patient_id). "
        "The selected patient ID that must be used for FHIR queries is: " + str(patient_id) + ". The patient's name is " + str(selected_name) + "."
        "If the user asks for patient/device/observation info, use the selected patient."
    )
    messages = [
        {"role": "system", "content": system_prompt + "\n" + context},
        {"role": "user", "content": prompt}
    ]
    response = client.chat.completions.create(
        model="o4-mini-2025-04-16",
        messages=messages,
        tools=openai_tools,
        tool_choice="auto",
        max_completion_tokens=10000
    )
    message = response.choices[0].message

    if message.content:
        return message.content.strip()
    if message.tool_calls:
        for tool_call in message.tool_calls:
            tool_name = tool_call.function.name
            st.info(f"Using {tool_name}")
        tool_messages = Utils.use_tools(message.tool_calls)
        messages.extend([message] + tool_messages)

        logger.info("Executing tools and sending result back to model...")

        response2 = client.chat.completions.create(
            model="o4-mini-2025-04-16",
            messages=messages,
            tools=openai_tools,
            max_completion_tokens=10000
        )

        final_msg = response2.choices[0].message
        return final_msg.content.strip() if final_msg.content else "Tool call completed, but model gave no message."
    logger.warning("Model returned no content or tool calls!!")
    return "No response from model."

def analyze_and_respond(user_input):
    logger.debug(f"Analyzing input: {user_input}")
    devices = Utils.get_devices(patient_id)
    observations = Utils.get_observations(patient_id)

    # Prep summaries for context injection
    device_summary = "\n".join([
        f"- {d.get('type', {}).get('text', d.get('id'))}" for d in devices
    ]) or "No devices found."

    observation_summary = "\n".join([
        f"- {o.get('code', {}).get('text') or o.get('code', {}).get('coding', [{}])[0].get('display', '')}"
        for o in observations
    ]) or "No observations found."

    context = (
        f"Patient ID: {patient_id}\n"
        f"Patient Name: {selected_name}\n\n"
        f"Devices:\n{device_summary}\n\n"
        f"Observations:\n{observation_summary}\n"
    )
    logger.debug("Calling OpenAI with injected context.")
    return call_chatgpt(user_input, context=context)

def everything_and_response(patient_id):
    bundle = Utils.get_patient_everything(patient_id)
    context = json.dumps(bundle, indent=2)[:10000]
    system_prompt = (
        "You are a clinical assistant with access to a patient's entire compartment from a FHIR Patient/$everything response. "
        "You have all the data you need from the bundle contents pasted at the end of this prompt. "
        "The patient's name is " + str(selected_name) + ". Provide a well balanced but detailed analysis of the patient's current and historic condition"
        "If you see symptoms, observations, allergies, medications or anything else that might be of interest to a clinician treating this patient, make sure to clearly call it out and explain its significance."
    )
    return call_chatgpt(system_prompt, context=context)

st.markdown("Ask a question about the selected patient, devices, or observations:")

user_input = st.text_input("Your question:", key="chat_input")

col1, col2 = st.columns([2, 2])
with col1:
    send_clicked = st.button("Send", key="SendButton")
with col2:
    everything_clicked = st.button("$everything", key="SendEverything")

if send_clicked and user_input:
    append_to_chat_history("user", user_input)
    with st.spinner("Thinking..."):
        response = analyze_and_respond(user_input)
    append_to_chat_history("assistant", response)

if everything_clicked:
    with st.spinner("Thinking..."):
        response = everything_and_response(patient_id)
    st.markdown(f"**Quick Ask Response:** {response}")

for msg in st.session_state.chat_histories[patient_id]:
    if msg["role"] == "user":
        st.markdown(f"**You:** {msg['content']}")
    else:
        st.markdown(f"**Assistant:** {msg['content']}")

st.markdown("---")
st.info("This assistant uses the currently selected patient from the sidebar for all queries.")

Utils.render_sidebar_bottom()