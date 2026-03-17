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

# Custom CSS for the "Duffley Blue" Aesthetic & Professional Layout
st.markdown("""
    <style>
        #MainMenu, footer, header {visibility: hidden;}
        div[data-testid="stToolbar"] {display: none;}
        .stApp {background-color: #ffffff;}
        
        /* Corporate Font Styling (Serif for Trust) */
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

        /* Header Layout */
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

# 2. Professional SVG Header (Shield & Pillars)
st.markdown("""
    <div class="header-box">
        <svg width="60" height="60" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
            <path d="M12 1L3 5V11C3 16.55 6.84 21.74 12 23C17.16 21.74 21 16.55 21 11V5L12 1Z" fill="#1A365D"/>
            <path d="M9 14H10V10H9V14ZM14 14H15V10H14V14ZM11.5 14H12.5V10H11.5V14ZM8 16H16V15H8V16ZM8 9H16V8H8V9Z" fill="white"/>
        </svg>
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
    model_name="gemini-3.1-flash-lite-preview",
    system_instruction=(
        "You are the Professional Intake Assistant for Duffley Law PLLC. "
        "Your tone is compassionate, patient, and highly professional. "
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
    with st.chat_message("
