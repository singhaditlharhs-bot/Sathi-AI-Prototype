"""
╔══════════════════════════════════════════════════════════════════════════════╗
║                   SATHI-AI  v3.0  —  PRODUCTION BUILD                      ║
║  Elder-first health assistant | Bilingual | Doctor Bridge | Living Brain    ║
╚══════════════════════════════════════════════════════════════════════════════╝

NEW IN v3:
  • 4 tabs: Sathi Bot | Doctor Clinic | Alarms+History | SOS/Call
  • Gemini 2.0 Flash via google-genai v1 (stable REST, no 404s)
  • Thread-safe SQLite Living Brain (WAL mode)
  • Full A-Z 3D keyboard with Caps, Del, Space, Clear
  • Voice input (mic) + transcription via Gemini
  • ElevenLabs TTS with replay loop button
  • Auto-alarm extraction + manual alarm setting
  • Prescription tracker
  • Doctor summary generator (for real doctor visits)
  • SOS / call buttons with tel: links
  • Elder-first UI: large text, high contrast, responsive
  • Hinglish / Hindi / English language toggle
  • Polite "Aap" language throughout
"""

# ─────────────────────────────────────────────────────────────────────────────
# IMPORTS
# ─────────────────────────────────────────────────────────────────────────────
import streamlit as st
import datetime
import sqlite3
import threading
import base64
import io

from PIL import Image
from google import genai
from google.genai import types
from elevenlabs.client import ElevenLabs

# ─────────────────────────────────────────────────────────────────────────────
# 1. PAGE CONFIG  — must be very first Streamlit call
# ─────────────────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Sathi-AI",
    layout="wide",
    page_icon="🏥",
    initial_sidebar_state="collapsed",
)

# ─────────────────────────────────────────────────────────────────────────────
# 2. THREAD-SAFE DATABASE  (Living Brain)
# ─────────────────────────────────────────────────────────────────────────────
_DB_LOCK = threading.Lock()


