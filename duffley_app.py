import streamlit as st
import google.generativeai as genai
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime

# 1. Page Configuration
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
    </style>
""", unsafe_allow_html=True)

st.markdown("""
    <div class="header-box">
        <h1 style="color: #1A365D; letter-spacing: 2px; margin-bottom: 0px;">DUFFLEY LAW PLLC</h1>
        <p style="color: #718096; font-style: italic;">Estate Planning & Probate Specialists</p>
    </div>
""", unsafe_allow_html=True)

# 2. Connection & AI Config with Safety Overrides
try:
    conn = st.connection("gsheets", type=GSheetsConnection, ttl=0)
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
    
    available_models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
    target_model = next((m for m in available_models if "flash" in m), available_models[0])
    
    # SAFETY FIX: Explicitly setting blocks to NONE for legal intake context
    safety_settings = [
        {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
        {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
        {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
        {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"},
    ]

    model = genai.GenerativeModel(
        model_name=target_model,
        safety_settings=safety_settings,
        system_instruction=(
            "Your name is Clara. You are the Professional Intake Assistant for Duffley Law PLLC. "
            "Identify as Clara and state you are an AI assistant, not an attorney. "
            "If a user is outside of Texas, explain the firm primarily handles Texas law "
            "but collect their info anyway for review. Collect: Name, County, Need, and Contact."
        )
    )
except Exception as e:
    st.error(f"Initialization Error: {e}")
    st.stop()

# 3. State Management
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

# 4. Interaction & Shielded Sync Logic
if prompt := st.chat_input("How can we help?"):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user", avatar="👤"):
        st.markdown(prompt)

    try:
        response = st.session_state.chat_session.send_message(prompt)
        
        # VALIDATION CHECK: Ensure response wasn't blocked by safety filters
        if response.candidates and len(response.candidates[0].content.parts) > 0:
            ai_msg = response.text
            with st.chat_message("assistant", avatar="⚖️"):
                st.markdown(ai_msg)
            st.session_state.messages.append({"role": "assistant", "content": ai_msg})
        else:
            error_fallback = "I apologize, but I am unable to process that specific request due to safety filters. Please try rephrasing your legal inquiry."
            st.warning(error_fallback)
            st.session_state.messages.append({"role": "assistant", "content": error_fallback})

        # Extraction Logic
        full_history = " ".join([m["content"] for m in st.session_state.messages])
        if ("@" in full_history or any(char.isdigit() for char in full_history)) and not st.session_state.lead_captured:
            extract_prompt = "Return ONLY data separated by pipes (|). No headers. Format: Name | Need | County | Contact | Summary. Context: " + full_history
            extract_resp = model.generate_content(extract_prompt)
            
            if extract_resp.candidates and len(extract_resp.candidates[0].content.parts) > 0:
                extract = extract_resp.text
                if "|" in extract:
                    p = [item.strip() for item in extract.split("|")]
                    if len(p) >= 4:
                        new_entry = pd.DataFrame([{
                            "Date": datetime.now().strftime("%Y-%m-%d %H:%M"),
                            "Client Name": p[0], "Inquiry Type": p[1],
                            "Texas County": p[2], "Email/Phone": p[3],
                            "Summary": p[4] if len(p) > 4 else "New Lead"
                        }])
                        existing_df = conn.read(worksheet="Sheet1", ttl=0)
                        updated_df = pd.concat([existing_df, new_entry], ignore_index=True)
                        conn.update(worksheet="Sheet1", data=updated_df)
                        st.session_state.lead_captured = True
                        st.toast("✅ Lead secured.")
                        
    except Exception as e:
        st.error(f"Sync Issue: {e}")

# 5. Footer
st.write("---")
st.markdown("<div style='text-align: center; color: #718096; font-size: 0.85rem;'><p>© 2026 Duffley Law PLLC. Clara AI Assistant.</p></div>", unsafe_allow_html=True)
