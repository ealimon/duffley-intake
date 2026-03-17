import streamlit as st
import google.generativeai as genai
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime

# 1. UI Branding & White-Label Styling (NEW)
st.set_page_config(
    page_title="Duffley Law PLLC | Client Intake",
    page_icon="⚖️",  # You could replace this with a base64 encoded version of image_0.png if desired
    layout="centered"
)

# Custom Styling for Legal Profession
st.markdown(f"""
    <style>
        #MainMenu, footer, header {{visibility: hidden;}}
        div[data-testid="stToolbar"] {{display: none;}}
        .stApp {{background-color: #fcfcfc;}} /* Light, clean background */
        
        /* Message Area Styling */
        .stChatMessage {{
            border-radius: 10px;
            margin-bottom: 1rem;
        }}
        
        /* Assistant Message Branding (Composed Grey) */
        [data-testid="stChatMessageAssistant"] {{
            background-color: #f1f3f4;
            color: #3c4043;
            border: 1px solid #dadce0;
        }}
        
        /* User Message Styling (Trustworthy Blue) */
        [data-testid="stChatMessageUser"] {{
            background-color: #e8f0fe;
            color: #1a73e8;
            border: 1px solid #d2e3fc;
        }}
        
        /* Input Area Styling */
        .stChatInputContainer {{
            border-top: 2px solid #dadce0;
            background-color: white;
            padding: 1rem;
        }}
        
        /* Hide the Streamlit 'built with' red line and balloon */
        .stDeployButton {{display:none;}}
        div[data-testid="stStatusWidget"] {{visibility: hidden;}}

    </style>
""", unsafe_allow_html=True)

# Add the Black Pillars logo at the top (NEW)
st.image("image_0.png", width=80) 
st.markdown("## Client Intake Portal")
st.markdown("Duffley Law PLLC | Estate Planning & Probate")
st.write("---")


# 2. Connection (Uses existing secrets)
try:
    # ttl=0 ensures we always get fresh data and bypass any old 'MAX' cache
    conn = st.connection("gsheets", type=GSheetsConnection, ttl=0)
except Exception as e:
    st.error("Technical setup incomplete. Please contact Limon Media support.")
    st.stop()


# 3. Gemini Configuration (Updated for Legal Brain)
genai.configure(api_key=st.secrets["GEMINI_API_KEY"])

model = genai.GenerativeModel(
    model_name="gemini-3.1-flash-lite-preview",
    system_instruction=(
        "You are the Professional Intake Assistant for Duffley Law PLLC, an Estate Planning and Probate law firm in Texas. "
        "Your tone is composed, empathetic, calm, and highly professional. You must never be overly enthusiastic or informal. "
        "MANDATORY OPENING: You must state in your very first message: 'I am an AI assistant, not an attorney. Our conversation does not create an attorney-client relationship.' "
        "YOUR GOAL: Qualify the lead by asking (one at a time): "
        "1. Their Full Name. "
        "2. Which Texas County they reside in (or where the deceased resided). "
        "3. A brief summary of what they need (Will, Trust, Probate help, or specific question). "
        "4. A brief summary of their family situation or assets (e.g., 'married with two minor children' or 'owning a home in Houston'). "
        "5. The best email or phone number to reach them for a formal consultation."
    )
)


# 4. State & Chat Logic
if "messages" not in st.session_state:
    st.session_state.messages = []
    st.session_state.chat_session = model.start_chat(history=[])
    st.session_state.lead_captured = False

# Display Chat History
for m in st.session_state.messages:
    with st.chat_message(m["role"]):
        st.markdown(m["content"])

# Initial Welcome (Updated with text from image_4.png)
if not st.session_state.messages:
    welcome = "Welcome to Duffley Law PLLC. I am an AI assistant, not an attorney, and this chat does not create an attorney-client relationship. How can we help you protect your legacy today?"
    st.session_state.messages.append({"role": "assistant", "content": welcome})
    with st.chat_message("assistant"):
        st.markdown(welcome)


# 5. Input, AI Response, & Reliable Sync
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

        # --- SYNC TRIGGER ---
        # Look for contact info (email or digits) anywhere in the history.
        full_history = " ".join([m["content"] for m in st.session_state.messages])
        
        if ("@" in full_history or any(char.isdigit() for char in full_history)) and not st.session_state.lead_captured:
            # Simple Extraction call
            extract_prompt = f"Extract as pipes: Name | Inquiry Type | County | Contact | Summary from: {full_history}"
            extraction = model.generate_content(extract_prompt).text
            
            if "|" in extraction:
                try:
                    p = extraction.split("|")
                    
                    # Ensure Row 1 of your 'Sheet1' is: Date, Client Name, Inquiry Type, Texas County, Email/Phone, Summary
                    new_row = pd.DataFrame([{
                        "Date": datetime.now().strftime("%Y-%m-%d %H:%M"),
                        "Client Name": p[0].strip() if len(p) > 0 else "Unknown",
                        "Inquiry Type": p[1].strip() if len(p) > 1 else "Needs review",
                        "Texas County": p[2].strip() if len(p) > 2 else "Check chat",
                        "Email/Phone": p[3].strip() if len(p) > 3 else "Check chat",
                        "Summary": p[4].strip() if len(p) > 4 else "Client Intake details"
                    }])
                    
                    # The reliable 'Read then Update' method
                    existing_data = conn.read(worksheet="Sheet1")
                    updated_data = pd.concat([existing_data, new_row], ignore_index=True)
                    conn.update(worksheet="Sheet1", data=updated_data)
                    
                    st.session_state.lead_captured = True
                    # A more formal success toast
                    st.toast("✅ Your intake details have been secured for attorney review.")
                    
                except Exception as sheet_err:
                    # In a law firm setting, we might log this internally rather than showing a dramatic red box.
                    # For debugging: st.error(f"Google Sheet Sync Error: {sheet_err}")
                    print(f"ERROR: Duffley Sheet sync failed: {sheet_err}") # Still logs to Streamlit backend

    except Exception as e:
        # Generic AI error
        st.error("Service momentarily unavailable. Please try your message again.")
