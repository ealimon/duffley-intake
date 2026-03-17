import streamlit as st
import google.generativeai as genai
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime

# 1. Page Configuration & Branding
st.set_page_config(page_title="Duffley Law PLLC", page_icon="⚖️", layout="centered")

st.markdown("""
    <style>
        #MainMenu, footer, header {visibility: hidden;}
        .stApp {background-color: #ffffff;}
        html, body, [class*="css"] { font-family: 'Georgia', serif; }
        .header-box { text-align: center; border-bottom: 2px solid #1A365D; padding-bottom: 20px; margin-bottom: 30px; }
    </style>
""", unsafe_allow_html=True)

st.markdown("""
    <div class="header-box">
        <h1 style="color: #1A365D; letter-spacing: 2px; margin-bottom: 0px;">DUFFLEY LAW PLLC</h1>
        <p style="color: #718096; font-style: italic;">Estate Planning & Probate Specialists</p>
    </div>
""", unsafe_allow_html=True)

# 2. Secure Connections
try:
    conn = st.connection("gsheets", type=GSheetsConnection, ttl=0)
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
    
    # RESOLUTION: Using the most stable model string for current API versions
    model = genai.GenerativeModel(
        model_name="gemini-1.5-flash", 
        system_instruction="You are a professional intake assistant for Duffley Law PLLC. You are an AI, not an attorney. Collect Name, County, and Contact info. Do not give legal advice."
    )
except Exception as e:
    st.error(f"Configuration Error: {e}")
    st.stop()

# 3. Chat State Management
if "messages" not in st.session_state:
    st.session_state.messages = []
    st.session_state.chat_session = model.start_chat(history=[])
    st.session_state.lead_captured = False

# Display Chat History
for m in st.session_state.messages:
    with st.chat_message(m["role"], avatar="⚖️" if m["role"] == "assistant" else "👤"):
        st.markdown(m["content"])

# Initial Welcome
if not st.session_state.messages:
    welcome = "Welcome to Duffley Law PLLC. I am an AI assistant, not an attorney, and this conversation does not create an attorney-client relationship. How can we help you protect your family's legacy today?"
    st.session_state.messages.append({"role": "assistant", "content": welcome})
    with st.chat_message("assistant", avatar="⚖️"):
        st.markdown(welcome)

# 4. User Interaction & Data Sync
if prompt := st.chat_input("How can we help?"):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user", avatar="👤"):
        st.markdown(prompt)

    try:
        response = st.session_state.chat_session.send_message(prompt)
        ai_msg = response.text
        with st.chat_message("assistant", avatar="⚖️"):
            st.markdown(ai_msg)
        st.session_state.messages.append({"role": "assistant", "content": ai_msg})

        # Syncing Logic (Fires when contact info is provided)
        full_history = " ".join([m["content"] for m in st.session_state.messages])
        if ("@" in full_history or any(char.isdigit() for char in full_history)) and not st.session_state.lead_captured:
            extract = model.generate_content(f"Extract as pipes: Name | Need | County | Contact | Summary from: {full_history}").text
            if "|" in extract:
                p = extract.split("|")
                new_row = pd.DataFrame([{
                    "Date": datetime.now().strftime("%Y-%m-%d %H:%M"),
                    "Client Name": p[0].strip() if len(p) > 0 else "Unknown",
                    "Inquiry Type": p[1].strip() if len(p) > 1 else "Unknown",
                    "Texas County": p[2].strip() if len(p) > 2 else "Unknown",
                    "Email/Phone": p[3].strip() if len(p) > 3 else "Unknown",
                    "Summary": p[4].strip() if len(p) > 4 else "New Lead"
                }])
                existing = conn.read(worksheet="Sheet1")
                updated = pd.concat([existing, new_row], ignore_index=True)
                conn.update(worksheet="Sheet1", data=updated)
                st.session_state.lead_captured = True
                st.toast("✅ Lead information secured.")
    except Exception as e:
        st.error(f"Connection Issue: {e}")

# 5. Permanent Footer
st.markdown("---")
st.markdown("<p style='text-align: center; color: grey; font-size: 0.8rem;'>© 2026 Duffley Law PLLC. AI Assistant (Non-Attorney).</p>", unsafe_allow_html=True)
