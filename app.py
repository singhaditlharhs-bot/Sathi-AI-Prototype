import streamlit as st
import datetime
import sqlite3
import google.generativeai as genai
import base64
from elevenlabs.client import ElevenLabs
from PIL import Image
import io
import os  # <--- Add this
os.environ["GOOGLE_API_USE_MTLS_ENDPOINT"] = "never"  # <--- Add this

# --- 1. INITIALIZATION & LIVING BRAIN DATABASE ---
conn = sqlite3.connect('sathi_memory.db', check_same_thread=False)
c = conn.cursor()
c.execute('CREATE TABLE IF NOT EXISTS health_logs (date TEXT, user_input TEXT, ai_response TEXT, tags TEXT)')
c.execute('CREATE TABLE IF NOT EXISTS contacts (role TEXT, name TEXT, phone TEXT)')
c.execute('CREATE TABLE IF NOT EXISTS reminders (date TEXT, task TEXT)') # New Alarm Table

# Default Doctor Info
c.execute("SELECT * FROM contacts WHERE role='Doctor'")
if not c.fetchone():
    c.execute("INSERT INTO contacts VALUES ('Doctor', 'Dr. Sharma (AIIMS)', '+91-9876543210')")
    conn.commit()

# API Keys
GEMINI_API_KEY = st.secrets.get("GEMINI_API_KEY")
ELEVEN_API_KEY = st.secrets.get("ELEVEN_API_KEY")
genai.configure(api_key=GEMINI_API_KEY)
# Change this line:
model = genai.GenerativeModel('gemini-1.5-flash') 
voice_client = ElevenLabs(api_key=ELEVEN_API_KEY)

# --- 2. AVATAR DISPLAY FUNCTION (Rectangular) ---
def display_media(file_path, is_video=False):
    try:
        with open(file_path, "rb") as f:
            data = f.read()
        b64 = base64.b64encode(data).decode()
        
        # Changed to Rectangular frame as requested
        style = "border-radius: 15px; border: 6px solid #2E7D32; object-fit: cover; box-shadow: 0 10px 30px rgba(0,0,0,0.3);"
        
        if is_video:
            st.markdown(f"""
                <div style="display: flex; justify-content: center; margin-bottom: 15px;">
                    <video width="300" height="250" autoplay loop muted style="{style}">
                        <source src="data:video/mp4;base64,{b64}" type="video/mp4">
                    </video>
                </div>
            """, unsafe_allow_html=True)
        else:
            st.markdown(f"""
                <div style="display: flex; justify-content: center; margin-bottom: 15px;">
                    <img src="data:image/png;base64,{b64}" width="300" height="250" style="{style}">
                </div>
            """, unsafe_allow_html=True)
    except FileNotFoundError:
        st.warning(f"File {file_path} not found. Ensure it is in the same folder.")

# --- 3. ADVANCED 3D UI STYLING ---
st.set_page_config(page_title="Sathi-AI", layout="wide")

st.markdown("""
    <style>
    .stApp { background-color: #FDF5E6; }
    
    /* Header Card */
    .header-card { 
        background: linear-gradient(135deg, #1B5E20, #2E7D32); 
        color: white; padding: 20px; border-radius: 20px; 
        text-align: center; margin-bottom: 20px;
    }

    /* 3D Connected Keyboard */
    .kb-boundary {
        background-color: #2C3E50;
        padding: 15px;
        border-radius: 15px;
        border: 4px solid #1A252F;
        box-shadow: inset 0 10px 20px rgba(0,0,0,0.5);
        margin-top: 10px;
    }
    
    /* Make columns tighter to look joined */
    [data-testid="column"] {
        padding: 0 2px !important; 
    }

    /* 3D Keys */
    .stButton>button {
        background-color: #E0E0E0 !important;
        color: #000 !important;
        font-weight: 900 !important;
        border-radius: 6px !important;
        height: 55px !important;
        font-size: 20px !important;
        border: 1px solid #999 !important;
        border-bottom: 6px solid #888 !important; /* 3D Depth */
        transition: all 0.1s;
        width: 100% !important;
        margin-bottom: 5px !important;
    }
    .stButton>button:active {
        transform: translateY(4px); /* Pushes down when clicked */
        border-bottom: 2px solid #888 !important;
    }

    /* Special Keys Colors */
    button[title="View fullscreen"] { display: none; } /* Hide image expander */
    </style>
""", unsafe_allow_html=True)

# --- 4. STATE LOGIC ---
if 'typed_text' not in st.session_state: st.session_state.typed_text = ""
if 'caps' not in st.session_state: st.session_state.caps = True
if 'is_talking' not in st.session_state: st.session_state.is_talking = False

def add_char(char): st.session_state.typed_text += char
def backspace(): st.session_state.typed_text = st.session_state.typed_text[:-1]

now = datetime.datetime.now()

# --- 5. THE INTERFACE ---
# Tab 1: Simple Bot, Tab 2: Full Doctor Experience, Tab 3: History & Alarms
tab1, tab2, tab3 = st.tabs(["🤖 Sathi Bot", "👨‍⚕️ Talk to Doctor", "⏰ Alarms & History"])

