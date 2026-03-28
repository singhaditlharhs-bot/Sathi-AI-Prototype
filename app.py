import streamlit as st
import os
from streamlit_mic_recorder import mic_recorder
import google.generativeai as genai

# --- INITIALIZE API ---
# This pulls the key you saved in 'Secrets'
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-1.5-flash')

# --- PAGE CONFIGURATION ---
st.set_page_config(page_title="Sathi-AI", page_icon="🫂", layout="centered")

# --- CUSTOM CSS ---
st.markdown("""
    <style>
    .stButton>button {
        width: 300px;
        height: 300px;
        border-radius: 50%;
        font-size: 30px;
        font-weight: bold;
        background-color: #4CAF50;
        color: white;
        border: 10px solid #2E7D32;
    }
    .main-text {
        font-size: 40px;
        font-weight: bold;
        text-align: center;
    }
    </style>
    """, unsafe_allow_html=True)

st.markdown('<p class="main-text">Pranam! Main Aapka Sathi Hoon. 🫂</p>', unsafe_allow_html=True)
st.write("---")

# --- THE MICROPHONE BUTTON ---
st.write("Niche diye gaye button ko dabayein aur baat karein:")

# This replaces the standard button with a recording button
audio = mic_recorder(
    start_prompt="Sathi Se Baat Karein (Tap to Talk)",
    stop_prompt="Bas, Maine Keh Diya (Tap to Stop)",
    key='recorder'
)

if audio:
    st.audio(audio['bytes'])
    st.info("Sathi is thinking...")
    
    # NEXT STEP: We will send 'audio['bytes']' to Gemini to understand the words
    # and then to ElevenLabs to speak back.
