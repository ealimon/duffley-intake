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
except Exception:
    st.error("Connection failed. Please refresh the page.")
    st.stop()

genai.configure(api_key=st.secrets["GEMINI_API_KEY"])

model = genai.GenerativeModel(
    model_name="gemini-1.5-flash",
    system_instruction=(
        "You are the Professional Intake Assistant for Duffley Law PLLC. "
        "Tone: Compassionate, patient, and precise. "
        "MANDATORY OPENING: You must state in your very first message: 'I am an AI assistant, not an attorney. Our conversation does not create an attorney-client relationship.' "
        "PROCESS: 1. Greet with kindness. 2. Collect Full Name and Texas County. "
        "3. Identify the legal need (Will, Trust, or Probate). "
        "4. Ask about family/assets. 5. Secure Email or Phone number."
    )
)

# 4. State Management
if "messages" not in st.session_state:
    st.session_state.messages = []
    st.session_state.chat_session = model.start_chat(history=[])
    st.session_state.lead_captured = False

# Display History with Scale (⚖️) and User (👤) Avatars
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

        # Sync Logic
        full_history = " ".join([m["content"] for m in st.session_state.messages])
        
        if ("@" in full_history or any(char.isdigit() for char in full_history)) and not st.session_state.lead_captured:
            extract_prompt = f"Extract as pipes: Name | Inquiry Type | County | Contact | Summary from: {full_history}"
            extract = model.generate_content(extract_prompt).text
            
            if "|" in extract:
                try:
                    p = extract.split("|")
                    new_row = pd.DataFrame([{
                        "Date": datetime.now().strftime("%Y-%m-%d %H:%M"),
                        "Client Name": p[0].strip() if len(p) > 0 else "Unknown",
                        "Inquiry Type": p[1].strip() if len(p) > 1 else "Needs review",
                        "Texas County": p[2].strip() if len(p) > 2 else "Check chat",
                        "Email/Phone": p[3].strip() if len(p) > 3 else "Check chat",
                        "Summary": p[4].strip() if len(p) > 4 else "Legal Lead"
                    }])
                    
                    existing = conn.read(worksheet="Sheet1")
                    updated = pd.concat([existing, new_row], ignore_index=True)
                    conn.update(worksheet="Sheet1", data=updated)
                    
                    st.session_state.lead_captured = True
                    st.toast("✅ Information secured for review.")
                except:
                    pass
    except:
        st.error("System temporarily busy. Please try again.")

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
