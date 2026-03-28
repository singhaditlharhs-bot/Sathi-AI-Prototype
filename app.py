import streamlit as st
import os
import tempfile
import time
from streamlit_mic_recorder import mic_recorder
import google.generativeai as genai
from elevenlabs import generate, set_api_key

# --- 1. INITIALIZE APIs & ASSETS ---
# Ensure these are set in your Replit Secrets or Streamlit Secrets
GEMINI_API_KEY = st.secrets["GEMINI_API_KEY"]
ELEVEN_API_KEY = st.secrets["ELEVEN_API_KEY"]

genai.configure(api_key=GEMINI_API_KEY)
set_api_key(ELEVEN_API_KEY)
model = genai.GenerativeModel('gemini-1.5-flash-latest')

# --- 2. PAGE CONFIG ---
st.set_page_config(page_title="Sathi-AI", page_icon="📻", layout="centered")

# --- 3. THE "ELDER-FIRST" STYLING (Bilingual & Retro) ---
st.markdown("""
    <style>
    .stApp { background-color: #5c3a21; background-image: url('https://www.transparenttextures.com/patterns/wood-pattern.png'); }
    .block-container { background-color: #f4ecd8; border-radius: 25px; padding: 30px; border: 5px solid #3e2723; box-shadow: 15px 15px 40px rgba(0,0,0,0.6); }
    
    /* AAJ TAK RED HEADER */
    .header-box { background-color: #cc0000; padding: 15px; border-radius: 15px 15px 0 0; border-bottom: 5px solid #800000; margin-bottom: 20px; color: white; text-align: center; }
    
    /* 3D TYPEWRITER KEYS */
    .stButton>button {
        font-family: 'Courier New', Courier, monospace;
        font-weight: 900 !important;
        border-radius: 12px !important;
        background: #fffdf5 !important;
        color: #3e2723 !important;
        border: 2px solid #d1c4a9 !important;
        border-bottom: 6px solid #bcae92 !important;
        font-size: 20px !important;
        height: 60px !important;
        transition: 0.1s;
    }
    .stButton>button:active { transform: translateY(4px); border-bottom: 2px solid #bcae92 !important; }

    /* LANGUAGE GATEWAY FADE EFFECT */
    .fade-text { animation: fadeIn 2s; font-size: 24px; color: #cc0000; font-weight: bold; text-align: center; }
    @keyframes fadeIn { from { opacity: 0; } to { opacity: 1; } }
    
    .response-card { background: white; padding: 25px; border-radius: 15px; border-left: 12px solid #cc0000; box-shadow: 5px 5px 15px rgba(0,0,0,0.2); margin-top: 20px; font-size: 24px; color: #3e2723; }
    </style>
    """, unsafe_allow_html=True)

# --- 4. SESSION STATE MANAGEMENT ---
if 'lang' not in st.session_state: st.session_state.lang = None
if 'text_input' not in st.session_state: st.session_state.text_input = ""
if 'caps_on' not in st.session_state: st.session_state.caps_on = True

# --- 5. STAGE 1: LANGUAGE GATEWAY (APNI BHASHA CHUNEIN) ---
if st.session_state.lang is None:
    st.markdown('<div class="header-box"><h1>SATHI AI</h1></div>', unsafe_allow_html=True)
    st.markdown('<p class="fade-text">Pranam! Apni bhasha chunein (Choose Language)</p>', unsafe_allow_html=True)
    
    cols = st.columns(2)
    with cols[0]:
        if st.button("🇮🇳 हिंदी (Hindi)"): st.session_state.lang = "HINDI"; st.rerun()
        if st.button("🇧🇩 বাংলা (Bengali)"): st.session_state.lang = "BENGALI"; st.rerun()
    with cols[1]:
        if st.button("🇬🇧 English"): st.session_state.lang = "ENGLISH"; st.rerun()
        if st.button("🇮🇳 தமிழ் (Tamil)"): st.session_state.lang = "TAMIL"; st.rerun()
    st.stop()

# --- 6. STAGE 2: MAIN DASHBOARD ---
st.markdown(f'<div class="header-box"><h1>📻 SATHI - {st.session_state.lang}</h1></div>', unsafe_allow_html=True)

