import streamlit as st
import datetime
import sqlite3
import google.generativeai as genai
from elevenlabs.client import ElevenLabs

# --- 1. INITIALIZATION ---
conn = sqlite3.connect('sathi_memory.db', check_same_thread=False)
c = conn.cursor()
c.execute('CREATE TABLE IF NOT EXISTS health_logs (date TEXT, user_input TEXT, ai_response TEXT, tags TEXT)')
conn.commit()

# API Keys from your Streamlit Secrets
GEMINI_API_KEY = st.secrets.get("GEMINI_API_KEY")
ELEVEN_API_KEY = st.secrets.get("ELEVEN_API_KEY")
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-1.5-flash-latest')
voice_client = ElevenLabs(api_key=ELEVEN_API_KEY)

# --- 2. ELDER-FRIENDLY KEYBOARD & SOS STYLE ---
st.set_page_config(page_title="Sathi-AI", layout="centered")

st.markdown("""
    <style>
    .stApp { background-color: #FDF5E6; }
    .header-card { background: linear-gradient(135deg, #2E7D32, #1B5E20); color: white; padding: 20px; border-radius: 15px; text-align: center; margin-bottom: 20px; }
    
    /* KEYBOARD STYLING: High Attention Colors */
    .key-btn {
        background-color: #FFD54F !important;
        color: #000 !important;
        font-weight: bold !important;
        font-size: 24px !important;
        border: 3px solid #F57F17 !important;
        border-radius: 10px !important;
        height: 60px !important;
        width: 100% !important;
    }
    .special-key {
        background-color: #EF5350 !important; /* Red for Backspace/SOS */
        color: white !important;
    }
    .space-key {
        background-color: #81C784 !important; /* Green for Space */
        color: white !important;
    }
    
    /* Sathi Message Style (The Doctor-Son Tone) */
    .sathi-card {
        background: white; border-left: 10px solid #2E7D32;
        padding: 20px; border-radius: 15px; font-size: 22px; line-height: 1.5;
        margin-top: 20px; box-shadow: 0 4px 8px rgba(0,0,0,0.1);
    }
    </style>
""", unsafe_allow_html=True)

# --- 3. KEYBOARD LOGIC ---
if 'typed_text' not in st.session_state:
    st.session_state.typed_text = ""
if 'caps' not in st.session_state:
    st.session_state.caps = True

def add_char(char):
    st.session_state.typed_text += char

def backspace():
    st.session_state.typed_text = st.session_state.typed_text[:-1]

# --- 4. THE INTERFACE ---
now = datetime.datetime.now()
st.markdown(f'<div class="header-card"><h2>Aapka Sathi Sahayak 🩺</h2><p>{now.strftime("%I:%M %p")}</p></div>', unsafe_allow_html=True)

# DISPLAY AREA
st.markdown("### 📝 Aapka Sandesh (Your Message):")
st.info(st.session_state.typed_text if st.session_state.typed_text else "Keyboard se likhein...")

# KEYBOARD GRID (A-Z)
keys = [
    ['Q', 'W', 'E', 'R', 'T', 'Y', 'U', 'I', 'O', 'P'],
    ['A', 'S', 'D', 'F', 'G', 'H', 'J', 'K', 'L'],
    ['Z', 'X', 'C', 'V', 'B', 'N', 'M']
]

for row in keys:
    cols = st.columns(len(row))
    for i, key in enumerate(row):
        display_key = key if st.session_state.caps else key.lower()
        if cols[i].button(display_key, key=f"btn_{display_key}"):
            add_char(display_key)

# SPECIAL KEYS
col_caps, col_space, col_back = st.columns([2, 5, 2])
if col_caps.button("⬆️ CAPS", key="caps_btn"):
    st.session_state.caps = not st.session_state.caps
if col_space.button("── SPACE ──", key="space_btn"):
    add_char(" ")
if col_back.button("⬅️ DEL", key="del_btn"):
    backspace()

# ACTION BUTTONS
col_send, col_sos = st.columns(2)
send_btn = col_send.button("✅ BHEJEIN (SEND)")
sos_btn = col_sos.button("🆘 EMERGENCY / SOS")

if send_btn and st.session_state.typed_text:
    # PERSONA: The Respectful Doctor-Son
    persona = f"""
    You are Sathi. Speak like a caring son who is also a doctor. 
    1. ALWAYS use 'Aap', never 'Tum' or 'Beta'.
    2. Use Hinglish (e.g., 'Aap apni medicine time par lijiye' or 'Checkup zaroori hai').
    3. Be warm, emotional, and responsible. 
    Current Time: {now.strftime("%I:%M %p")}
    """
    response = model.generate_content([persona, st.session_state.typed_text])
    
    # Save to Database
    c.execute("INSERT INTO health_logs VALUES (?, ?, ?, ?)", 
              (now.strftime("%Y-%m-%d %H:%M"), st.session_state.typed_text, response.text, "Chat"))
    conn.commit()
    
    st.markdown(f'<div class="sathi-card"><b>Sathi (Doctor-Son):</b><br>{response.text}</div>', unsafe_allow_html=True)
    
    # Voice output
    try:
        audio = voice_client.generate(text=response.text, voice="Josh", model="eleven_multilingual_v2")
        st.audio(b"".join(audio), format="audio/mp3", autoplay=True)
    except:
        st.warning("Awaaz system busy hai, kripya sandesh padein.")
    
    # Clear keyboard after sending
    st.session_state.typed_text = ""

if sos_btn:
    st.error("🚨 EMERGENCY ALERT! Family members aur Doctor ko message bhej diya gaya hai. Aap ghabraiye mat, hum saath hain.")
    # Here we would integrate Twilio/SMS API in the next sub-step.
