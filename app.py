import streamlit as st
import datetime
import sqlite3
import google.generativeai as genai
import base64
from elevenlabs.client import ElevenLabs

# --- 1. INITIALIZATION & FUNCTIONS ---
conn = sqlite3.connect('sathi_memory.db', check_same_thread=False)
c = conn.cursor()
c.execute('CREATE TABLE IF NOT EXISTS health_logs (date TEXT, user_input TEXT, ai_response TEXT, tags TEXT)')
c.execute('CREATE TABLE IF NOT EXISTS contacts (role TEXT, name TEXT, phone TEXT)')

# Default Doctor Info
c.execute("SELECT * FROM contacts WHERE role='Doctor'")
if not c.fetchone():
    c.execute("INSERT INTO contacts VALUES ('Doctor', 'Dr. Sharma (AIIMS)', '+91-9876543210')")
    conn.commit()

# API Keys
GEMINI_API_KEY = st.secrets.get("GEMINI_API_KEY")
ELEVEN_API_KEY = st.secrets.get("ELEVEN_API_KEY")
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-1.5-flash') 
voice_client = ElevenLabs(api_key=ELEVEN_API_KEY)

# --- 2. AVATAR DISPLAY FUNCTION ---
def display_media(file_path, is_video=False):
    try:
        with open(file_path, "rb") as f:
            data = f.read()
        b64 = base64.b64encode(data).decode()
        
        if is_video:
            st.markdown(f"""
                <div style="display: flex; justify-content: center; margin-bottom: 10px;">
                    <video width="220" height="220" autoplay loop muted 
                    style="border-radius: 50%; border: 6px solid #2E7D32; object-fit: cover; box-shadow: 0 10px 30px rgba(46,125,50,0.4);">
                        <source src="data:video/mp4;base64,{b64}" type="video/mp4">
                    </video>
                </div>
            """, unsafe_allow_html=True)
        else:
            st.markdown(f"""
                <div style="display: flex; justify-content: center; margin-bottom: 10px;">
                    <img src="data:image/png;base64,{b64}" width="220" height="220" 
                    style="border-radius: 50%; border: 6px solid #2E7D32; object-fit: cover; box-shadow: 0 10px 30px rgba(0,0,0,0.2);">
                </div>
            """, unsafe_allow_html=True)
    except FileNotFoundError:
        st.warning(f"File {file_path} not found. Upload it to GitHub!")

# --- 3. ADVANCED UI STYLING ---
st.set_page_config(page_title="Sathi-AI", layout="wide")

st.markdown("""
    <style>
    .stApp { background-color: #FDF5E6; }
    
    /* Header Card */
    .header-card { 
        background: linear-gradient(135deg, #1B5E20, #2E7D32); 
        color: white; padding: 20px; border-radius: 20px; 
        text-align: center; margin-bottom: 20px;
        box-shadow: 0 4px 15px rgba(0,0,0,0.1);
    }

    /* Keyboard Boundary Box */
    .kb-boundary {
        background-color: #E0E0E0;
        padding: 20px;
        border-radius: 25px;
        border: 4px solid #BDBDBD;
        box-shadow: inset 0 4px 10px rgba(0,0,0,0.1);
        margin-top: 10px;
    }

    /* Professional Buttons */
    .stButton>button {
        background-color: #FFD54F !important;
        color: #1A1A1A !important;
        font-weight: 800 !important;
        border: 2px solid #F57F17 !important;
        border-radius: 12px !important;
        height: 60px !important;
        font-size: 22px !important;
        transition: all 0.2s ease-in-out;
    }
    .stButton>button:hover {
        transform: scale(1.05);
        background-color: #FFCA28 !important;
    }

    /* SOS Styling */
    .sos-btn button {
        background: linear-gradient(to right, #D32F2F, #B71C1C) !important;
        color: white !important;
        border: none !important;
        font-size: 24px !important;
    }
    </style>
""", unsafe_allow_html=True)

# --- 4. KEYBOARD LOGIC ---
if 'typed_text' not in st.session_state: st.session_state.typed_text = ""
if 'caps' not in st.session_state: st.session_state.caps = True
if 'is_talking' not in st.session_state: st.session_state.is_talking = False

def add_char(char): st.session_state.typed_text += char
def backspace(): st.session_state.typed_text = st.session_state.typed_text[:-1]