@st.cache_resource
def get_db():
    conn = sqlite3.connect("sathi_memory.db", check_same_thread=False)
    conn.execute("PRAGMA journal_mode=WAL")

    # Create tables fresh if they don't exist
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS health_logs (
            id       INTEGER PRIMARY KEY AUTOINCREMENT,
            date     TEXT,
            user_msg TEXT,
            ai_reply TEXT,
            summary  TEXT,
            tags     TEXT
        );
        CREATE TABLE IF NOT EXISTS contacts (
            role  TEXT PRIMARY KEY,
            name  TEXT,
            phone TEXT
        );
        CREATE TABLE IF NOT EXISTS reminders (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            set_date   TEXT,
            alarm_time TEXT,
            medicine   TEXT,
            done       INTEGER DEFAULT 0
        );
        CREATE TABLE IF NOT EXISTS prescriptions (
            id       INTEGER PRIMARY KEY AUTOINCREMENT,
            date     TEXT,
            medicine TEXT,
            dosage   TEXT,
            duration TEXT
        );
    """)

    # MIGRATION: safely add missing columns to existing tables
    migrations = [
        ("health_logs",   "id",      "INTEGER"),
        ("health_logs",   "summary", "TEXT"),
        ("reminders",     "id",      "INTEGER"),
        ("reminders",     "done",    "INTEGER DEFAULT 0"),
        ("prescriptions", "id",      "INTEGER"),
        ("prescriptions", "dosage",  "TEXT"),
        ("prescriptions", "duration","TEXT"),
    ]
    for table, col, col_type in migrations:
        try:
            conn.execute(f"ALTER TABLE {table} ADD COLUMN {col} {col_type}")
            conn.commit()
        except Exception:
            pass  # column already exists — safe to ignore

    # Seed default contacts
    conn.execute(
        "INSERT OR IGNORE INTO contacts VALUES "
        "('Doctor','Dr. Sharma (AIIMS)','+91-9876543210')"
    )
    conn.execute(
        "INSERT OR IGNORE INTO contacts VALUES "
        "('Emergency','Emergency / Ambulance','112')"
    )
    conn.commit()
    return conn


def db_write(sql, params=()):
    c = get_db()
    with _DB_LOCK:
        c.execute(sql, params)
        c.commit()


def db_read(sql, params=()):
    c = get_db()
    with _DB_LOCK:
        return c.execute(sql, params).fetchall()


# ─────────────────────────────────────────────────────────────────────────────
# 3. API CLIENTS
# ─────────────────────────────────────────────────────────────────────────────
GEMINI_KEY  = st.secrets.get("GEMINI_API_KEY", "")
ELEVEN_KEY  = st.secrets.get("ELEVEN_API_KEY", "")
GEMINI_MDL  = "gemini-2.0-flash"


@st.cache_resource
def get_gemini():
    return genai.Client(api_key=GEMINI_KEY)


@st.cache_resource
def get_voice():
    return ElevenLabs(api_key=ELEVEN_KEY)


# ─────────────────────────────────────────────────────────────────────────────
# 4. GEMINI CALL  (text + optional vision or audio)
# ─────────────────────────────────────────────────────────────────────────────
def call_gemini(prompt: str, pil_image=None) -> str:
    client = get_gemini()
    parts = []
    if pil_image:
        buf = io.BytesIO()
        pil_image.save(buf, format="JPEG", quality=85)
        parts.append(types.Part.from_bytes(data=buf.getvalue(), mime_type="image/jpeg"))
    parts.append(types.Part.from_text(text=prompt))
    resp = client.models.generate_content(
        model=GEMINI_MDL,
        contents=parts,
        config=types.GenerateContentConfig(max_output_tokens=1500, temperature=0.7),
    )
    return resp.text.strip()


def transcribe_audio(audio_bytes: bytes) -> str:
    client = get_gemini()
    resp = client.models.generate_content(
        model=GEMINI_MDL,
        contents=[
            types.Part.from_bytes(data=audio_bytes, mime_type="audio/wav"),
            types.Part.from_text(text="Transcribe exactly what is said in this audio clip."),
        ],
        config=types.GenerateContentConfig(max_output_tokens=300),
    )
    return resp.text.strip()


# ─────────────────────────────────────────────────────────────────────────────
# 5. TTS
# ─────────────────────────────────────────────────────────────────────────────
def speak(text: str):
    """Generate audio bytes from ElevenLabs, return bytes or None."""
    try:
        client = get_voice()
        gen = client.generate(text=text[:800], voice="Josh", model="eleven_multilingual_v2")
        buf = b"".join(chunk for chunk in gen if isinstance(chunk, bytes))
        return buf if buf else None
    except Exception as e:
        st.warning(f"🔇 Voice unavailable: {e}")
        return None


# ─────────────────────────────────────────────────────────────────────────────
# 6. ALARM PARSER
# ─────────────────────────────────────────────────────────────────────────────
def parse_alarms(text: str) -> str:
    """Extract ALARM: lines, save to DB, return cleaned text."""
    now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    clean = []
    for line in text.split("\n"):
        if line.strip().startswith("ALARM:"):
            parts = line.replace("ALARM:", "").strip().split("|")
            alarm_time = parts[0].strip() if len(parts) > 0 else "As directed"
            medicine   = parts[1].strip() if len(parts) > 1 else "Medicine"
            dosage     = parts[2].strip() if len(parts) > 2 else ""
            duration   = parts[3].strip() if len(parts) > 3 else ""
            db_write(
                "INSERT INTO reminders (set_date,alarm_time,medicine) VALUES (?,?,?)",
                (now_str, alarm_time, f"{medicine} {dosage} {duration}".strip()),
            )
            db_write(
                "INSERT INTO prescriptions (date,medicine,dosage,duration) VALUES (?,?,?,?)",
                (now_str[:10], medicine, dosage, duration),
            )
        else:
            clean.append(line)
    return "\n".join(clean).strip()


# ─────────────────────────────────────────────────────────────────────────────
# 7. LANGUAGE SYSTEM
# ─────────────────────────────────────────────────────────────────────────────
LANG_PROMPT = {
    "hinglish": (
        "Aap warmly Hinglish mein bolein — Hindi aur English ka natural mix. "
        "'Aap' use karein (kabhi 'Tum' nahi). Ek caring bete ya respectful doctor ki tarah bolein. "
        "Sentences chote aur simple rakhein buzurgon ke liye."
    ),
    "hindi": (
        "Sirf shuddh Hindi mein uttar dein. 'Aap' ka prayog karein. "
        "Buzurgon ke liye saral aur spasht bhaasha mein likhein."
    ),
    "english": (
        "Speak only in clear, simple English. Use 'you' respectfully. "
        "Keep sentences short and easy for elderly users."
    ),
}

LANG_LABEL = {"hinglish": "🇮🇳 Hinglish", "hindi": "🕉️ Hindi", "english": "🇬🇧 English"}

UI = {
    "hinglish": {
        "t1":"🤖 Sathi Bot", "t2":"👨‍⚕️ Doctor Clinic", "t3":"⏰ Alarms", "t4":"🆘 SOS",
        "greet":"Namaste! Aap kya poochna chahte hain?",
        "hint":"Keyboard se likhein ya mic dabayein...",
        "ask":"🙏 Poochhein", "send":"✅ Bhejein", "replay":"🔁 Phir Sunein",
        "alarm_saved":"✅ Alarm set ho gaya!",
        "clinic":"🏥 Live Clinic — Dr. Sathi",
        "ready":"🔵 Dr. Sathi ready hain",
        "talking":"🟢 Doctor jawab de rahe hain...",
    },
    "hindi": {
        "t1":"🤖 साथी Bot", "t2":"👨‍⚕️ Doctor Clinic", "t3":"⏰ अलार्म", "t4":"🆘 SOS",
        "greet":"नमस्ते! आप क्या पूछना चाहते हैं?",
        "hint":"कीबोर्ड से लिखें या माइक दबाएं...",
        "ask":"🙏 पूछें", "send":"✅ भेजें", "replay":"🔁 फिर सुनें",
        "alarm_saved":"✅ अलार्म सेट हो गया!",
        "clinic":"🏥 Live Clinic — Dr. साथी",
        "ready":"🔵 Dr. साथी तैयार हैं",
        "talking":"🟢 Doctor उत्तर दे रहे हैं...",
    },
    "english": {
        "t1":"🤖 Sathi Bot", "t2":"👨‍⚕️ Doctor Clinic", "t3":"⏰ Alarms", "t4":"🆘 SOS",
        "greet":"Hello! How can I help you today?",
        "hint":"Type using the keyboard or press the mic...",
        "ask":"🙏 Ask Sathi", "send":"✅ Send", "replay":"🔁 Replay",
        "alarm_saved":"✅ Alarm has been set!",
        "clinic":"🏥 Live Clinic — Dr. Sathi",
        "ready":"🔵 Dr. Sathi is ready",
        "talking":"🟢 Doctor is responding...",
    },
}


# ─────────────────────────────────────────────────────────────────────────────
# 8. AVATAR DISPLAY
# ─────────────────────────────────────────────────────────────────────────────
AV_CSS = (
    "border-radius:20px;border:5px solid #2E7D32;"
    "object-fit:cover;box-shadow:0 8px 32px rgba(46,125,50,0.35);"
    "width:100%;max-width:320px;height:260px;"
)

def show_avatar(talking: bool):
    if talking:
        try:
            with open("doctor_talking.mp4", "rb") as f:
                b64 = base64.b64encode(f.read()).decode()
            st.markdown(
                f'<div style="text-align:center;"><video autoplay loop muted style="{AV_CSS}">'
                f'<source src="data:video/mp4;base64,{b64}" type="video/mp4"></video></div>',
                unsafe_allow_html=True,
            )
            return
        except FileNotFoundError:
            pass
    try:
        with open("doctor_static.png", "rb") as f:
            b64 = base64.b64encode(f.read()).decode()
        st.markdown(
            f'<div style="text-align:center;"><img src="data:image/png;base64,{b64}" style="{AV_CSS}"></div>',
            unsafe_allow_html=True,
        )
    except FileNotFoundError:
        st.markdown(
            '<div style="text-align:center;font-size:110px;">👨‍⚕️</div>',
            unsafe_allow_html=True,
        )


# ─────────────────────────────────────────────────────────────────────────────
# 9. CSS — Elder-first, professional, responsive
# ─────────────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Baloo+2:wght@400;600;800&display=swap');

:root {
  --g-dark:#1B5E20; --g-mid:#2E7D32; --g-lt:#4CAF50; --g-pale:#E8F5E9;
  --amber:#FF8F00;  --amber-lt:#FFF8E1;
  --red:#C62828;    --red-lt:#FFEBEE;
  --blue:#1565C0;
  --cream:#FFFDE7;  --shadow:0 4px 24px rgba(0,0,0,0.12); --r:18px;
}

html,body,.stApp {
  background:linear-gradient(150deg,#f0f7f0 0%,#fffde7 60%,#e8f5e9 100%) !important;
  font-family:'Baloo 2',sans-serif !important;
  color:#1A1A1A !important;
}

/* ── Header ── */
.sathi-hdr {
  background:linear-gradient(135deg,var(--g-dark),var(--g-mid));
  color:white; padding:16px 24px; border-radius:var(--r);
  margin-bottom:18px; box-shadow:var(--shadow);
  display:flex; align-items:center; gap:14px; flex-wrap:wrap;
}
.sathi-hdr h1 {font-size:2rem;margin:0;font-weight:800;}
.sathi-hdr p  {font-size:1rem;margin:0;opacity:.88;}
.badge {background:var(--amber);color:#fff;font-size:.7rem;font-weight:700;
        padding:2px 9px;border-radius:20px;margin-left:8px;}

/* ── Tabs ── */
.stTabs [data-baseweb="tab-list"] {
  gap:6px; background:white; padding:6px;
  border-radius:var(--r); box-shadow:var(--shadow); flex-wrap:wrap;
}
.stTabs [data-baseweb="tab"] {
  font-size:1.05rem !important; font-weight:700 !important;
  padding:10px 16px !important; border-radius:12px !important;
  color:#424242 !important; transition:all .2s !important;
}
.stTabs [aria-selected="true"] {
  background:var(--g-mid) !important; color:white !important;
  box-shadow:0 2px 12px rgba(46,125,50,.3) !important;
}

/* ── Cards ── */
.card {background:white;border-radius:var(--r);padding:18px;
       box-shadow:var(--shadow);margin-bottom:14px;border-left:6px solid var(--g-mid);}
.doc-resp {background:linear-gradient(135deg,#f1f8e9,#fff);border:2px solid var(--g-lt);
           border-radius:var(--r);padding:20px;margin:14px 0;
           font-size:1.12rem;line-height:1.8;
           box-shadow:0 2px 16px rgba(76,175,80,.15);}
.sum-box  {background:var(--amber-lt);border:2px solid var(--amber);
           border-radius:12px;padding:14px 18px;margin-top:10px;
           font-size:1.05rem;font-weight:600;}
.presc-box{background:var(--g-pale);border:2px solid var(--g-lt);
           border-radius:12px;padding:12px 16px;margin:6px 0;}
.urgent   {background:var(--red-lt);border:2px solid var(--red);
           border-radius:12px;padding:12px 16px;margin-top:8px;
           font-weight:700;color:var(--red);}
.kb-display{background:#0d2518;border:2px solid var(--g-mid);border-radius:12px;
            padding:14px 18px;min-height:58px;color:#69F0AE;
            font-size:1.3rem;font-family:'Courier New',monospace;font-weight:700;
            margin-bottom:10px;letter-spacing:1px;word-break:break-all;
            box-shadow:inset 0 2px 8px rgba(0,0,0,.5);}
.kb-wrap  {background:#1a2332;border-radius:20px;padding:16px 12px 12px;
           border:3px solid #0d1520;
           box-shadow:0 12px 40px rgba(0,0,0,.5),inset 0 2px 4px rgba(255,255,255,.04);
           margin-top:12px;}
.clinic-title{text-align:center;font-size:1.5rem;font-weight:800;
              color:var(--g-dark);margin-bottom:10px;}

/* ── All buttons base ── */
[data-testid="column"]{padding:0 2px !important;}
.stButton>button {
  background:linear-gradient(180deg,#f0f0f0,#d8d8d8) !important;
  color:#111 !important; font-weight:800 !important;
  border-radius:7px !important; height:50px !important; font-size:1.05rem !important;
  border-top:1px solid #fff !important; border-left:1px solid #ccc !important;
  border-right:1px solid #aaa !important; border-bottom:5px solid #888 !important;
  transition:all .08s !important; width:100% !important; margin-bottom:4px !important;
  box-shadow:0 2px 4px rgba(0,0,0,.22) !important;
}
.stButton>button:hover {
  background:linear-gradient(180deg,#fff,#e8e8e8) !important;
  transform:translateY(-1px) !important;
}
.stButton>button:active {
  transform:translateY(4px) !important;
  border-bottom:1px solid #888 !important;
  box-shadow:none !important;
}
/* Primary = ENTER/Send — green */
button[kind="primary"] {
  background:linear-gradient(180deg,#4CAF50,#2E7D32) !important;
  color:white !important; border-bottom:5px solid #1B5E20 !important;
}
/* Space — blue */
.sp .stButton>button  {background:linear-gradient(180deg,#42A5F5,#1565C0) !important;
                        color:white !important;border-bottom:5px solid #0d3a77 !important;}
/* Del — orange */
.dl .stButton>button  {background:linear-gradient(180deg,#FF7043,#BF360C) !important;
                        color:white !important;border-bottom:5px solid #7f2600 !important;}
/* Caps — purple */
.cp .stButton>button  {background:linear-gradient(180deg,#AB47BC,#6A1B9A) !important;
                        color:white !important;border-bottom:5px solid #4a0072 !important;}
/* Mic — amber */
.mc .stButton>button  {background:linear-gradient(180deg,#FFCA28,#F57F17) !important;
                        color:#111 !important;border-bottom:5px solid #a35000 !important;
                        font-size:1.3rem !important;}
/* Replay — teal */
.rp .stButton>button  {background:linear-gradient(180deg,#26C6DA,#00838F) !important;
                        color:white !important;border-bottom:5px solid #005662 !important;}
/* Clear — grey */
.cl .stButton>button  {background:linear-gradient(180deg,#90A4AE,#546E7A) !important;
                        color:white !important;border-bottom:5px solid #263238 !important;}

/* ── SOS / Call ── */
.sos .stButton>button {
  background:linear-gradient(135deg,#C62828,#E53935) !important;
  color:white !important;font-size:1.35rem !important;font-weight:900 !important;
  height:68px !important;border-radius:16px !important;
  border-bottom:5px solid #7f0000 !important;
  box-shadow:0 6px 24px rgba(198,40,40,.4) !important;
  animation:pred 2s infinite;
}
@keyframes pred{0%,100%{box-shadow:0 6px 24px rgba(198,40,40,.4);}
                50%     {box-shadow:0 6px 36px rgba(198,40,40,.7);}}
.dc .stButton>button {
  background:linear-gradient(135deg,#1565C0,#1976D2) !important;
  color:white !important;font-size:1.15rem !important;font-weight:800 !important;
  height:62px !important;border-radius:16px !important;
  border-bottom:5px solid #0d3a77 !important;
  box-shadow:0 4px 20px rgba(21,101,192,.35) !important;
}

/* ── Responsive ── */
@media(max-width:768px){
  .sathi-hdr h1{font-size:1.4rem;}
  .stButton>button{height:44px !important;font-size:.95rem !important;}
}
@media(max-width:480px){
  .sathi-hdr{flex-direction:column;text-align:center;}
  .stButton>button{height:40px !important;font-size:.85rem !important;}
}
button[title="View fullscreen"]{display:none !important;}
#MainMenu,footer,header{visibility:hidden !important;}
.block-container{padding-top:.8rem !important;}
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────────────────
# 10. SESSION STATE
# ─────────────────────────────────────────────────────────────────────────────
for k, v in {
    "typed": "", "caps": True, "talking": False,
    "lang": "hinglish", "last_audio": None,
    "last_reply": "", "last_summary": "",
}.items():
    if k not in st.session_state:
        st.session_state[k] = v

NOW = datetime.datetime.now()

# ─────────────────────────────────────────────────────────────────────────────
# 11. HEADER + LANGUAGE BAR
# ─────────────────────────────────────────────────────────────────────────────
lang = st.session_state.lang
ui   = UI[lang]

st.markdown(f"""
<div class="sathi-hdr">
  <span style="font-size:2.8rem;">🏥</span>
  <div>
    <h1>Sathi-AI <span class="badge">v3</span></h1>
    <p>Aapka Swasthya Saathi — Your Caring Health Companion</p>
  </div>
  <div style="margin-left:auto;text-align:right;font-size:.95rem;opacity:.85;">
    📅 {NOW.strftime('%d %b %Y')}<br>🕐 {NOW.strftime('%I:%M %p')}
  </div>
