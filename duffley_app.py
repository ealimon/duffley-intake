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
        
        /* Corporate Font Styling (Serif) */
        html, body, [class*="css"] {
            font-family: 'Georgia', serif; 
        }

        /* Chat Bubble Styling */
        [data-testid="stChatMessageAssistant"] {
            background-color: #F8F9FA;
            color: #1A365D;
            border-left: 5px solid #1A365D;
            border-radius: 0px 10px 10px 0px;
        }
        
        [data-testid="stChatMessageUser"] {
            background-color: #E2E8F0;
            color: #2D3748;
            border-radius: 10px;
        }

        .header-box {
            text-align: center;
            border-bottom: 2px solid #1A365D;
            padding-bottom: 20px;
            margin-bottom: 30px;
        }

        .stDeployButton {display:none;}
        div[data-testid="stStatusWidget"] {visibility: hidden;}
    </style>
""", unsafe_allow_html=True)

# 2. Professional Header
st.markdown("""
    <div class="header-box">
        <h1 style="color: #1A365D; letter-spacing: 2px; margin-bottom: 0px; font-size: 1.8rem;">DUFFLEY LAW PLLC</h1>
        <p style="color: #718096; font-style: italic; margin-top: 5px;">Estate Planning & Probate Specialists</p>
    </div>
""", unsafe_allow_html=True)

# 3. Connection & AI Config
try:
    conn = st.connection("gsheets", type=GSheetsConnection, ttl=0)
except Exception as e:
    st.error(f"Connection Error: {e}")
    st.stop()

# Configure API
genai.configure(api_key=st.secrets["GEMINI_API_KEY"])

# Safety Settings to prevent "Refusal" errors
safety_settings = {
    "HARM_CATEGORY_HARASSMENT": "BLOCK_NONE",
    "HARM_CATEGORY_HATE_SPEECH": "BLOCK_NONE",
    "HARM_CATEGORY_SEXUALLY_EXPLICIT": "BLOCK_NONE",
    "HARM_CATEGORY_DANGEROUS_CONTENT": "BLOCK_NONE",
}

model = genai.GenerativeModel(
    model_name="gemini-1.5-flash",
    system_instruction=(
        "You are a Professional Intake Assistant for Duffley Law PLLC. "
        "IMPORTANT: You are an AI assistant, NOT an attorney. You cannot give legal advice. "
        "Your only goal is to collect: 1. Name, 2. Texas County, 3. Legal Need (Will/Trust/Probate), "
        "and 4. Contact info. Be compassionate and professional."
    ),
    safety_settings=safety_settings
)

# 4. State Management
if "messages" not in st.session_state:
    st.session_state.messages = []
    st.session_state.chat_session = model.start_chat(history=[])
    st.session_state.lead_captured = False

# Display History
for m in st.session_state.messages:
    avatar_choice = "⚖️" if m["role"] == "assistant" else "👤"
    with st.chat_message(m["role"], avatar=avatar_choice):
        st.markdown(m["content"])

# Initial Welcome
if not st.session_state.messages:
    welcome = "Welcome to Duffley Law PLLC. I am an AI assistant, not an attorney, and this conversation does not create an attorney-client relationship. How can we help you protect your family's legacy today?"
    st.session_state.messages.append({"role": "assistant", "content": welcome})
    with st.chat_message("assistant", avatar="⚖️"):
        st.markdown(welcome)

# 5. Intake & Data Sync
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

        # Sync Logic (Trigger on contact info)
        full_history = " ".join([m["content"] for m in st.session_state.messages])
        if ("@" in full_history or any(char.isdigit() for char in full_history)) and not st.session_state.lead_captured:
            extract = model.generate_content(f"Extract as pipes: Name | Need | County | Contact | Summary from: {full_history}").text
            if "|" in extract:
                try:
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
                    st.toast("✅ Information secured for review.")
                except:
                    pass
    except Exception as e:
        # RED BOX DEBUG: Tells us exactly why it failed
        st.error(f"DEBUG ERROR: {e}")

# 6. Legal Footer
st.markdown("<br><br>", unsafe_allow_html=True)
st.markdown("---")
st.markdown(
    """
    <div style="text-align: center; color: #718096; font-size: 0.8rem; padding: 10px;">
        <p><strong>LEGAL DISCLAIMER</strong></p>
        <p>This AI Assistant is for informational purposes only and does not constitute legal advice or the 
        formation of an attorney-client relationship.</p>
        <p>© 2026 Duffley Law PLLC. All Rights Reserved.</p>
    </div>
    """, 
    unsafe_allow_html=True
)
