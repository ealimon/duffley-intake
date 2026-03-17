import streamlit as st
import google.generativeai as genai
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime

# 1. UI Branding & Professional Legal Styling
st.set_page_config(
    page_title="Duffley Law PLLC | Client Intake",
    page_icon="⚖️",
    layout="centered"
)

st.markdown("""
    <style>
        #MainMenu, footer, header {visibility: hidden;}
        div[data-testid="stToolbar"] {display: none;}
        .stApp {background-color: #fcfcfc;}
        
        /* Message Bubbles */
        .stChatMessage {
            border-radius: 10px;
            margin-bottom: 1rem;
        }
        
        /* Assistant (Duffley Law) Styling */
        [data-testid="stChatMessageAssistant"] {
            background-color: #f1f3f4;
            color: #3c4043;
            border: 1px solid #dadce0;
        }
        
        /* User Styling */
        [data-testid="stChatMessageUser"] {
            background-color: #e8f0fe;
            color: #1a73e8;
            border: 1px solid #d2e3fc;
        }
        
        /* Input Field */
        .stChatInputContainer {
            border-top: 1px solid #dadce0;
            background-color: white;
        }
        
        /* Hide Streamlit status elements */
        .stDeployButton {display:none;}
        div[data-testid="stStatusWidget"] {visibility: hidden;}
    </style>
""", unsafe_allow_html=True)

# 2. Header Section
st.markdown("# 🏛️ Client Intake Portal")
st.markdown("### Duffley Law PLLC | Estate Planning & Probate")
st.write("---")

# 3. Connection Setup
try:
    conn = st.connection("gsheets", type=GSheetsConnection, ttl=0)
except Exception as e:
    st.error("Technical setup incomplete. Please contact Limon Media support.")
    st.stop()

# 4. Gemini Configuration
genai.configure(api_key=st.secrets["GEMINI_API_KEY"])

model = genai.GenerativeModel(
    model_name="gemini-3.1-flash-lite-preview",
    system_instruction=(
        "You are the Professional Intake Assistant for Duffley Law PLLC, a Texas Estate Planning firm. "
        "Your tone is empathetic, calm, and highly professional. "
        "MANDATORY OPENING: You must state in your very first message: 'I am an AI assistant, not an attorney. Our conversation does not create an attorney-client relationship.' "
        "YOUR GOAL: Efficiently collect: 1. Full Name, 2. Texas County of residence, 3. Need (Will, Trust, or Probate), "
        "4. Brief family/asset summary, 5. Email or Phone. "
        "Do not offer legal advice. If asked, refer them to the attorney during the consultation."
    )
)

# 5. Session State for Chat
if "messages" not in st.session_state:
    st.session_state.messages = []
    st.session_state.chat_session = model.start_chat(history=[])
    st.session_state.lead_captured = False

# Display Chat History
for m in st.session_state.messages:
    with st.chat_message(m["role"]):
        st.markdown(m["content"])

# Initial Welcome Message
if not st.session_state.messages:
    welcome = "Welcome to Duffley Law PLLC. I am an AI assistant, not an attorney, and this chat does not create an attorney-client relationship. How can we help you protect your legacy today?"
    st.session_state.messages.append({"role": "assistant", "content": welcome})
    with st.chat_message("assistant"):
        st.markdown(welcome)

# 6. Chat Input & Data Sync
if prompt := st.chat_input("How can we help you?"):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    try:
        response = st.session_state.chat_session.send_message(prompt)
        ai_msg = response.text
        
        with st.chat_message("assistant"):
            st.markdown(ai_msg)
        st.session_state.messages.append({"role": "assistant", "content": ai_msg})

        # Sync Trigger Logic
        full_history = " ".join([m["content"] for m in st.session_state.messages])
        
        if ("@" in full_history or any(char.isdigit() for char in full_history)) and not st.session_state.lead_captured:
            # Data Extraction
            extract_prompt = f"Extract as pipes: Name | Inquiry Type | County | Contact | Summary from: {full_history}"
            extraction = model.generate_content(extract_prompt).text
            
            if "|" in extraction:
                try:
                    p = extraction.split("|")
                    
                    new_row = pd.DataFrame([{
                        "Date": datetime.now().strftime("%Y-%m-%d %H:%M"),
                        "Client Name": p[0].strip() if len(p) > 0 else "Unknown",
                        "Inquiry Type": p[1].strip() if len(p) > 1 else "Needs review",
                        "Texas County": p[2].strip() if len(p) > 2 else "Check chat",
                        "Email/Phone": p[3].strip() if len(p) > 3 else "Check chat",
                        "Summary": p[4].strip() if len(p) > 4 else "Legal Intake"
                    }])
                    
                    # Update Google Sheet
                    existing_data = conn.read(worksheet="Sheet1")
                    updated_data = pd.concat([existing_data, new_row], ignore_index=True)
                    conn.update(worksheet="Sheet1", data=updated_data)
                    
                    st.session_state.lead_captured = True
                    st.toast("✅ Intake details secured for attorney review.")
                    
                except Exception as sheet_err:
                    print(f"Sync Error: {sheet_err}")

    except Exception as e:
        st.error("Service momentarily unavailable. Please try your message again.")