</div>
""", unsafe_allow_html=True)

# Language toggle
lc = st.columns([1, 1, 1, 5])
with lc[0]:
    if st.button("🇮🇳 Hinglish", key="l1"):
        st.session_state.lang = "hinglish"; st.rerun()
with lc[1]:
    if st.button("🕉️ Hindi", key="l2"):
        st.session_state.lang = "hindi"; st.rerun()
with lc[2]:
    if st.button("🇬🇧 English", key="l3"):
        st.session_state.lang = "english"; st.rerun()
with lc[3]:
    st.markdown(
        f"<span style='color:#2E7D32;font-weight:700;'>"
        f"Active language: {LANG_LABEL[lang]}</span>",
        unsafe_allow_html=True,
    )

# ─────────────────────────────────────────────────────────────────────────────
# 12. TABS
# ─────────────────────────────────────────────────────────────────────────────
tab1, tab2, tab3, tab4 = st.tabs([ui["t1"], ui["t2"], ui["t3"], ui["t4"]])


# ══════════════════════════════════════════════════════════════════════════════
# TAB 1 — SATHI BOT
# ══════════════════════════════════════════════════════════════════════════════
with tab1:
    st.markdown(f'<div class="card"><b style="font-size:1.3rem;">💬 {ui["greet"]}</b>'
                '<br>Koi bhi sawaal poochhein — sehat, dawai, ya zindagi ke baare mein.</div>',
                unsafe_allow_html=True)

    bot_q = st.text_area("Aapka Sawaal:", height=100,
                          placeholder=ui["hint"], key="bot_q")
    b1, b2 = st.columns([3, 1])
    with b1:
        ask = st.button(ui["ask"], key="bot_ask", type="primary", use_container_width=True)
    with b2:
        st.markdown('<div class="mc">', unsafe_allow_html=True)
        st.button("🎙️ Mic", key="mc_bot", use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)

    audio_bot = st.audio_input("🎙️ Ya yahan bolein:", key="ab")

    if ask or audio_bot:
        query = bot_q.strip()
        if audio_bot and not query:
            with st.spinner("Aapki awaaz sun raha hoon..."):
                try:
                    query = transcribe_audio(audio_bot.read())
                except Exception as e:
                    st.warning(f"Transcription error: {e}")

        if query:
            with st.spinner("Sathi soch raha hai..."):
                try:
                    prompt = (
                        f"{LANG_PROMPT[lang]}\n"
                        "You are Sathi, a warm companion for elderly people. "
                        "Answer simply and kindly. Avoid complex medical jargon.\n"
                        f"Question: {query}"
                    )
                    reply = call_gemini(prompt)
                    st.markdown(
                        f'<div class="doc-resp"><b>🤖 Sathi:</b><br>{reply}</div>',
                        unsafe_allow_html=True,
                    )
                    audio = speak(reply)
                    if audio:
                        st.session_state.last_audio = audio
                        st.audio(audio, format="audio/mp3", autoplay=True)
                    db_write(
                        "INSERT INTO health_logs (date,user_msg,ai_reply,tags) VALUES (?,?,?,?)",
                        (NOW.strftime("%Y-%m-%d %H:%M"), query, reply, "Sathi Bot"),
                    )
                except Exception as e:
                    st.error(f"⚠️ Error: {e}")
        else:
            st.warning("Kuch toh likhein ya bolein! 🙏")

    if st.session_state.last_audio:
        st.markdown('<div class="rp">', unsafe_allow_html=True)
        if st.button(ui["replay"], key="rp_bot", use_container_width=True):
            st.audio(st.session_state.last_audio, format="audio/mp3", autoplay=True)
        st.markdown('</div>', unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# TAB 2 — DOCTOR CLINIC
# ══════════════════════════════════════════════════════════════════════════════
with tab2:
    st.markdown(f'<div class="clinic-title">{ui["clinic"]}</div>', unsafe_allow_html=True)

    av_col, inp_col = st.columns([1, 1], gap="large")

    with av_col:
        show_avatar(st.session_state.talking)
        status_txt = ui["talking"] if st.session_state.talking else ui["ready"]
        st.markdown(
            f'<div style="text-align:center;font-weight:700;color:#2E7D32;'
            f'font-size:1rem;margin-top:8px;">{status_txt}</div>',
            unsafe_allow_html=True,
        )
        if st.session_state.last_audio:
            st.markdown('<div class="rp" style="margin-top:10px;">', unsafe_allow_html=True)
            if st.button(f"🔁 {ui['replay']}", key="rp_doc", use_container_width=True):
                st.audio(st.session_state.last_audio, format="audio/mp3", autoplay=True)
            st.markdown('</div>', unsafe_allow_html=True)

    with inp_col:
        st.markdown("**📷 Camera — Dawai ya Chot Dikhayein**")
        cam_photo = st.camera_input("Cam", label_visibility="collapsed", key="cam")
        st.markdown("**🖼️ Ya Photo Upload Karein**")
        up_img = st.file_uploader("Upload", type=["jpg","jpeg","png"],
                                   label_visibility="collapsed", key="up")
        st.markdown("**🎙️ Bolkar Batayein**")
        doc_audio = st.audio_input("Voice", label_visibility="collapsed", key="da")

    # Show persisted reply
    if st.session_state.last_reply:
        st.markdown(
            f'<div class="doc-resp"><b>👨‍⚕️ Dr. Sathi:</b><br>'
            f'{st.session_state.last_reply}</div>',
            unsafe_allow_html=True,
        )
        if st.session_state.last_summary:
            st.markdown(
                f'<div class="sum-box">📋 <b>Summary:</b> {st.session_state.last_summary}</div>',
                unsafe_allow_html=True,
            )

    # ── 3D Keyboard ────────────────────────────────────────────────────────
    st.markdown("---")
    disp = st.session_state.typed if st.session_state.typed else ui["hint"]
    st.markdown(
        f'<div class="kb-wrap"><div class="kb-display">{disp}</div>',
        unsafe_allow_html=True,
    )

    for row in [list("QWERTYUIOP"), list("ASDFGHJKL"), list("ZXCVBNM")]:
        cols = st.columns(len(row))
        for i, ch in enumerate(row):
            lbl = ch if st.session_state.caps else ch.lower()
            if cols[i].button(lbl, key=f"k_{ch}"):
                st.session_state.typed += lbl
                st.rerun()

    r1, r2, r3, r4, r5 = st.columns([1.1, 1.1, 3.5, 1.2, 1.8])
    with r1:
        st.markdown('<div class="cp">', unsafe_allow_html=True)
        if st.button("⬆️ CAPS", key="caps_k", use_container_width=True):
            st.session_state.caps = not st.session_state.caps; st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)
    with r2:
        st.markdown('<div class="dl">', unsafe_allow_html=True)
        if st.button("⌫ DEL", key="del_k", use_container_width=True):
            st.session_state.typed = st.session_state.typed[:-1]; st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)
    with r3:
        st.markdown('<div class="sp">', unsafe_allow_html=True)
        if st.button("──────── SPACE ────────", key="sp_k", use_container_width=True):
            st.session_state.typed += " "; st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)
    with r4:
        st.markdown('<div class="cl">', unsafe_allow_html=True)
        if st.button("🗑 CLR", key="cl_k", use_container_width=True):
            st.session_state.typed = ""; st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)
    with r5:
        send_clicked = st.button(
            ui["send"], key="send_k", type="primary", use_container_width=True
        )

    st.markdown('</div>', unsafe_allow_html=True)  # close kb-wrap

    # ── SEND LOGIC ─────────────────────────────────────────────────────────
    if send_clicked:
        user_text = st.session_state.typed.strip()
        pil_img   = None
        if cam_photo:
            pil_img = Image.open(cam_photo)
        elif up_img:
            pil_img = Image.open(up_img)

        # Voice → text if no keyboard input
        if not user_text and doc_audio:
            with st.spinner("Awaaz sun raha hoon..."):
                try:
                    user_text = transcribe_audio(doc_audio.read())
                    st.session_state.typed = user_text
                except Exception as e:
                    st.warning(f"Voice error: {e}")

        if not user_text and not pil_img:
            st.warning("Kuch likhein, bolein, ya photo lo pehle! 🙏")
        else:
            st.session_state.talking = True
            prompt = f"""
{LANG_PROMPT[lang]}