# ==========================================
# TAB 1: SATHI BOT (Simple Text/Speech)
# ==========================================
with tab1:
    st.markdown("### 💬 Sathi se baat karein")
    st.write("Aap hindi ya english mein sawal pooch sakte hain.")
    
    bot_input = st.text_input("Aapka Sawal (Your Question):", key="bot_input")
    if st.button("Poochhein (Ask Sathi)"):
        with st.spinner("Soch raha hoon..."):
            resp = model.generate_content(f"You are a helpful bilingual assistant (Hindi/English) for elders. Answer this warmly: {bot_input}")
            st.success(resp.text)

# ==========================================
# TAB 2: TALK TO DOCTOR (Avatar, Camera, 3D Keyboard)
# ==========================================
with tab2:
    # A. DOCTOR AVATAR
    st.markdown("<h2 style='text-align: center;'>Live Clinic</h2>", unsafe_allow_html=True)
    if st.session_state.is_talking:
        display_media("doctor_talking.mp4", is_video=True)
    else:
        display_media("doctor_static.png", is_video=False)

    # B. SENSORS: CAMERA & MIC
    col_cam, col_mic = st.columns(2)
    with col_cam:
        st.markdown("**📷 Dawai ya Report Dikhayein**")
        camera_photo = st.camera_input("Take a picture", label_visibility="collapsed")
    with col_mic:
        st.markdown("**🎙️ Bol Kar Batayein**")
        audio_val = st.audio_input("Record your voice", label_visibility="collapsed")

    # C. MESSAGE DISPLAY & 3D KEYBOARD
    st.info(st.session_state.typed_text if st.session_state.typed_text else "Likhne ke liye keyboard dabayein...")

    st.markdown('<div class="kb-boundary">', unsafe_allow_html=True)
    keys = [['Q', 'W', 'E', 'R', 'T', 'Y', 'U', 'I', 'O', 'P'],
            ['A', 'S', 'D', 'F', 'G', 'H', 'J', 'K', 'L'],
            ['Z', 'X', 'C', 'V', 'B', 'N', 'M']]
    
    for row in keys:
        cols = st.columns(len(row))
        for i, key in enumerate(row):
            display_key = key if st.session_state.caps else key.lower()
            if cols[i].button(display_key, key=f"doc_btn_{display_key}"):
                add_char(display_key)

    col_c, col_s, col_b, col_ent = st.columns([1.5, 4, 2, 2])
    if col_c.button("⬆️ CAPS"): st.session_state.caps = not st.session_state.caps
    if col_s.button("── SPACE ──"): add_char(" ")
    if col_b.button("⬅️ BACKSPACE"): backspace()
    
    # D. THE MAIN ENGINE (ENTER BUTTON)
    if col_ent.button("✅ ENTER", type="primary"):
        st.session_state.is_talking = True
        
        with st.spinner("Doctor is analyzing..."):
            prompt = f"""
            You are Dr. Sathi, a caring Indian doctor. Time: {now.strftime('%I:%M %p')}.
            1. If there is an image, analyze it (is it a medicine, injury, or prescription?). 
            2. Tell the user what you see and give advice. 
            3. If there is a medicine/dosage mentioned, end your response with exactly: ALARM: [Time/Frequency] to take [Medicine].
            4. Speak warmly in a mix of Hindi and English.
            User Text: {st.session_state.typed_text}
            """
            
            # Vision Logic: Combine Image and Text for Gemini
            contents = [prompt]
            if camera_photo:
                img = Image.open(camera_photo)
                contents.append(img)
                
            response = model.generate_content(contents)
            response_text = response.text
            
            # Extract Alarm Logic
            if "ALARM:" in response_text:
                alarm_part = response_text.split("ALARM:")[1].strip()
                c.execute("INSERT INTO reminders VALUES (?, ?)", (now.strftime("%Y-%m-%d"), alarm_part))
                conn.commit()
                response_text = response_text.split("ALARM:")[0].strip() # Hide the code word from user
            
            # Save Transcript
            c.execute("INSERT INTO health_logs VALUES (?, ?, ?, ?)", 
                      (now.strftime("%Y-%m-%d %H:%M"), "Used Camera/Keyboard", response_text, "Doctor Visit"))
            conn.commit()
            
            st.markdown(f'<div style="background: white; border-left: 10px solid #2E7D32; padding: 20px; border-radius: 10px;"><b>Doctor Transcript:</b><br>{response_text}</div>', unsafe_allow_html=True)
            
            # Audio Generation
            try:
                audio = voice_client.generate(text=response_text, voice="Josh", model="eleven_multilingual_v2")
                st.audio(b"".join(audio), format="audio/mp3", autoplay=True)
            except: 
                st.warning("Audio unavailable right now.")
            
            st.session_state.typed_text = ""
            
    st.markdown('</div>', unsafe_allow_html=True)

# ==========================================
# TAB 3: ALARMS & HISTORY
# ==========================================
with tab3:
    st.subheader("⏰ Reminders (Dawaii ka Samay)")
    alarms = c.execute("SELECT * FROM reminders").fetchall()
    if alarms:
        for a in alarms:
            st.info(f"📅 **{a[0]}:** {a[1]}")
    else:
        st.write("Koi naya reminder nahi hai.")
        
    st.divider()
    
    st.subheader("📜 Purani Baatein (History)")
    logs = c.execute("SELECT * FROM health_logs ORDER BY date DESC LIMIT 5").fetchall()
    for log in logs:
        st.write(f"**[{log[0]}]** \n* Sathi: {log[2]}")
