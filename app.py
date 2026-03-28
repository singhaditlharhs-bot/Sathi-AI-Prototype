import streamlit as st
import datetime
import sqlite3
import google.generativeai as genai
from elevenlabs.client import ElevenLabs

# --- 1. INITIALIZATION & LIVING BRAIN DATABASE ---
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

# --- 2. ADAPTIVE UI DESIGN (Mobile & PC Friendly) ---
st.set_page_config(page_title="Sathi-AI", layout="wide") # Wide layout helps with PC scaling

st.markdown("""
    <style>
    .stApp { background-color: #FDF5E6; }
    
    /* Responsive Header */
    .header-card { 
        background: linear-gradient(135deg, #2E7D32, #1B5E20); 
        color: white; padding: 25px; border-radius: 15px; 
        text-align: center; margin-bottom: 20px;
    }

    /* Adaptive Keyboard Buttons */
    .stButton>button {
        background-color: #FFD54F !important;
        color: #000 !important;
        font-weight: bold !important;
        border: 2px solid #F57F17 !important;
        border-radius: 10px !important;
        width: 100% !important;
        transition: 0.3s;
    }
    
    /* Small screen (Mobile) optimization */
    @media (max-width: 600px) {
        .stButton>button { height: 70px !important; font-size: 26px !important; }
        .header-card h1 { font-size: 28px !important; }
    }
    
    /* Large screen (PC) optimization */
    @media (min-width: 601px) {
        .stButton>button { height: 55px !important; font-size: 20px !important; }
    }

    /* Attention-Seeking SOS Button */
    .sos-btn button {
        background-color: #D32F2F !important;
        color: white !important;
        border: 3px solid #7B1FA2 !important;
        font-size: 24px !important;
    }
    </style>
""", unsafe_allow_html=True)

# --- 3. KEYBOARD & BRAIN LOGIC ---
if 'typed_text' not in st.session_state: st.session_state.typed_text = ""
if 'caps' not in st.session_state: st.session_state.caps = True

def add_char(char): st.session_state.typed_text += char
def backspace(): st.session_state.typed_text = st.session_state.typed_text[:-1]

# --- 4. LIVING BRAIN: DYNAMIC GREETINGS ---
now = datetime.datetime.now()
hour = now.hour
if 5 <= hour < 12: greet = "Pranam Uncle-ji, Shubh Prabhat! ☀️"
elif 12 <= hour < 17: greet = "Pranam Sir, Shubh Dopahar! 🌤️"
else: greet = "Shubh Sandhya Uncle-ji! 🌆"

st.markdown(f'<div class="header-card"><h1>{greet}</h1><p>{now.strftime("%I:%M %p")}</p></div>', unsafe_allow_html=True)

# --- 5. THE INTERFACE TABS ---
tab1, tab2, tab3 = st.tabs(["💬 Baat Karein", "📁 Doctor Info", "📜 Purani Baatein"])

with tab1:
    st.markdown("### 📝 Message Likhein:")
    st.info(st.session_state.typed_text if st.session_state.typed_text else "Niche diye keyboard ka istemal karein...")

    # ADAPTIVE KEYBOARD GRID
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
    if col_b.button("⬅️ DEL"): backspace()

    st.divider()
    
    # ACTION BRIDGE
    col_send, col_sos = st.columns(2)
    
    if col_send.button("✅ BHEJEIN (SEND)"):
        if st.session_state.typed_text:
            with st.spinner("Sathi sun raha hai..."):
                # PERSONA: Polite, Caring Son/Doctor
                persona = f"""
                You are Sathi, a caring son and a respectful doctor. 
                1. ALWAYS use 'Aap' (polite). NEVER use 'Tum'.
                2. Mix English terms (Hinglish) like 'Medicine', 'Checkup', 'Health'.
                3. Be warm and emotional. 
                Current Time: {now.strftime('%I:%M %p')}
                """
                response = model.generate_content([persona, st.session_state.typed_text])
                
                # Save to Logger
                c.execute("INSERT INTO health_logs VALUES (?, ?, ?, ?)", 
                          (now.strftime("%Y-%m-%d %H:%M"), st.session_state.typed_text, response.text, "Chat"))
                conn.commit()
                
                st.markdown(f'<div style="background: white; border-left: 10px solid #2E7D32; padding: 20px; border-radius: 15px; font-size: 20px;"><b>Sathi:</b><br>{response.text}</div>', unsafe_allow_html=True)
                
                # Audio Output
                try:
                    audio = voice_client.generate(text=response.text, voice="Josh", model="eleven_multilingual_v2")
                    st.audio(b"".join(audio), format="audio/mp3", autoplay=True)
                except: st.warning("Audio system busy hai.")
                st.session_state.typed_text = ""

    with col_sos:
        if st.button("🆘 EMERGENCY", key="sos_btn"):
            doc_info = c.execute("SELECT name, phone FROM contacts WHERE role='Doctor'").fetchone()
            st.error(f"🚨 SOS ALERT! Calling {doc_info[0]} at {doc_info[1]}")
            st.markdown(f"**Ghabraiye mat Uncle-ji, Sathi ne {doc_info[0]} ko khabar bhej di hai. Hum saath hain.**")

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
