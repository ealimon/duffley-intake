import streamlit as st
import google.generativeai as genai
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime

# 1. UI Branding for Duffley Law
st.set_page_config(page_title="Duffley Law Intake", page_icon="⚖️", layout="centered")
st.markdown("<style>#MainMenu, footer, header {visibility: hidden;} .stApp {background-color: #f8f9fa;}</style>", unsafe_allow_html=True)

# 2. Connection (Uses your existing Secrets)
conn = st.connection("gsheets", type=GSheetsConnection, ttl=0)

# 3. Gemini Config
genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
model = genai.GenerativeModel(
    model_name="gemini-3.1-flash-lite-preview", 
    system_instruction="[INSERT THE LEGAL BRAIN INSTRUCTION FROM ABOVE HERE]"
)

# 4. State & Chat Logic
if "messages" not in st.session_state:
    st.session_state.messages = []
    st.session_state.chat_session = model.start_chat(history=[])
    st.session_state.lead_captured = False

# Initial Welcome
if not st.session_state.messages:
    welcome = "Welcome to Duffley Law PLLC. I am an AI assistant, not an attorney, and this chat does not create an attorney-client relationship. How can we help you protect your legacy today?"
    st.session_state.messages.append({"role": "assistant", "content": welcome})

for m in st.session_state.messages:
    with st.chat_message(m["role"]): st.markdown(m["content"])

# 5. Intake & Sync
if prompt := st.chat_input("How can we help?"):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"): st.markdown(prompt)

    response = st.session_state.chat_session.send_message(prompt)
    with st.chat_message("assistant"): st.markdown(response.text)
    st.session_state.messages.append({"role": "assistant", "content": response.text})

    # Trigger Sync when contact info is shared
    hist = " ".join([m["content"] for m in st.session_state.messages])
    if ("@" in hist or any(char.isdigit() for char in prompt)) and not st.session_state.lead_captured:
        extract = model.generate_content(f"Extract as pipes: Name | Inquiry Type | County | Contact | Summary from: {hist}").text
        if "|" in extract:
            try:
                p = extract.split("|")
                new_row = pd.DataFrame([{
                    "Date": datetime.now().strftime("%Y-%m-%d %H:%M"),
                    "Client Name": p[0].strip(),
                    "Inquiry Type": p[1].strip(),
                    "Texas County": p[2].strip(),
                    "Email/Phone": p[3].strip(),
                    "Summary": p[4].strip() if len(p) > 4 else "Legal Intake"
                }])
                # Sync to the new Duffley Sheet
                existing = conn.read(worksheet="Sheet1")
                updated = pd.concat([existing, new_row], ignore_index=True)
                conn.update(worksheet="Sheet1", data=updated)
                st.session_state.lead_captured = True
                st.toast("✅ Intake details secured for review.")
            except: pass
