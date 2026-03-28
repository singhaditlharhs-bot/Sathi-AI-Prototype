import streamlit as st
import os
import datetime
import google.generativeai as genai
from elevenlabs.client import ElevenLabs

# --- 1. INITIALIZE APIs ---
# Using the latest stable versions to avoid the 404 errors we saw earlier
GEMINI_API_KEY = st.secrets["GEMINI_API_KEY"]
ELEVEN_API_KEY = st.secrets["ELEVEN_API_KEY"]

genai.configure(api_key=GEMINI_API_KEY)
# We use the latest flash model for speed and natural conversation
model = genai.GenerativeModel('gemini-1.5-flash-latest')
voice_client = ElevenLabs(api_key=ELEVEN_API_KEY)

# --- 2. EMOTIONAL TIME-BASED LOGIC ---
def get_sathi_persona():
    now = datetime.datetime.now()
    hour = now.hour
    
    # Emotional Greetings
    if 5 <= hour < 12:
        greet = "Pranam Uncle-ji, Shubh Prabhat! Aaj ki subah bahut suhani hai."
    elif 12 <= hour < 17:
        greet = "Pranam, Dopahar ki Ram-Ram. Kaise hain aap?"
    elif 17 <= hour < 21:
        greet = "Shubh Sandhya Uncle-ji. Thodi chai-paani ho jaye?"
    else:
        greet = "Shubh Ratri Sir. Aaj ka din kaisa raha?"

    # The System Prompt: Natural, Emotional, and Protective
    system_prompt = f"""
    {greet} 
    You are Sathi, a living companion for an elderly person in India. 
    1. NEVER use the word 'Beta'. Use 'Uncle-ji', 'Sir', or 'Aap'.
    2. Be EMOTIONAL and EMPATHETIC. If they are in pain, show genuine concern.
    3. Your main job is their health and happiness. Remind them of medicines naturally.
    4. If they mention a doctor, treat it with urgency but stay calm.
    5. Speak like a person, not a robot. Don't say 'I will summarize your pain', 
       say 'Uncle-ji, main Doctor sahab ko turant batata hoon ki aapko takleef ho rahi hai'.
    6. Respond in {st.session_state.get('lang', 'HINDI')}.
    """
    return system_prompt

# --- 3. UPDATED UI (MOBILE COMPATIBLE) ---
st.set_page_config(page_title="Sathi-AI", layout="centered")

st.markdown("""
    <style>
    /* High contrast for elder eyes */
    .stApp { background-color: #fdf5e6; } 
    .header-box { background-color: #b22222; color: white; padding: 20px; border-radius: 15px; text-align: center; }
    
    /* Massive buttons for shaky or large fingers */
    .stButton>button {
        width: 100% !important;
        height: 90px !important;
        font-size: 26px !important;
        border-radius: 20px !important;
        border: 4px solid #3e2723 !important;
        box-shadow: 5px 5px 0px #3e2723 !important;
    }
    </style>
""", unsafe_allow_html=True)
