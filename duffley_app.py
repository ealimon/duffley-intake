import streamlit as st
import google.generativeai as genai
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime

# 1. Page Config
st.set_page_config(page_title="Duffley Law PLLC", page_icon="⚖️")

# 2. Connection to Google Sheets
try:
    conn = st.connection("gsheets", type=GSheetsConnection, ttl=0)
except Exception as e:
    st.error(f"Spreadsheet Connection Failed: {e}")
    st.stop()

# 3. AI Setup - THE RESOLUTION POINT
genai.configure(api_key=st.secrets["GEMINI_API_KEY"])

# Use the 'models/gemini-1.5-flash' name which is the current "Global Address"
model = genai.GenerativeModel(
    model_name="models/gemini-1.5-flash",
    system_instruction="You are a professional intake assistant for Duffley Law PLLC. You are an AI, not an attorney. Collect Name, County, and Contact info."
)

# 4. Chat Interface
if "messages" not in st.session_state:
    st.session_state.messages = []
    st.session_state.chat_session = model.start_chat(history=[])

for m in st.session_state.messages:
    with st.chat_message(m["role"]):
        st.markdown(m["content"])

if prompt := st.chat_input("How can we help?"):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    try:
        response = st.session_state.chat_session.send_message(prompt)
        ai_msg = response.text
        with st.chat_message("assistant"):
            st.markdown(ai_msg)
        st.session_state.messages.append({"role": "assistant", "content": ai_msg})
        
        # Simple extraction logic
        if "@" in prompt or any(c.isdigit() for c in prompt):
            st.toast("Syncing with Google Sheets...")
            # (Sync logic goes here)
            
    except Exception as e:
        # This will tell us if it's a 404, 401 (Auth), or 429 (Rate Limit)
        st.error(f"Resolution Debug: {e}")
