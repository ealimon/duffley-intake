import streamlit as st
import google.generativeai as genai
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime

# 1. UI Branding & High-End Legal Styling
st.set_page_config(
    page_title="Duffley Law PLLC | Client Intake",
    page_icon="⚖️",
    layout="centered"
)

# Custom CSS for a White-Label, Prestige Look
st.markdown("""
    <style>
        #MainMenu, footer, header {visibility: hidden;}
        div[data-testid="stToolbar"] {display: none;}
        .stApp {background-color: #ffffff;}
        
        /* Professional Font and Spacing */
        html, body, [class*="css"] {
            font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif;
        }

        /* Message Bubbles - Clean & Subtle */
        [data-testid="stChatMessageAssistant"] {
            background-color: #f8f9fa;
            color: #202124;
            border: 1px solid #e8eaed;
            border-radius: 15px;
        }
        
        [data-testid="stChatMessageUser"] {
            background-color: #f1f3f4;
            color: #202124;
            border-radius: 15px;
        }

        /* Custom Header Styling */
        .legal-header {
            text-align: center;
            padding-bottom: 20px;
        }
        
        /* Hide Streamlit elements */
        .stDeployButton {display:none;}
        div[data-testid="stStatusWidget"] {visibility: hidden;}
    </style>
""", unsafe_allow_html=True)

# 2. Baked-in Professional SVG Logo (Shield & Pillars)
# This replaces the orange robot with a Navy Blue Legal Icon
st.markdown("""
    <div style="text-align: center;">
        <svg width="80" height="80" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
            <path d="M12 1L3 5V11C3 16.55 6.84 21.74 12 23C17.16 21.74 21 16.55 21 11V5L12 1Z" fill="#1A365D"/>
            <path d="M9 14H10V10H9V14ZM14 14H15V10H14V14ZM11.5 14H12.5V10H11.5V14ZM8 16H16V15H8V16ZM8 9H16V8H8V9Z" fill="white"/>
        </svg>
        <h2 style="color: #1A365D; margin-top: 10px; font-weight: 700;">DUFFLEY LAW PLLC</h2>
        <p style="color: #4A5568; font-size: 0.9rem; margin-top: -15px;">Secure Client Intake Portal</p>
    </div>
""", unsafe_allow_html=True)

st.write("---")

# 3. Connection Setup
try:
    conn = st.connection("gsheets", type=GSheetsConnection, ttl=0)
except Exception as e:
    st.error("Connection unavailable. Please contact system administrator.")
    st.stop()

# 4. Gemini Configuration
genai.configure(api_key=st.secrets["GEMINI_API_KEY"])

model = genai.GenerativeModel(
    model_name="gemini-3.1-flash-lite-preview",
    system_instruction=(
        "You are the Professional Intake Assistant for Duffley Law PLLC, a Texas Estate Planning firm. "
        "Your tone is empathetic, composed, and highly professional. "
        "MANDATORY OPENING: You must state: 'I am an AI assistant, not an attorney. Our conversation does not create an attorney-client relationship.' "
        "GOAL: Collect 1. Full Name, 2. Texas County, 3. Need (Will, Trust, or Probate), 4. Brief Family/Asset Summary, 5. Contact Info. "
        "Do not offer legal advice."
    )
)

# 5. Session State
if "messages" not in st.session_state:
    st.session_state.messages = []
    st.session_state.chat_session = model.start_chat(history=[])
    st.session_state.lead_captured = False

# Display History
for m in st.session_state.messages:
    with st.chat_message(m["role"]):
        st.markdown(m["content"])

# Welcome Message
if not st.session_state.messages:
    welcome = "Welcome to Duffley Law PLLC. I am an AI assistant, not an attorney, and this conversation does not create an attorney-client relationship. How can we help you protect your legacy today?"
    st.session_state.messages.append({"role": "assistant", "content": welcome})
    with st.chat_message("assistant"):
        st.markdown(welcome)

# 6. Input & Data Sync
if prompt := st.chat_input("Message the assistant..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    try:
        response = st.session_state.chat_session.send_message(prompt)
        ai_msg = response.text
        
        with st.chat_message("assistant"):
            st.markdown(ai_msg)
        st.session_state.messages.append({"role": "assistant", "content": ai_msg})

        # Trigger Sync Logic
        full_history = " ".join([m["content"] for m in st.session_state.messages])
        
        if ("@" in full_history or any(char.isdigit() for char in full_history)) and not st.session_state.lead_captured:
            extract = model.generate_content(f"Extract as pipes: Name | Inquiry Type | County | Contact | Summary from: {full_history}").text
            
            if "|" in extract:
                try:
                    p = extract.split("|")
                    new_row = pd.DataFrame([{
                        "Date": datetime.now().strftime("%Y-%m-%d %H:%M"),
                        "Client Name": p[0].strip(),
                        "Inquiry Type": p[1].strip(),
                        "Texas County": p[2].strip(),
                        "Email/Phone": p[3].strip(),
                        "Summary": p[4].strip() if len(p) > 4 else "Legal Inquiry"
                    }])
                    
                    # Update Google Sheet
                    existing_data = conn.read(worksheet="Sheet1")
                    updated_data = pd.concat([existing_data, new_row], ignore_index=True)
                    conn.update(worksheet="Sheet1", data=updated_data)
                    
                    st.session_state.lead_captured = True
                    st.toast("✅ Your intake details have been secured for attorney review.")
                except:
                    pass
    except:
        st.error("Service momentarily unavailable.")
