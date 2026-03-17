import streamlit as st
import google.generativeai as genai
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime

# 1. Corporate Branding
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

# 2. Dynamic Model Selection (The "Bypass" Logic)
try:
    conn = st.connection("gsheets", type=GSheetsConnection, ttl=0)
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
    
    # We dynamically find a working model instead of hardcoding a name
    available_models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
    # Filter for flash models specifically
    target_model = next((m for m in available_models if "flash" in m), available_models[0])
    
    model = genai.GenerativeModel(
        model_name=target_model,
        system_instruction=(
            "You are a professional intake assistant for Duffley Law PLLC. "
            "You are an AI, not an attorney. Do not give legal advice. "
            "Collect: Name, Texas County, and Contact info."
        )
    )
except Exception as e:
    st.error(f"System Initialization Error: {e}")
    st.stop()

# 3. State Management
if "messages" not in st.session_state:
    st.session_state.messages = []
    st.session_state.chat_session = model.start_chat(history=[])
    st.session_state.lead_captured = False

for m in st.session_state.messages:
    with st.chat_message(m["role"], avatar="⚖️" if m["role"] == "assistant" else "👤"):
        st.markdown(m["content"])

if not st.session_state.messages:
    welcome = "Welcome to Duffley Law. I am an AI assistant, not an attorney. How can we help you today?"
    st.session_state.messages.append({"role": "assistant", "content": welcome})
    with st.chat_message("assistant", avatar="⚖️"):
        st.markdown(welcome)

# 4. Interaction
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

        # Capture logic
        full_history = " ".join([m["content"] for m in st.session_state.messages])
        if ("@" in full_history or any(char.isdigit() for char in full_history)) and not st.session_state.lead_captured:
            extract = model.generate_content(f"Extract: Name|Need|County|Contact|Summary from: {full_history}").text
            if "|" in extract:
                p = extract.split("|")
                new_row = pd.DataFrame([{
                    "Date": datetime.now().strftime("%Y-%m-%d %H:%M"),
                    "Client Name": p[0].strip() if len(p) > 0 else "N/A",
                    "Inquiry Type": p[1].strip() if len(p) > 1 else "N/A",
                    "Texas County": p[2].strip() if len(p) > 2 else "N/A",
                    "Email/Phone": p[3].strip() if len(p) > 3 else "N/A",
                    "Summary": p[4].strip() if len(p) > 4 else "New Lead"
                }])
                existing = conn.read(worksheet="Sheet1")
                updated = pd.concat([existing, new_row], ignore_index=True)
                conn.update(worksheet="Sheet1", data=updated)
                st.session_state.lead_captured = True
                st.toast("✅ Information secured.")
    except Exception as e:
        st.error(f"Connection Error: {e}")

st.markdown("---")
st.markdown("<p style='text-align: center; font-size: 0.8rem;'>© 2026 Duffley Law PLLC.</p>", unsafe_allow_html=True)