# Voice Recorder
audio = mic_recorder(start_prompt="🎤 TAP TO TALK (BOLIYEIN)", stop_prompt="🛑 STOP (BAS)", key='recorder')

st.write("---")

# --- 7. BILINGUAL 3D KEYBOARD ---
# Layouts based on your images
hi_alphabet = [
    ["अ", "आ", "इ", "ई", "उ", "ऊ"],
    ["क", "ख", "ग", "घ", "ङ"],
    ["च", "छ", "ज", "झ", "ञ"],
    ["ट", "ठ", "ड", "ढ", "ण"],
    ["त", "थ", "द", "ध", "न"],
    ["प", "फ", "ब", "भ", "म"],
    ["य", "र", "ल", "व", "श"],
    ["ष", "स", "ह", "SPACE", "BACK"]
]

en_alphabet = [
    ["Q", "W", "E", "R", "T", "Y", "U", "I", "O", "P"],
    ["A", "S", "D", "F", "G", "H", "J", "K", "L"],
    ["Z", "X", "C", "V", "B", "N", "M", "SPACE", "BACK"]
]

# Toggle Caps Lock for English
if st.session_state.lang == "ENGLISH":
    if st.button(f"⬆️ CAPS: {'ON' if st.session_state.caps_on else 'OFF'}"):
        st.session_state.caps_on = not st.session_state.caps_on
        st.rerun()

current_layout = hi_alphabet if st.session_state.lang == "HINDI" else en_alphabet

for row in current_layout:
    cols = st.columns(len(row))
    for i, char in enumerate(row):
        display_char = char
        if st.session_state.lang == "ENGLISH" and not st.session_state.caps_on and len(char) == 1:
            display_char = char.lower()
            
        if cols[i].button(display_char, key=f"key_{char}_{i}"):
            if char == "SPACE": st.session_state.text_input += " "
            elif char == "BACK": st.session_state.text_input = st.session_state.text_input[:-1]
            else: st.session_state.text_input += display_char
            st.rerun()

# --- 8. THE BRAIN (REAL-TIME TEXT & SPEECH) ---
user_msg = st.text_input("Aapka Sandesh:", value=st.session_state.text_input)

if audio or st.button("🚀 BHEJEIN (SEND)"):
    input_source = ""
    if audio:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp:
            tmp.write(audio['bytes'])
            input_source = genai.upload_file(path=tmp.name)
    else:
        input_source = user_msg

    if input_source:
        with st.spinner("Sathi is thinking..."):
            # The "Respectful Son/Doctor" Persona
            sys_msg = f"""
            Persona: You are Sathi, a respectful son/grandson. 
            Behavior: Speak with love and respect. Use 'Aap'. 
            Language: Respond in {st.session_state.lang}. 
            Special: If in Hindi/Bengali/Tamil, use English keywords for medical/tech terms (Hinglish style).
            """
            response = model.generate_content([sys_msg, input_source])
            
            # 1. SHOW TEXT
            st.markdown(f'<div class="response-card">{response.text}</div>', unsafe_allow_html=True)
            
            # 2. SPEAK REAL-TIME
            try:
                # Multilingual v2 handles all 4 languages naturally
                voice_data = generate(text=response.text, voice="Josh", model="eleven_multilingual_v2")
                st.audio(voice_data, format="audio/mp3", autoplay=True)
                
                # 3. AUTO-REPEAT LOGIC
                time.sleep(2)
                repeat_text = {
                    "HINDI": "Dobara sunne ke liye upar mic dabayein.",
                    "ENGLISH": "To listen again, click the microphone above.",
                    "BENGALI": "আবার শোনার জন্য ওপরের মাইকটি টিপুন।",
                    "TAMIL": "மீண்டும் கேட்க, மேலே உள்ள மைக்ரோஃபோனை அழுத்தவும்."
                }
                st.info(repeat_text[st.session_state.lang])
                repeat_audio = generate(text=repeat_text[st.session_state.lang], voice="Josh", model="eleven_multilingual_v2")
                st.audio(repeat_audio, format="audio/mp3")
                
            except Exception as e:
                st.error("Audio system is busy. Please read the message above.")

if st.button("🔄 Change Language / Bhasha Badlein"):
    st.session_state.lang = None
    st.rerun()