# --- 5. DYNAMIC GREETINGS ---
now = datetime.datetime.now()
hour = now.hour
if 5 <= hour < 12: greet = "Pranam Uncle-ji, Shubh Prabhat! ☀️"
elif 12 <= hour < 17: greet = "Pranam Sir, Shubh Dopahar! 🌤️"
else: greet = "Shubh Sandhya Uncle-ji! 🌆"

st.markdown(f'<div class="header-card"><h1>{greet}</h1><p>{now.strftime("%I:%M %p")}</p></div>', unsafe_allow_html=True)

# --- 6. THE INTERFACE ---
tab1, tab2, tab3 = st.tabs(["💬 Baat Karein", "📁 Doctor Info", "📜 History"])

with tab1:
    # A. AVATAR AREA
    if st.session_state.is_talking:
        display_media("doctor_talking.mp4", is_video=True)
    else:
        display_media("doctor_static.png", is_video=False)

    # B. MESSAGE DISPLAY
    st.info(st.session_state.typed_text if st.session_state.typed_text else "Likhein ya Camera dikhayein...")

    # C. KEYBOARD WITH BOUNDARY
    st.markdown('<div class="kb-boundary">', unsafe_allow_html=True)
    keys = [['Q', 'W', 'E', 'R', 'T', 'Y', 'U', 'I', 'O', 'P'],
            ['A', 'S', 'D', 'F', 'G', 'H', 'J', 'K', 'L'],
            ['Z', 'X', 'C', 'V', 'B', 'N', 'M']]
    
    for row in keys:
        cols = st.columns(len(row))
        for i, key in enumerate(row):
            display_key = key if st.session_state.caps else key.lower()
            if cols[i].button(display_key, key=f"btn_{display_key}"):
                add_char(display_key)

    col_c, col_s, col_b = st.columns([2, 5, 2])
    if col_c.button("⬆️ CAPS"): st.session_state.caps = not st.session_state.caps
    if col_s.button("── SPACE ──"): add_char(" ")
    if col_b.button("⬅️ BACKSPACE"): backspace()
    st.markdown('</div>', unsafe_allow_html=True)

    st.divider()
    
    # D. ACTION BRIDGE
    col_send, col_sos = st.columns(2)
    
    if col_send.button("✅ BHEJEIN (SEND)"):
        if st.session_state.typed_text:
            st.session_state.is_talking = True
            with st.spinner("Sathi sun raha hai..."):
                persona = f"You are Sathi, a caring son and doctor. Use 'Aap'. Time: {now.strftime('%I:%M %p')}"
                response = model.generate_content([persona, st.session_state.typed_text])
                
                # Database Log
                c.execute("INSERT INTO health_logs VALUES (?, ?, ?, ?)", 
                          (now.strftime("%Y-%m-%d %H:%M"), st.session_state.typed_text, response.text, "Chat"))
                conn.commit()
                
                st.markdown(f'<div style="background: white; border-left: 10px solid #2E7D32; padding: 20px; border-radius: 15px;"><b>Dr. Sathi:</b><br>{response.text}</div>', unsafe_allow_html=True)
                
                try:
                    audio = voice_client.generate(text=response.text, voice="Josh", model="eleven_multilingual_v2")
                    st.audio(b"".join(audio), format="audio/mp3", autoplay=True)
                except: st.warning("Audio unavailable.")
                
                st.session_state.typed_text = ""
                # To reset talking state after response, you can use a timer or manual button
                # For now, it stays talking until next interaction

    with col_sos:
        if st.button("🆘 EMERGENCY", key="sos_btn"):
            doc_info = c.execute("SELECT name, phone FROM contacts WHERE role='Doctor'").fetchone()
            st.error(f"🚨 Calling {doc_info[0]} at {doc_info[1]}")

# Rest of tabs remain same...
with tab2:
    st.subheader("🏥 Doctor ki Jankari")
    d_name = st.text_input("Doctor Name:", value="Dr. Sharma (AIIMS)")
    d_phone = st.text_input("Doctor Phone:", value="+91 9876543210")
    if st.button("Save Info"):
        c.execute("UPDATE contacts SET name=?, phone=? WHERE role='Doctor'", (d_name, d_phone))
        conn.commit()
        st.success("Jankari save ho gayi!")

with tab3:
    st.subheader("📜 History")
    logs = c.execute("SELECT * FROM health_logs ORDER BY date DESC").fetchall()
    for log in logs:
        st.write(f"**[{log[0]}]** Aap: {log[1]} | Sathi: {log[2]}")
