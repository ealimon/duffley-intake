import streamlit as st
import google.generativeai as genai
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime

# 1. Branding & UI
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

# 2. Clara's Brain (Dynamic Model Selection)
try:
    conn = st.connection("gsheets", type=GSheetsConnection, ttl=0)
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
    
    available_models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
    target_model = next((m for m in available_models if "flash" in m), available_models[0])
    
    model = genai.GenerativeModel(
        model_name=target_model,
        system_instruction=(
            "Your name is Clara. You are the Professional Intake Assistant for Duffley Law PLLC. "
            "MANDATORY: You must lead by identifying yourself as Clara and stating you are an AI assistant, not an attorney. "
            "Tone: Compassionate and professional. "
            "Goal: Collect Name, Texas County, Legal Need, and Contact info."
        )
    )
except Exception as e:
    st.error(f"Initialization Error: {e}")
    st.stop()

# 3. Session State
if "messages" not in st.session_state:
    st.session_state.messages = []
    st.session_state.chat_session = model.start_chat(history=[])
    st.session_state.lead_captured = False

for m in st.session_state.messages:
    avatar_choice = "⚖️" if m["role"] == "assistant" else "👤"
    with st.chat_message(m["role"], avatar=avatar_choice):
        st.markdown(m["content"])

if not st.session_state.messages:
    welcome = "Welcome to Duffley Law PLLC. My name is Clara. I am an AI assistant, not an attorney. How can I help you today?"
    st.session_state.messages.append({"role": "assistant", "content": welcome})
    with st.chat_message("assistant", avatar="⚖️"):
        st.markdown(welcome)

# 4. Interaction & FIXED Sync Logic
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
        # Trigger sync if contact info is found and lead hasn't been captured yet
        if ("@" in full_history or any(char.isdigit() for char in full_history)) and not st.session_state.lead_captured:
            extract_prompt = f"Return ONLY data separated by pipes: Name | Need | County | Contact | Summary. Context: {full_history}"
            extract = model.generate_content(extract_prompt).text
            
            if "|" in extract:
                p = [item.strip() for item in extract.split("|")]
                # Ensure we have enough parts
                if len(p) >= 4:
                    new_entry = {
                        "Date": datetime.now().strftime("%Y-%m-%d %H:%M"),
                        "Client Name": p[0],
                        "Inquiry Type": p[1],
                        "Texas County": p[2],
                        "Email/Phone": p[3],
                        "Summary": p[4] if len(p) > 4 else "New Lead"
                    }
                    
                    # Read existing data and append new row cleanly
                    existing_df = conn.read(worksheet="Sheet1")
                    updated_df = pd.concat([existing_df, pd.DataFrame([new_entry])], ignore_index=True)
                    conn.update(worksheet="Sheet1", data=updated_df)
                    
                    st.session_state.lead_captured = True
                    st.toast("✅ Lead information securely synced.")
                    
    except Exception as e:
        st.error(f"Sync Issue: {e}")

# 5. Footer
st.markdown("<br><br>---")
st.markdown("<p style='text-align: center; color: #718096; font-size: 0.85rem;'>© 2026 Duffley Law PLLC. Clara AI Assistant.</p>", unsafe_allow_html=True)