You are Dr. Sathi — a caring, experienced Indian doctor speaking to an elderly patient.
Time: {NOW.strftime('%I:%M %p, %d %B %Y')}.

RULES:
1. Be warm, patient, and respectful. Use "Aap" in Hindi/Hinglish.
2. If image provided: analyse it (medicine label → purpose/dosage; injury → first aid;
   prescription/report → simple summary).
3. End with a SUMMARY line: SUMMARY: [one clear sentence]
4. For any medicine/dosage mentioned, add: ALARM: [time(s)] | [Medicine] | [Dosage] | [Duration]
5. If symptoms are serious, add: URGENT: [advice]
6. Close with a kind, encouraging sentence.

Patient message: {user_text if user_text else "(No text — analyse image only)"}
"""
            with st.spinner("Doctor soch rahe hain..."):
                try:
                    raw = call_gemini(prompt, pil_img)
                    clean = parse_alarms(raw)

                    summary, urgent = "", ""
                    if "SUMMARY:" in clean:
                        p = clean.split("SUMMARY:")
                        clean   = p[0].strip()
                        summary = p[1].strip().split("\n")[0]
                    if "URGENT:" in clean:
                        p = clean.split("URGENT:")
                        clean  = p[0].strip()
                        urgent = p[1].strip().split("\n")[0]

                    st.session_state.last_reply   = clean
                    st.session_state.last_summary = summary

                    db_write(
                        "INSERT INTO health_logs (date,user_msg,ai_reply,summary,tags) "
                        "VALUES (?,?,?,?,?)",
                        (NOW.strftime("%Y-%m-%d %H:%M"),
                         user_text or "(Image)", clean, summary, "Doctor Visit"),
                    )

                    st.markdown(
                        f'<div class="doc-resp"><b>👨‍⚕️ Dr. Sathi:</b><br>{clean}</div>',
                        unsafe_allow_html=True,
                    )
                    if summary:
                        st.markdown(
                            f'<div class="sum-box">📋 <b>Summary:</b> {summary}</div>',
                            unsafe_allow_html=True,
                        )
                    if urgent:
                        st.markdown(
                            f'<div class="urgent">🚨 <b>URGENT:</b> {urgent}</div>',
                            unsafe_allow_html=True,
                        )
                    st.success(ui["alarm_saved"])

                    audio = speak(f"{clean}. {summary}")
                    if audio:
                        st.session_state.last_audio = audio
                        st.audio(audio, format="audio/mp3", autoplay=True)

                except Exception as e:
                    st.error(f"⚠️ Doctor ka jawab nahi aaya: {e}")
                finally:
                    st.session_state.talking = False
                    st.session_state.typed   = ""


# ══════════════════════════════════════════════════════════════════════════════
# TAB 3 — ALARMS + PRESCRIPTIONS + HISTORY
# ══════════════════════════════════════════════════════════════════════════════
with tab3:
    s1, s2, s3 = st.tabs(["⏰ Alarms", "💊 Prescriptions", "📜 History"])

    with s1:
        st.markdown("### ⏰ Dawai ke Alarms")
        with st.expander("➕ Nayi Alarm Manually Set Karein"):
            m1, m2, m3 = st.columns(3)
            with m1: at = st.text_input("Samay (e.g. 8:00 AM)", key="at")
            with m2: am = st.text_input("Dawai ka naam", key="am")
            with m3:
                st.write(""); st.write("")
                if st.button("✅ Set", key="set_al"):
                    if at and am:
                        db_write(
                            "INSERT INTO reminders (set_date,alarm_time,medicine) VALUES (?,?,?)",
                            (NOW.strftime("%Y-%m-%d %H:%M"), at, am),
                        )
                        st.success(ui["alarm_saved"]); st.rerun()
                    else:
                        st.warning("Samay aur dawai dono bharen!")

        alarms = db_read(
            "SELECT id,set_date,alarm_time,medicine,done FROM reminders ORDER BY id DESC"
        )
        if alarms:
            for aid, adate, atime, amed, adone in alarms:
                icon = "✅" if adone else "⏰"
                bg   = "#f5f5f5" if adone else "#FFF8E1"
                bc   = "#bbb"    if adone else "#FF8F00"
                st.markdown(f"""
                <div style="background:{bg};border:2px solid {bc};border-radius:12px;
                     padding:12px 16px;margin:6px 0;">
                  <b>{icon} {atime}</b> — {amed}
                  <div style="font-size:.82rem;color:#666;">Set: {adate}</div>
                </div>""", unsafe_allow_html=True)
                c1, c2 = st.columns(2)
                with c1:
                    if not adone and st.button("✔ Done", key=f"d_{aid}"):
                        db_write("UPDATE reminders SET done=1 WHERE id=?", (aid,)); st.rerun()
                with c2:
                    if st.button("🗑 Del", key=f"da_{aid}"):
                        db_write("DELETE FROM reminders WHERE id=?", (aid,)); st.rerun()
        else:
            st.info("Koi alarm nahi hai. Doctor se baat karne par automatic alarm set hogi.")

    with s2:
        st.markdown("### 💊 Prescriptions")
        pres = db_read("SELECT date,medicine,dosage,duration FROM prescriptions ORDER BY id DESC")
        if pres:
            for pdate, pmed, pdos, pdur in pres:
                st.markdown(f"""
                <div class="presc-box">
                  💊 <b>{pmed}</b>
                  {f'— {pdos}' if pdos else ''} {f'({pdur})' if pdur else ''}
                  <div style="font-size:.82rem;color:#888;">📅 {pdate}</div>
                </div>""", unsafe_allow_html=True)
        else:
            st.info("Koi prescription nahi hai abhi.")

    with s3:
        st.markdown("### 📜 Health History")
        logs = db_read(
            "SELECT date,user_msg,ai_reply,summary,tags "
            "FROM health_logs ORDER BY id DESC LIMIT 20"
        )
        if logs:
            for ldate, luser, lreply, lsum, ltag in logs:
                with st.expander(f"🕐 {ldate}  |  🏷 {ltag or 'General'}"):
                    st.markdown(f"**🗣 Aapne kaha:** {luser}")
                    st.markdown(
                        f'<div style="background:#f9f9f9;border-radius:8px;'
                        f'padding:10px;font-size:.95rem;">{lreply}</div>',
                        unsafe_allow_html=True,
                    )
                    if lsum:
                        st.markdown(f"**📋 Summary:** {lsum}")
        else:
            st.info("Koi history nahi hai abhi.")


# ══════════════════════════════════════════════════════════════════════════════
# TAB 4 — SOS / CALL
# ══════════════════════════════════════════════════════════════════════════════
with tab4:
    st.markdown("### 🆘 Emergency & Doctor Contact")
    st.markdown("""
    <div class="card" style="border-left-color:#C62828;">
      <b style="color:#C62828;font-size:1.15rem;">⚠️ Zaruri Suchna</b><br>
      Agar aapko bahut takleef hai ya emergency hai —
      neeche diye button se seedha call karein.
    </div>""", unsafe_allow_html=True)

    contacts = db_read("SELECT role,name,phone FROM contacts")
    for role, name, phone in contacts:
        icon  = "🆘" if role == "Emergency" else "👨‍⚕️"
        color = "#C62828" if role == "Emergency" else "#1565C0"
        st.markdown(f"""
        <div style="background:white;border:2px solid {color};border-radius:14px;
             padding:16px 20px;margin:10px 0;display:flex;align-items:center;
             gap:14px;box-shadow:0 4px 16px rgba(0,0,0,.1);">
          <span style="font-size:2.2rem;">{icon}</span>
          <div style="flex:1;">
            <div style="font-size:1.15rem;font-weight:800;color:{color};">{name}</div>
            <div style="font-size:1.4rem;font-weight:700;letter-spacing:1px;">{phone}</div>
            <div style="font-size:.82rem;color:#666;">{role}</div>
          </div>
          <a href="tel:{phone}"
             style="background:{color};color:white;padding:12px 22px;border-radius:10px;
                    font-weight:800;font-size:1rem;text-decoration:none;
                    box-shadow:0 2px 8px rgba(0,0,0,.2);">
            📞 Call
          </a>
        </div>""", unsafe_allow_html=True)

    st.markdown("---")
    st.markdown("### ➕ Naya Contact Jorhein")
    nc1, nc2, nc3 = st.columns(3)
    with nc1: nr = st.text_input("Role (e.g. Beta, Beti)", key="nr")
    with nc2: nn = st.text_input("Naam", key="nn")
    with nc3: np_ = st.text_input("Phone Number", key="np")
    if st.button("✅ Contact Save Karein", key="sc"):
        if nr and nn and np_:
            db_write("INSERT OR REPLACE INTO contacts VALUES (?,?,?)", (nr, nn, np_))
            st.success(f"✅ {nn} ka number save ho gaya!"); st.rerun()
        else:
            st.warning("Teeno fields bharna zaroori hai.")

    # ── Symptom Summary for Real Doctor ───────────────────────────────────
    st.markdown("---")
    st.markdown("### 📋 Real Doctor ke liye Summary Banayein")
    st.markdown(
        "Apna dard ya bimari batayein — Sathi ek proper summary banayega "
        "jo aap doctor ko dikha ya WhatsApp kar sakein."
    )
    sym = st.text_area(
        "Aapki takleef:",
        placeholder="Jaise: Teen din se bukhar, sar dard, bhookh nahi...",
        height=120, key="sym",
    )
    if st.button("📄 Summary Banao", key="sum_btn", type="primary"):
        if sym.strip():
            with st.spinner("Summary ban rahi hai..."):
                try:
                    sp = (
                        f"{LANG_PROMPT[lang]}\n"
                        "Create a clear professional medical summary for a real doctor. "
                        "Include: Chief Complaint, Duration, Associated Symptoms, "
                        "Medicines taken. Format neatly with bullet points.\n"
                        f"Patient description: {sym}"
                    )
                    sumtxt = call_gemini(sp)
                    st.markdown(
                        f'<div class="doc-resp"><b>📋 Doctor ke liye Summary:</b>'
                        f'<br><br>{sumtxt}</div>',
                        unsafe_allow_html=True,
                    )
                    st.info("👆 Yeh summary apne doctor ko WhatsApp ya print karke dikha sakte hain.")
                except Exception as e:
                    st.error(f"Summary nahi bani: {e}")
        else:
            st.warning("Pehle apni takleef likhein!")
