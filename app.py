import streamlit as st
import datetime
import google.generativeai as genai
# NEW IMPORT: Works with the library you just added
from elevenlabs.client import ElevenLabs

# --- 1. PAGE CONFIG (Must be the very first Streamlit command) ---
st.set_page_config(page_title="Sathi-AI", page_icon="📻", layout="centered")

# --- 2. SECRETS & API INITIALIZATION ---
GEMINI_API_KEY = st.secrets.get("GEMINI_API_KEY")
ELEVEN_API_KEY = st.secrets.get("ELEVEN_API_KEY")

if not GEMINI_API_KEY or not ELEVEN_API_KEY:
    st.error("🔑 Sathi ki chaabi missing hai! Please check Streamlit Secrets.")
    st.stop()

genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-1.5-flash-latest')
voice_client = ElevenLabs(api_key=ELEVEN_API_KEY)

# --- 3. TIME-BASED EMOTIONAL GREETING ---
def get_sathi_intro():
    now = datetime.datetime.now()
    hour = now.hour
    if 5 <= hour < 12: return "Pranam Uncle-ji, Shubh Prabhat! ☀️"
    elif 12 <= hour < 17: return "Pranam Sir, Shubh Dopahar! 🌤️"
    elif 17 <= hour < 21: return "Shubh Sandhya Uncle-ji! Kaise hain aap? 🌆"
    else: return "Shubh Ratri Sir! Din kaisa raha? 🌙"

# --- 4. MOBILE-FRIENDLY STYLING ---
st.markdown("""
    <style>
    .stApp { background-color: #fdf5e6; }
    .header-box { background-color: #b22222; color: white; padding: 20px; border-radius: 15px; text-align: center; margin-bottom: 20px; }
    /* BIG BUTTONS for mobile thumbs */
    .stButton>button {
        width: 100% !important; height: 80px !important; font-size: 24px !important;
        border-radius: 15px !important; border: 3px solid #3e2723 !important;
    }
    .response-card { background: white; padding: 20px; border-radius: 15px; border-left: 10px solid #b22222; font-size: 22px; margin-top: 20px; }
    </style>
    """, unsafe_allow_html=True)

# --- 5. DASHBOARD ---
st.markdown(f'<div class="header-box"><h1>📻 {get_sathi_intro()}</h1></div>', unsafe_allow_html=True)

# Simple Language Selector for now
lang = st.radio("Bhasha Chunein / Choose Language:", ["HINDI", "ENGLISH"], horizontal=True)

user_text = st.text_input("Uncle-ji, kuch kehna chahte hain? (Type here):")

if st.button("🚀 BHEJEIN (SEND)"):
    if user_text:
        with st.spinner("Sathi soch raha hai..."):
            # Emotional Persona
            persona = f"""
            You are Sathi, a respectful companion. 
            NEVER use 'Beta'. Use 'Uncle-ji', 'Sir', or 'Aap'.
            Be emotional and caring. If they are in pain, show genuine worry.
            Respond in {lang}.
            """
            response = model.generate_content([persona, user_text])
            
            # Show Text
            st.markdown(f'<div class="response-card">{response.text}</div>', unsafe_allow_html=True)
            
            # Speak (New ElevenLabs logic)
            try:
                audio_stream = voice_client.generate(
                    text=response.text, 
                    voice="Josh", 
                    model="eleven_multilingual_v2"
                )
                st.audio(b"".join(audio_stream), format="audio/mp3", autoplay=True)
            except Exception as e:
                st.error("Gale mein thodi kharash hai (Audio Busy). Please read above!")
