import streamlit as st
import google.generativeai as genai
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime

# 1. Branding & UI (The "Duffley" Navy & White)
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

# 2. Connection & Direct Model Configuration
try:
    conn = st.connection("gsheets", type=GSheetsConnection, ttl=0)
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
    
    # THE RESOLUTION: Using the most widely accepted standard alias
    model = genai.GenerativeModel(
        model_name="gemini-1.5-flash", 
        system_instruction=(
            "You are a professional intake assistant for Duffley Law PLLC. "
            "STRICT RULE: You are an AI, not an attorney. You cannot give legal advice. "
            "If asked for legal advice, explain that you are an AI assistant and only an attorney "
            "can answer that. Your goal is to collect: Name, Texas County, and Contact info."
        )
    )
except Exception as e:
    st.error(f"Setup Error: {e}")
    st.stop()

# 3. State Management
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

# 4. Interaction & Data Sync
if prompt := st.chat_input("How can we help?"):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user", avatar="👤"):
        st.markdown(prompt)

    try:
        # Use simple generation to bypass 'Handshake' errors
        response = st.session_state.chat_session.send_message(prompt)
        ai_msg = response.text
        
        with st.chat_message("assistant", avatar="⚖️"):
            st.markdown(ai_msg)
        st.session_state.messages.append({"role": "assistant", "content": ai_msg})

        # Data Extraction logic
        full_history = " ".join([m["content"] for m in st.session_state.messages])
        if ("@" in full_history or any(char.isdigit() for char in full_history)) and not st.session_state.lead_captured:
            # We use a separate generation for extraction to keep the chat stable
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
                st.toast("✅ Information secured for review.")
    except Exception as e:
        # Final connection check
        st.error(f"Final Connection Check: {e}")

# 5. Footer
st.markdown("---")
st.markdown("<p style='text-align: center; color: #718096; font-size: 0.8rem;'>© 2026 Duffley Law PLLC. Estate Planning & Probate Specialists.</p>", unsafe_allow_html=True)
