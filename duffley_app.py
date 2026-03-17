import streamlit as st
import google.generativeai as genai
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime

# 1. Branding & UI Setup
st.set_page_config(page_title="Duffley Law PLLC | Portal", page_icon="⚖️", layout="centered")

st.markdown("""
    <style>
        #MainMenu, footer, header {visibility: hidden;}
        .stApp {background-color: #ffffff;}
        html, body, [class*="css"] { font-family: 'Georgia', serif; }
        [data-testid="stChatMessageAssistant"] {
            background-color: #F8F9FA;
            color: #1A365D;
            border-left: 5px solid #1A365D;
            border-radius: 0px 10px 10px 0px;
        }
        .header-box { text-align: center; border-bottom: 2px solid #1A365D; padding-bottom: 20px; margin-bottom: 30px; }
        .stDeployButton {display:none;}
    </style>
""", unsafe_allow_html=True)

st.markdown("""
    <div class="header-box">
        <h1 style="color: #1A365D; letter-spacing: 2px; margin-bottom: 0px;">DUFFLEY LAW PLLC</h1>
        <p style="color: #718096; font-style: italic;">Estate Planning & Probate Specialists</p>
    </div>
""", unsafe_allow_html=True)

# 2. Connection & Clara's Brain
try:
    conn = st.connection("gsheets", type=GSheetsConnection, ttl=0)
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
    
    # Using the Dynamic search that fixed our 404
    available_models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
    target_model = next((m for m in available_models if "flash" in m), available_models[0])
    
    model = genai.GenerativeModel(
        model_name=target_model,
        system_instruction=(
            "Your name is Clara. You are the Professional Intake Assistant for Duffley Law PLLC. "
            "MANDATORY: You must lead by identifying yourself as Clara and stating you are an AI assistant, not an attorney. "
            "Tone: Compassionate, patient, and professional. "
            "Goal: Collect Name, Texas County, Legal Need, and Contact info for the attorney to review."
        )
    )
except Exception as error_msg:
    st.error(f"Initialization Error: {error_msg}")
    st.stop()

# 3. Chat Session & State
if "messages" not in st.session_state:
    st.session_state.messages = []
    st.session_state.chat_session = model.start_chat(history=[])
    st.session_state.lead_captured = False

for m in st.session_state.messages:
    avatar_choice = "⚖️" if m["role"] == "assistant" else "👤"
    with st.chat_message(m["role"], avatar=avatar_choice):
        st.markdown(m["content"])

if not st.session_state.messages:
    welcome = "Welcome to Duffley Law PLLC. My name is Clara. I am an AI assistant, not an attorney, and this chat does not create an attorney-client relationship. How can I help you today?"
    st.session_state.messages.append({"role": "assistant", "content": welcome})
    with st.chat_message("assistant", avatar="⚖️"):
        st.markdown(welcome)

# 4. Interaction & GSheets Sync
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

        # Extraction Logic
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
                st.toast("✅ Information secured for attorney review.")
    except Exception as e:
        st.error(f"Connection Issue: {e}")

# 5. Professional Footer
st.markdown("<br><br>", unsafe_allow_html=True)
st.markdown("---")
st.markdown(
    """
    <div style="text-align: center; color: #718096; font-size: 0.85rem; padding: 20px;">
        <p><strong>LEGAL DISCLAIMER</strong></p>
        <p>This AI Assistant is for informational and intake purposes only. 
        It does not constitute legal advice or form an attorney-client relationship.</p>
        <p>© 2026 Duffley Law PLLC. All Rights Reserved.</p>
    </div>
    """, 
    unsafe_allow_html=True
)
