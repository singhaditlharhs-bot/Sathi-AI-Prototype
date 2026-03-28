import streamlit as st
import os
from streamlit_mic_recorder import mic_recorder
import google.generativeai as genai

# --- INITIALIZE API ---
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-1.5-flash')

# --- PAGE CONFIGURATION ---
st.set_page_config(page_title="Sathi-AI", page_icon="📻", layout="centered")

# --- RETRO SKEUOMORPHIC CSS ---
st.markdown("""
    <style>
    /* Warm Wood Background for the whole app */
    .stApp {
        background-color: #5c3a21;
        background-image: repeating-linear-gradient(
            45deg,
            transparent,
            transparent 10px,
            rgba(0,0,0,0.05) 10px,
            rgba(0,0,0,0.05) 20px
        );
    }
    
    /* Ivory/Aged Paper Console Container */
    .block-container {
        background-color: #f4ecd8;
        border-radius: 20px;
        padding: 40px;
        box-shadow: 10px 10px 30px rgba(0,0,0,0.5), 
                    inset 0px 0px 15px rgba(139, 69, 19, 0.2);
        border: 4px solid #8b4513;
        margin-top: 2rem;
    }

    /* The 3D Tactile Button */
    .stButton>button {
        width: 100%;
        height: 150px; /* Large target area */
        border-radius: 15px;
        font-size: 28px !important;
        font-weight: bold;
        background: linear-gradient(to bottom, #d42e2e, #a01a1a);
        color: white !important;
        border: 2px solid #5a0e0e;
        /* The 3D Shadow Effect */
        box-shadow: 0px 10px 0px #701010, 0px 15px 20px rgba(0,0,0,0.4);
        transition: all 0.1s ease;
        text-shadow: 1px 1px 2px black;
    }
    
    /* The 'Depress' Animation when clicked */
    .stButton>button:active {
        transform: translateY(10px);
        box-shadow: 0px 0px 0px #701010, 0px 5px 10px rgba(0,0,0,0.4);
    }

    /* Retro Typography */
    .main-text {
        font-size: 35px;
        font-weight: 800;
        text-align: center;
        color: #3e2723;
        font-family: 'Courier New', Courier, monospace;
        border-bottom: 2px solid #8b4513;
        padding-bottom: 15px;
        margin-bottom: 30px;
    }
    
    .instruction-text {
        font-size: 22px;
        color: #5d4037;
        text-align: center;
        font-weight: bold;
    }
    </style>
    """, unsafe_allow_html=True)

# --- APP HEADER ---
st.markdown('<p class="main-text">📻 SATHI - Digital Sahayak</p>', unsafe_allow_html=True)

# --- INSTRUCTIONS ---
st.markdown('<p class="instruction-text">Lal button dabayein aur baat karein<br>(Press the red button and speak)</p>', unsafe_allow_html=True)
st.write("") # Spacer

# --- THE MICROPHONE BUTTON ---
# The mic_recorder uses the stButton styling defined above
audio = mic_recorder(
    start_prompt="🔴 BAAT KAREIN (TAP TO TALK)",
    stop_prompt="⬛ BAND KAREIN (TAP TO STOP)",
    key='recorder'
)

if audio:
    st.audio(audio['bytes'])
    st.info("Sathi is listening to the radio waves... (Thinking)")
    
    # NEXT STEP: Connecting to Gemini
