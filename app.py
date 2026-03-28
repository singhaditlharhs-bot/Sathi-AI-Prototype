import streamlit as st
import os
import tempfile
from streamlit_mic_recorder import mic_recorder
import google.generativeai as genai

# --- INITIALIZE API ---
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-1.5-flash-latest')

# --- PAGE CONFIGURATION ---
st.set_page_config(page_title="Sathi-AI", page_icon="📻", layout="centered")

# --- RETRO KEYBOARD & UI CSS ---
st.markdown("""
    <style>
    /* Main Background: Textured Wood */
    .stApp {
        background-color: #5c3a21;
        background-image: url('https://www.transparenttextures.com/patterns/wood-pattern.png');
    }
    
    /* Ivory Console */
    .block-container {
        background-color: #f4ecd8;
        border-radius: 25px;
        padding: 30px;
        box-shadow: 15px 15px 40px rgba(0,0,0,0.6);
        border: 5px solid #3e2723;
    }

    /* AAJ TAK RED HEADER */
    .header-box {
        background-color: #cc0000;
        padding: 15px;
        border-radius: 15px 15px 0 0;
        border-bottom: 5px solid #800000;
        margin-bottom: 20px;
    }

    /* TYPEWRITER KEY STYLE */
    .stButton>button {
        font-family: 'Courier New', Courier, monospace;
        font-weight: 900 !important;
        border-radius: 12px !important;
        text-transform: uppercase;
        transition: 0.1s;
    }

    /* THE MAIN VOICE BUTTON (Large Red) */
    div[data-testid="stVerticalBlock"] > div:nth-child(4) .stButton>button {
        height: 120px;
        background: linear-gradient(145deg, #ff4d4d, #b30000) !important;
        border-bottom: 10px solid #660000 !important;
        font-size: 26px !important;
        color: white !important;
        margin-bottom: 20px;
    }

    /* THE KEYBOARD BUTTONS (Ivory Mechanical Keys) */
    .keyboard-row .stButton>button {
        background: #fffdf5 !important;
        color: #3e2723 !important;
        border: 2px solid #d1c4a9 !important;
        border-bottom: 6px solid #bcae92 !important;
        font-size: 22px !important;
        height: 70px;
        width: 100%;
    }

    .keyboard-row .stButton>button:active {
        transform: translateY(4px);
        border-bottom: 2px solid #bcae92 !important;
    }

    /* LANGUAGE TOGGLE (Navy Blue) */
    .toggle-box .stButton>button {
        background: #002d62 !important;
        color: white !important;
        border-bottom: 6px solid #001a39 !important;
        font-size: 20px !important;
    }

    .instruction-text {
        font-size: 22px;
        color: #3e2723;
        text-align: center;
        font-weight: bold;
        background: #fff9c4;
        padding: 10px;
        border-radius: 10px;
        border: 1px dashed #8b4513;
    }
    </style>
    """, unsafe_allow_html=True)

# --- APP HEADER ---
st.markdown('<div class="header-box"><h1 style="color:white; text-align:center; margin:0;">📻 SATHI AI</h1></div>', unsafe_allow_html=True)

# --- LANGUAGE STATE ---
if 'lang' not in st.session_state:
    st.session_state.lang = 'HINDI'
if 'text_input' not in st.session_state:
    st.session_state.text_input = ""

# --- LANGUAGE TOGGLE ---
st.markdown('<p class="instruction-text">Bhasha Chunein / Choose Language:</p>', unsafe_allow_html=True)
col_t1, col_t2 = st.columns(2)
with col_t1:
    if st.button("🇮🇳 HINDI (हिंदी)", key="btn_hi"):
        st.session_state.lang = 'HINDI'
with col_t2:
    if st.button("🇬🇧 ENGLISH", key="btn_en"):
        st.session_state.lang = 'ENGLISH'

st.write("---")

# --- VOICE INPUT SECTION ---
audio = mic_recorder(
    start_prompt="🎤 BOL KAR BATAYEIN (TAP TO TALK)",
    stop_prompt="🛑 BAS KAREIN (STOP)",
    key='recorder'
)

# --- KEYBOARD SECTION ---
st.markdown(f'<p class="instruction-text">Yahan Likhein (Type here in {st.session_state.lang}):</p>', unsafe_allow_html=True)

# Simulated Keyboard Rows
if st.session_state.lang == 'HINDI':
    keys = [["क", "ख", "ग", "घ"], ["च", "छ", "ज", "झ"], ["ट", "ठ", "ड", "ढ"]]
else:
    keys = [["A", "B", "C", "D"], ["E", "F", "G", "H"], ["I", "J", "K", "L"]]

for row in keys:
    cols = st.columns(len(row))
    for i, key in enumerate(row):
        if cols[i].button(key, key=f"k_{key}"):
            st.session_state.text_input += key

# Text Display Area
user_text = st.text_input("Aapka Sandesh (Your Message):", value=st.session_state.text_input)

if st.button("🚀 SAATHI KO BHEJEIN (SEND MESSAGE)"):
    if user_text:
        with st.spinner("Sathi soch raha hai..."):
            # Here we send the text to Gemini
            prompt = f"User says: {user_text}. Respond as Sathi (respectful elder companion) in {st.session_state.lang}."
            response = model.generate_content(prompt)
            st.success(response.text)
            st.session_state.text_input = "" # Reset
