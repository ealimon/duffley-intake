# ... (Top of your code remains the same) ...

# 2. Dynamic Model Logic
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
            "Tone: Compassionate, patient, and professional. "
            "Goal: Collect Name, Texas County, Legal Need, and Contact info for the attorney to review."
        )
    )
except Exception as e:
    st.error(f"Initialization Error: {e}")
    st.stop()

# ... (Chat logic remains the same) ...

if not st.session_state.messages:
    welcome = "Welcome to Duffley Law PLLC. My name is Clara. I am an AI assistant, not an attorney, and this chat does not create an attorney-client relationship. How can I help you protect your family's legacy today?"
    st.session_state.messages.append({"role": "assistant", "content": welcome})
    with st.chat_message("assistant", avatar="⚖️"):
        st.markdown(welcome)

# ... (Rest of the interaction code) ...
