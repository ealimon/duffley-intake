import streamlit as st
import google.generativeai as genai
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime

# 1. UI Branding - Duffley Law PLLC Corporate Identity
st.set_page_config(
    page_title="Duffley Law PLLC | Client Portal",
    page_icon="⚖️",
    layout="centered"
)

# Custom CSS for the "Duffley Blue" Aesthetic
st.markdown("""
    <style>
        #MainMenu, footer, header {visibility: hidden;}
        div[data-testid="stToolbar"] {display: none;}
        .stApp {background-color: #ffffff;}
        html, body, [class*="css"] { font-family: 'Georgia', serif; }
        [data-testid="stChatMessageAssistant"] {
            background-color: #F8F9FA;
            color: #1A365D;
            border-left: 5px solid #1A365D;
            border-radius: 0px 10px 10px 0px;
        }
        .header-box {
            text-align: center;
            border-bottom: 2px solid #1A365D;
            padding-bottom: 20px;
            margin-bottom: 30px;
        }
    </style>
""", unsafe_allow_html=True)

# 2. Professional Header
st.markdown("""
    <div class="header-box">
        <h1 style="color: #1A365D; letter-spacing: 2px; margin-bottom: 0px;">DUFFLEY LAW PLLC</h1>
        <p style="color: #718096; font-style: italic;">Estate Planning & Probate Specialists</p>
    </div>
""", unsafe_allow_html=True)

# 3. Connection & API Config
try:
    conn = st.connection("gsheets", type=GSheetsConnection, ttl=0)
except Exception:
    st.error("Sheet Connection Error.")
    st.stop()

# 4. API & Model Setup
genai.configure(api_key=st.secrets["GEMINI_API_KEY"])

# THE FIX: Explicitly using the full path 'models/gemini-1.5-flash'
# This is the address the 404 error is asking for.
model = genai.GenerativeModel(
    model_name="models/gemini-1.5-flash", 
    system_instruction=(
        "You are a Professional Intake Assistant for Duffley Law PLLC. "
        "MANDATORY: You are an AI, not an attorney. You cannot give legal advice. "
        "Goal: Compassionately collect Name, Texas County, Need (Will/Trust/Probate), and Contact Info."
    ),
    safety_settings={
        "HARM_CATEGORY_HARASSMENT": "BLOCK_NONE",
        "HARM_CATEGORY_HATE_SPEECH": "BLOCK_NONE",
        "HARM_CATEGORY_SEXUALLY_EXPLICIT": "BLOCK_NONE",
        "HARM_CATEGORY_DANGEROUS_CONTENT": "BLOCK_NONE",
    }
)

# 5. State Management
if "messages" not in st.session_state:
    st.session_state.messages = []
    st.session_state.chat_session = model.start_chat(history=[])
    st.session_state.lead_captured = False

# Display History with Scale Avatar
for m in st.session_state.messages:
    avatar_icon = "⚖️" if m["role"] == "assistant" else "👤"
    with st.chat_message(m["role"], avatar=avatar_icon):
        st.markdown(m["content"])

# Initial Welcome
if not st.session_state.messages:
    welcome = "Welcome to Duffley Law PLLC. I am an AI assistant, not an attorney, and this conversation does not create an attorney-client relationship. How can we help you protect your family's legacy today?"
    st.session_state.messages.append({"role": "assistant", "content": welcome})
    with st.chat_message("assistant", avatar="⚖️"):
        st.markdown(welcome)

# 6. Chat & Sync
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

        # Logic to save to Google Sheet
        full_history = " ".join([m["content"] for m in st.session_state.messages])
        if ("@" in full_history or any(char.isdigit() for char in full_history)) and not st.session_state.lead_captured:
            extract = model.generate_content(f"Extract as pipes: Name | Need | County | Contact | Summary from: {full_history}").text
            if "|" in extract:
                p = extract.split("|")
                new_row = pd.DataFrame([{
                    "Date": datetime.now().strftime("%Y-%m-%d %H:%M"),
                    "Client Name": p[0].strip(),
                    "Inquiry Type": p[1].strip(),
                    "Texas County": p[2].strip(),
                    "Email/Phone": p[3].strip(),
                    "Summary": p[4].strip() if len(p) > 4 else "New Lead"
                }])
                existing = conn.read(worksheet="Sheet1")
                updated = pd.concat([existing, new_row], ignore_index=True)
                conn.update(worksheet="Sheet1", data=updated)
                st.session_state.lead_captured = True
                st.toast("✅ Lead secured.")
    except Exception as e:
        # This will now show the SPECIFIC error if it fails again
        st.error(f"System busy. Details: {e}")

# 7. Legal Footer
st.markdown("---")
st.markdown("<p style='text-align: center; color: grey; font-size: 0.8rem;'>© 2026 Duffley Law PLLC. This AI does not provide legal advice.</p>", unsafe_allow_html=True)
