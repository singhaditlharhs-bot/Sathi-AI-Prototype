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
import time
import base64
import io
 
from PIL import Image
from openai import OpenAI
from groq import Groq  # xAI uses OpenAI-compatible SDK
from elevenlabs.client import ElevenLabs
 
# ─────────────────────────────────────────────────────────────────────────────
# 1. PAGE CONFIG
# ─────────────────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Sathi-AI",
    layout="wide",
    page_icon="🏥",
    initial_sidebar_state="collapsed",
)
 
# ─────────────────────────────────────────────────────────────────────────────
# 2. 🧠 HIDDEN KNOWLEDGE BASE  (elders never see this)
#
#   HOW TO FILL THIS FROM NOTEBOOKLM:
#   1. Open your notebook → Chat panel
#   2. Type: "Give me a complete plain-text summary of all 4 sources
#             covering key medicines, diseases, dosages, geriatric care rules"
#   3. Copy the full response
#   4. Paste it between the triple-quotes below (replace the placeholder text)
#   5. Save the file — Sathi will silently use this in every answer
# ─────────────────────────────────────────────────────────────────────────────
SATHI_KNOWLEDGE = """
The Indian Pharmacopoeia is the official book of standards for drugs in India under the Drugs and Cosmetics Act of 1940. It prescribes standards for the identity, purity, and strength of drugs manufactured or marketed in the country. The process for developing a monograph in the Indian Pharmacopoeia involves six steps: preparing an initial list, acquisition of specifications, drafting, public review for 45 days, review of comments by experts, and final release. Good Laboratory Practices are statutory norms for drug testing laboratories to ensure smooth functioning and adequate space for activities. Analytical method validation must be performed to establish that performance characteristics like accuracy, precision, specificity, and linearity meet the requirements for intended applications. Indian Pharmacopoeia Reference Substances are highly-characterized physical specimens used as primary standards to ensure drug identity and purity. Proper disposal of pharmaceutical waste is essential to prevent contamination of water supplies and hazardous reactions; methods include high-temperature incineration for bulk waste and chemical inactivation for smaller quantities.
Responsible use of medicines means patients receive the right medicine at the right time in appropriate doses. Medicines are legal drugs intended for diagnosis, treatment, prevention, or mitigation of disease. Prescription medicines must be sold only under the supervision of a registered pharmacist and against a valid prescription from a qualified doctor. Non-prescription or over-the-counter medicines are relatively safe for self-medication but can still cause side effects. A valid prescription should include the doctor's name, qualifications, registration number, and address, along with patient details like age, weight, and sex, plus the medicine's generic name, strength, dosage form, and total quantity. Pharmacists are professionally qualified experts who act as a link between doctors and patients, guiding correct usage and storage. Medicine labels include critical information like the generic name, brand name, expiry date, batch number, and Schedule H warnings indicating a prescription is required. 
The expiration date is the last date a manufacturer guarantees a medicine's safety and potency when stored correctly. Common storage instructions include keeping medicines in a cool and dry place away from direct sunlight; some items like certain eye drops or insulin may require refrigeration between 2 and 8 degrees Celsius. Self-medication should only be done for minor illnesses with over-the-counter drugs and for no more than two or three days. Common prescription abbreviations include OD for once a day, BD for twice a day, TDS for three times a day, and QID for four times a day. One teaspoonful is equal to 5 millilitres, and household spoons should not be used for critical medicines like antibiotics in children.
Rational use of medicines involves providing the right medicine in the correct dose for the sufficient duration at the lowest cost. Essential medicines satisfy the priority health care needs of the population and should be available at all times in appropriate dosage forms. Standard treatment guidelines assist prescribers in making optimal treatment decisions for common health problems. An adverse drug reaction is an unintended and noxious response to a drug occurring at normal doses.
Geriatric care requires extra attention as the elderly often take more medicines and have metabolic mechanisms that have slowed down with age. Frequently prescribed drugs for Indian seniors include Metformin for diabetes, Telmisartan and Amlodipine for hypertension, Atorvastatin for cholesterol, and Pantoprazole for gastric protection. Polypharmacy increases the risk of red-flag interactions. Aspirin taken with anticoagulants like Warfarin or other antiplatelets like Clopidogrel increases the risk of major gastrointestinal or intracranial bleeding. Metoprolol taken with Timolol eye drops can cause bradycardia and low blood pressure. Levofloxacin combined with Ondansetron may lead to dangerous heart rhythms. Food interactions are also critical; vitamin K-rich leafy greens can reduce the effect of Warfarin if intake is inconsistent. High-fiber foods like Isabgol or coffee can reduce the absorption of thyroid medication like Levothyroxine and should be separated by at least 30 to 60 minutes. Metformin is best taken with regular meals but unplanned large fiber supplements should be avoided. Digital health companions for seniors should use a warm persona, kinship terms like Dada ji, large high-contrast buttons, and slow, clear speech. Such AI systems must never diagnose or prescribe and must refer emergencies like chest pain or sudden weakness to immediate medical care.
Children are not miniature adults; their doses must be calculated based on body weight. Aspirin is generally avoided in children under 12 years due to the risk of Reye's syndrome. Paracetamol at a dose of 10 to 15 milligrams per kilogram is a safer alternative for fever. For dehydration in diarrhea, oral rehydration salts are the first line of treatment. Pregnant women must be extra careful as many drugs cross the placenta; Thalidomide is a famous example that caused severe birth defects. Breastfeeding mothers should inform their doctors as drugs like Aspirin, certain antihistamines, and Diazepam can pass into breast milk and harm the baby.
For emergency conditions, immediate actions are vital. Anaphylaxis requires immediate intramuscular adrenaline at a 1:1000 concentration; the dose is 0.01 millilitres per kilogram up to 0.5 millilitres in adults. Myocardial infarction management includes chewable aspirin 325 milligrams, sublingual nitrates, and potentially thrombolytic therapy like Streptokinase. Organophosphorus poisoning is treated with atropine starting at 2 milligrams IV every 5 to 10 minutes until secretions dry, followed by pralidoxime. Snake bites require the RIGHT approach: reassure, immobilize, get to hospital, and tell the doctor; polyvalent anti-snake venom is the main treatment when signs of envenomation are present. Dog bites require immediate wound scrubbing with soap and water and post-exposure prophylaxis with rabies vaccine on days 0, 3, 7, 14, and 28.
Common infectious diseases have specific protocols. Malaria caused by P. vivax is treated with Chloroquine 25 milligrams per kilogram over three days plus Primaquine for 14 days. P. falciparum requires Artemisinin-based combination therapy. Typhoid fever is managed with antibiotics like Ceftriaxone 2 grams daily or Azithromycin 1 gram daily. Tuberculosis treatment under the RNTCP uses categories; new cases receive a 6-month regimen of Isoniazid, Rifampicin, Pyrazinamide, and Ethambutol. HIV management uses antiretroviral therapy regimens like Zidovudine, Lamivudine, and Nevirapine. In chronic conditions, hypertension is managed with lifestyle changes and drugs like Enalapril 2.5 milligrams or Amlodipine 5 milligrams. Diabetes mellitus is managed with medical nutrition therapy and medications like Metformin or Insulin. For eye conditions, bacterial conjunctivitis is treated with moxifloxacin 0.5% drops. Skin conditions like Scabies require Permethrin 5% cream or Ivermectin. Dental abscesses are treated with antibiotics like Amoxicillin and analgesics like Ibuprofen. All medical treatments must be tailored to the individual patient by a qualified professional.
Instruction: You are Sathi, the warm and patient digital grandson/companion for an Indian elder. * Voice Tone: Melodious, respectful, and unhurried. Use kinship terms like "Dada ji" or "Aunty ji" or "Sir". * Constraints: You NEVER diagnose or change doses. You only explain and remind. * Fallback: If a user mentions "chest pain," "sudden weakness," or "heavy bleeding," immediately stop the conversation and urge them to call an ambulance or family.
"""
 
# ─────────────────────────────────────────────────────────────────────────────
# 3. DATABASE
# ─────────────────────────────────────────────────────────────────────────────
_DB_LOCK = threading.Lock()
 
 
@st.cache_resource
def get_db():
    conn = sqlite3.connect("sathi_memory.db", check_same_thread=False)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS health_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT, user_msg TEXT, ai_reply TEXT, summary TEXT, tags TEXT
        );
        CREATE TABLE IF NOT EXISTS contacts (
            role TEXT PRIMARY KEY, name TEXT, phone TEXT
        );
        CREATE TABLE IF NOT EXISTS reminders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            set_date TEXT, alarm_time TEXT, medicine TEXT, done INTEGER DEFAULT 0
        );
        CREATE TABLE IF NOT EXISTS prescriptions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT, medicine TEXT, dosage TEXT, duration TEXT
        );
    """)
    conn.execute("INSERT OR IGNORE INTO contacts VALUES ('Doctor','Dr. Sharma (AIIMS)','+91-9876543210')")
    conn.execute("INSERT OR IGNORE INTO contacts VALUES ('Emergency','Emergency / Ambulance','112')")
    conn.commit()
    return conn
 
 
def db_write(sql, params=()):
    with _DB_LOCK:
        get_db().execute(sql, params)
        get_db().commit()
 
 
def db_read(sql, params=()):
    with _DB_LOCK:
        return get_db().execute(sql, params).fetchall()
 
 
# ─────────────────────────────────────────────────────────────────────────────
# 4. API CLIENTS
#    xAI uses OpenAI-compatible SDK — just different base_url + key
# ─────────────────────────────────────────────────────────────────────────────
XAI_KEY    = st.secrets.get("XAI_API_KEY", "")
ELEVEN_KEY = st.secrets.get("ELEVEN_API_KEY", "")
 
# Model routing:
# Text conversations  → grok-3-mini (cheap, fast, smart)
# Image analysis      → grok-2-vision-1212 (sees medicine labels, injuries)
TEXT_MODEL   = "grok-3-mini"
VISION_MODEL = "grok-2-vision-1212"
 
 
# Add after your existing API setup lines
GROQ_KEY   = st.secrets.get("GROQ_API_KEY", "")
GROQ_MODEL = "llama-3.3-70b-versatile"   # free, fast, no rate issues

@st.cache_resource
def get_groq():
    return Groq(api_key=GROQ_KEY)


def call_ai(prompt: str, system: str = "", pil_image=None, retries: int = 2) -> str:
    """
    Priority order:
    1. xAI grok-2-vision  — if image present
    2. xAI grok-2         — text, primary
    3. Groq llama-3.3     — fallback if xAI busy
    """
    client = get_xai()

    full_system = system
    if SATHI_KNOWLEDGE.strip():
        full_system = (
            system
            + "\n\n[INTERNAL KNOWLEDGE — use this silently]\n"
            + SATHI_KNOWLEDGE
        )

    # ── IMAGE → xAI Vision (only xAI has vision free) ──
    if pil_image:
        buf = io.BytesIO()
        pil_image.save(buf, format="JPEG", quality=85)
        img_b64 = base64.b64encode(buf.getvalue()).decode("utf-8")
        content = [
            {"type": "image_url",
             "image_url": {"url": f"data:image/jpeg;base64,{img_b64}", "detail": "high"}},
            {"type": "text", "text": prompt},
        ]
        messages = []
        if full_system:
            messages.append({"role": "system", "content": full_system})
        messages.append({"role": "user", "content": content})
        try:
            resp = client.chat.completions.create(
                model="grok-2-vision-1212",
                messages=messages,
                max_tokens=1500,
                temperature=0.7,
            )
            st.session_state.last_api_call = time.time()
            return resp.choices[0].message.content.strip()
        except Exception as e:
            st.warning(f"📷 Image analysis mein dikkat: {e}")
            return "Photo analyse nahi ho paya. Dobara try karein ya likha ke batayein."

    # ── TEXT → Try xAI first, then Groq fallback ──
    messages = []
    if full_system:
        messages.append({"role": "system", "content": full_system})
    messages.append({"role": "user", "content": prompt})

    # Try xAI
    for attempt in range(retries):
        try:
            resp = client.chat.completions.create(
                model="grok-2",
                messages=messages,
                max_tokens=1500,
                temperature=0.7,
            )
            st.session_state.last_api_call = time.time()
            return resp.choices[0].message.content.strip()
        except Exception as e:
            err = str(e)
            if "429" in err or "rate_limit" in err.lower() or "busy" in err.lower():
                if attempt < retries - 1:
                    time.sleep(5)
                    continue
                # xAI busy — silently switch to Groq
                break
            else:
                break   # non-rate error, go to Groq anyway

    # Groq fallback — runs silently, user never knows
    if GROQ_KEY:
        try:
            groq_client = get_groq()
            resp = groq_client.chat.completions.create(
                model=GROQ_MODEL,
                messages=messages,
                max_tokens=1500,
                temperature=0.7,
            )
            st.session_state.last_api_call = time.time()
            return resp.choices[0].message.content.strip()
        except Exception as e2:
            pass   # both failed

    # Both APIs failed — return cached answer if available
    return get_cached_answer(prompt)


def get_cached_answer(prompt: str) -> str:
    """Last resort — common health questions answered from built-in cache."""
    prompt_lower = prompt.lower()
    cache = {
        ("sar", "sir", "headache", "dard"): (
            "Sar dard ke liye: thoda paani pijiye, andheri jagah mein lete jayein, "
            "Paracetamol 500mg le sakte hain. Agar 2 din se zyada ho ya bahut tej ho "
            "toh doctor se zaroor milein. 🙏"
        ),
        ("bukhar", "fever", "temperature", "garmi"): (
            "Bukhar mein: paani aur nimbu paani pijiye, "
            "Paracetamol 500mg baar baar le sakte hain. "
            "103°F se zyada ho toh doctor ko turant dikhayein. 🙏"
        ),
        ("bp", "blood pressure", "tension", "hypertension"): (
            "BP ke liye: namak kam khayen, tension na lein, "
            "dawai waqt par lein. Agar chakkar aa rahe hain ya sar bahut dard kar raha hai "
            "toh seedha doctor ke paas jayein. 🙏"
        ),
        ("sugar", "diabetes", "madhumeh"): (
            "Sugar ke liye: meetha band karein, waqt par khaana khayen, "
            "dawai kabhi mat bhoolein. Regular check karwate rahein. 🙏"
        ),
        ("pet", "stomach", "pait", "acidity", "gas"): (
            "Pet dard ya acidity ke liye: halka khaana khayen, "
            "masaledar cheezein kam karein. Antacid le sakte hain. "
            "Agar 2 din se zyada ho toh doctor se milein. 🙏"
        ),
        ("neend", "sleep", "insomnia", "so nahi"): (
            "Neend na aane par: raat ko chai/coffee mat pijiye, "
            "sone se pehle halka garam doodh pijiye, "
            "phone band kar ke lete jayein. 🙏"
        ),
        ("ghabrahat", "anxiety", "chinta", "tension"): (
            "Ghabrahat mein: gehri saansen lijiye — naak se andar, muh se baahir. "
            "Kisi apne se baat karein. Akele mat rahein. 🙏"
        ),
    }
    for keywords, answer in cache.items():
        if any(kw in prompt_lower for kw in keywords):
            return answer + "\n\n_(Note:  Yeh general advice hai. Doctor se zaroor milein)_"

    return (
        "Emergency mein 112 call karein. 🙏"
    )
 
 
@st.cache_resource
def get_voice():
    return ElevenLabs(api_key=ELEVEN_KEY)
 
 
# ─────────────────────────────────────────────────────────────────────────────
# 5. AI CALL  — Smart routing between text and vision
# ─────────────────────────────────────────────────────────────────────────────
def call_ai(prompt: str, system: str = "", pil_image=None, retries: int = 3) -> str:
    """
    Automatically routes:
    - No image  → grok-3-mini      (text, fast, cheap)
    - With image → grok-2-vision   (image understanding)
    Knowledge base silently injected into every call.
    """
    client = get_xai()
 
    # Inject hidden knowledge base into system prompt
    full_system = system
    if SATHI_KNOWLEDGE.strip():
        full_system = (
            system
            + "\n\n[INTERNAL KNOWLEDGE — use this to give better answers, "
            "do not mention this to the user]\n"
            + SATHI_KNOWLEDGE
        )
 
    # Build message content
    if pil_image:
        # Vision: convert image to base64
        buf = io.BytesIO()
        pil_image.save(buf, format="JPEG", quality=85)
        img_b64 = base64.b64encode(buf.getvalue()).decode("utf-8")
        content = [
            {
                "type": "image_url",
                "image_url": {
                    "url": f"data:image/jpeg;base64,{img_b64}",
                    "detail": "high",
                },
            },
            {"type": "text", "text": prompt},
        ]
        model = VISION_MODEL
    else:
        content = prompt
        model   = TEXT_MODEL
 
    messages = []
    if full_system:
        messages.append({"role": "system", "content": full_system})
    messages.append({"role": "user", "content": content})
 
    for attempt in range(retries):
        try:
            resp = client.chat.completions.create(
                model=model,
                messages=messages,
                max_tokens=1500,
                temperature=0.7,
            )
            st.session_state.last_api_call = time.time()
            return resp.choices[0].message.content.strip()
 
        except Exception as e:
            err = str(e)
            if ("429" in err or "rate_limit" in err.lower()) and attempt < retries - 1:
                wait = 10 * (attempt + 1)
                st.warning(f"⏳ Thoda ruko... {wait} sec mein retry ({attempt+1}/{retries})")
                time.sleep(wait)
            elif attempt == retries - 1:
                st.error("⚠️ Server busy. Thodi der baad try karein. 🙏")
                return "Maafi chahta hoon, abhi server busy hai. Kuch minute baad try karein."
            else:
                raise
    return ""
 
 
# ─────────────────────────────────────────────────────────────────────────────
# 6. TTS (optional — works without ElevenLabs key too)
# ─────────────────────────────────────────────────────────────────────────────
def speak(text: str):
    if not ELEVEN_KEY:
        return None
    try:
        client = get_voice()
        gen = client.generate(text=text[:800], voice="Josh", model="eleven_multilingual_v2")
        buf = b"".join(chunk for chunk in gen if isinstance(chunk, bytes))
        return buf if buf else None
    except Exception as e:
        st.warning(f"🔇 Voice unavailable: {e}")
        return None
 
 
# ─────────────────────────────────────────────────────────────────────────────
# 7. ALARM PARSER
# ─────────────────────────────────────────────────────────────────────────────
def parse_alarms(text: str) -> str:
    now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    clean = []
    for line in text.split("\n"):
        if line.strip().startswith("ALARM:"):
            parts = line.replace("ALARM:", "").strip().split("|")
            alarm_time = parts[0].strip() if parts          else "As directed"
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
# 8. LANGUAGE SYSTEM
# ─────────────────────────────────────────────────────────────────────────────
LANG_PROMPT = {
    "hinglish": (
        "Aap warmly Hinglish mein bolein — Hindi aur English ka natural mix. "
        "'Aap' use karein. Ek caring bete ya respectful doctor ki tarah bolein. "
        "Sentences chote aur simple rakhein buzurgon ke liye."
    ),
    "hindi": (
        "Sirf shuddh Hindi mein uttar dein. 'Aap' ka prayog karein. "
        "Buzurgon ke liye saral aur spasht bhaasha mein likhein."
    ),
    "english": (
        "Speak only in clear simple English. Use 'you' respectfully. "
        "Keep sentences short and easy for elderly users."
    ),
}
 
LANG_LABEL = {"hinglish": "🇮🇳 Hinglish", "hindi": "🕉️ Hindi", "english": "🇬🇧 English"}
 
UI = {
    "hinglish": {
        "t1":"🤖 Sathi Bot","t2":"👨‍⚕️ Doctor","t3":"⏰ Alarms","t4":"🆘 SOS",
        "greet":"Namaste! Aap kya poochna chahte hain?",
        "hint":"Yahan likhein ya mic dabayein...",
        "ask":"🙏 Poochhein","send":"✅ Bhejein","replay":"🔁 Phir Sunein",
        "alarm_saved":"✅ Alarm set ho gaya!",
        "clinic":"🏥 Live Clinic — Dr. Sathi",
        "ready":"🔵 Dr. Sathi ready hain",
        "talking":"🟢 Doctor jawab de rahe hain...",
    },
    "hindi": {
        "t1":"🤖 साथी Bot","t2":"👨‍⚕️ Doctor","t3":"⏰ अलार्म","t4":"🆘 SOS",
        "greet":"नमस्ते! आप क्या पूछना चाहते हैं?",
        "hint":"यहाँ लिखें या माइक दबाएं...",
        "ask":"🙏 पूछें","send":"✅ भेजें","replay":"🔁 फिर सुनें",
        "alarm_saved":"✅ अलार्म सेट हो गया!",
        "clinic":"🏥 Live Clinic — Dr. साथी",
        "ready":"🔵 Dr. साथी तैयार हैं",
        "talking":"🟢 Doctor उत्तर दे रहे हैं...",
    },
    "english": {
        "t1":"🤖 Sathi Bot","t2":"👨‍⚕️ Doctor","t3":"⏰ Alarms","t4":"🆘 SOS",
        "greet":"Hello! How can I help you today?",
        "hint":"Type here or press the mic...",
        "ask":"🙏 Ask Sathi","send":"✅ Send","replay":"🔁 Replay",
        "alarm_saved":"✅ Alarm has been set!",
        "clinic":"🏥 Live Clinic — Dr. Sathi",
        "ready":"🔵 Dr. Sathi is ready",
        "talking":"🟢 Doctor is responding...",
    },
}
 
 
# ─────────────────────────────────────────────────────────────────────────────
# 9. AVATAR
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
                unsafe_allow_html=True)
            return
        except FileNotFoundError:
            pass
    try:
        with open("doctor_static.png", "rb") as f:
            b64 = base64.b64encode(f.read()).decode()
        st.markdown(
            f'<div style="text-align:center;"><img src="data:image/png;base64,{b64}" style="{AV_CSS}"></div>',
            unsafe_allow_html=True)
    except FileNotFoundError:
        st.markdown('<div style="text-align:center;font-size:110px;">👨‍⚕️</div>', unsafe_allow_html=True)
 
 
# ─────────────────────────────────────────────────────────────────────────────
# 10. CSS
# ─────────────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Baloo+2:wght@400;600;800&display=swap');
:root{--g-dark:#1B5E20;--g-mid:#2E7D32;--g-lt:#4CAF50;--g-pale:#E8F5E9;
      --amber:#FF8F00;--amber-lt:#FFF8E1;--red:#C62828;--red-lt:#FFEBEE;
      --cream:#FFFDE7;--shadow:0 4px 24px rgba(0,0,0,0.12);--r:18px;}
html,body,.stApp{background:linear-gradient(150deg,#f0f7f0 0%,#fffde7 60%,#e8f5e9 100%)!important;
  font-family:'Baloo 2',sans-serif!important;color:#1A1A1A!important;}
.sathi-hdr{background:linear-gradient(135deg,var(--g-dark),var(--g-mid));color:white;
  padding:16px 24px;border-radius:var(--r);margin-bottom:18px;box-shadow:var(--shadow);
  display:flex;align-items:center;gap:14px;flex-wrap:wrap;}
.sathi-hdr h1{font-size:2rem;margin:0;font-weight:800;}
.sathi-hdr p{font-size:1rem;margin:0;opacity:.88;}
.badge{background:var(--amber);color:#fff;font-size:.7rem;font-weight:700;
  padding:2px 9px;border-radius:20px;margin-left:8px;}
.grok-badge{background:linear-gradient(135deg,#1a1a2e,#16213e);color:#00d4ff;
  padding:4px 12px;border-radius:20px;font-size:.8rem;font-weight:700;
  display:inline-block;margin-left:8px;border:1px solid #00d4ff;}
.stTabs [data-baseweb="tab-list"]{gap:6px;background:white;padding:6px;
  border-radius:var(--r);box-shadow:var(--shadow);flex-wrap:wrap;}
.stTabs [data-baseweb="tab"]{font-size:1.05rem!important;font-weight:700!important;
  padding:10px 16px!important;border-radius:12px!important;color:#424242!important;transition:all .2s!important;}
.stTabs [aria-selected="true"]{background:var(--g-mid)!important;color:white!important;
  box-shadow:0 2px 12px rgba(46,125,50,.3)!important;}
.card{background:white;border-radius:var(--r);padding:18px;box-shadow:var(--shadow);
  margin-bottom:14px;border-left:6px solid var(--g-mid);}
.doc-resp{background:linear-gradient(135deg,#f1f8e9,#fff);border:2px solid var(--g-lt);
  border-radius:var(--r);padding:20px;margin:14px 0;font-size:1.12rem;line-height:1.8;
  box-shadow:0 2px 16px rgba(76,175,80,.15);}
.sum-box{background:var(--amber-lt);border:2px solid var(--amber);border-radius:12px;
  padding:14px 18px;margin-top:10px;font-size:1.05rem;font-weight:600;}
.presc-box{background:var(--g-pale);border:2px solid var(--g-lt);border-radius:12px;padding:12px 16px;margin:6px 0;}
.urgent{background:var(--red-lt);border:2px solid var(--red);border-radius:12px;
  padding:12px 16px;margin-top:8px;font-weight:700;color:var(--red);}
.kb-display{background:#0d2518;border:2px solid var(--g-mid);border-radius:12px;
  padding:14px 18px;min-height:58px;color:#69F0AE;font-size:1.3rem;
  font-family:'Courier New',monospace;font-weight:700;margin-bottom:10px;
  letter-spacing:1px;word-break:break-all;box-shadow:inset 0 2px 8px rgba(0,0,0,.5);}
.kb-wrap{background:#1a2332;border-radius:20px;padding:16px 12px 12px;
  border:3px solid #0d1520;box-shadow:0 12px 40px rgba(0,0,0,.5);margin-top:12px;}
.clinic-title{text-align:center;font-size:1.5rem;font-weight:800;color:var(--g-dark);margin-bottom:10px;}
[data-testid="column"]{padding:0 2px!important;}
.stButton>button{background:linear-gradient(180deg,#f0f0f0,#d8d8d8)!important;color:#111!important;
  font-weight:800!important;border-radius:7px!important;height:50px!important;font-size:1.05rem!important;
  border-top:1px solid #fff!important;border-left:1px solid #ccc!important;border-right:1px solid #aaa!important;
  border-bottom:5px solid #888!important;transition:all .08s!important;width:100%!important;
  margin-bottom:4px!important;box-shadow:0 2px 4px rgba(0,0,0,.22)!important;}
.stButton>button:hover{background:linear-gradient(180deg,#fff,#e8e8e8)!important;transform:translateY(-1px)!important;}
.stButton>button:active{transform:translateY(4px)!important;border-bottom:1px solid #888!important;box-shadow:none!important;}
button[kind="primary"]{background:linear-gradient(180deg,#4CAF50,#2E7D32)!important;
  color:white!important;border-bottom:5px solid #1B5E20!important;}
.sp .stButton>button{background:linear-gradient(180deg,#42A5F5,#1565C0)!important;
  color:white!important;border-bottom:5px solid #0d3a77!important;}
.dl .stButton>button{background:linear-gradient(180deg,#FF7043,#BF360C)!important;
  color:white!important;border-bottom:5px solid #7f2600!important;}
.cp .stButton>button{background:linear-gradient(180deg,#AB47BC,#6A1B9A)!important;
  color:white!important;border-bottom:5px solid #4a0072!important;}
.rp .stButton>button{background:linear-gradient(180deg,#26C6DA,#00838F)!important;
  color:white!important;border-bottom:5px solid #005662!important;}
.cl .stButton>button{background:linear-gradient(180deg,#90A4AE,#546E7A)!important;
  color:white!important;border-bottom:5px solid #263238!important;}
.sos .stButton>button{background:linear-gradient(135deg,#C62828,#E53935)!important;
  color:white!important;font-size:1.35rem!important;font-weight:900!important;
  height:68px!important;border-radius:16px!important;border-bottom:5px solid #7f0000!important;
  box-shadow:0 6px 24px rgba(198,40,40,.4)!important;animation:pred 2s infinite;}
@keyframes pred{0%,100%{box-shadow:0 6px 24px rgba(198,40,40,.4);}50%{box-shadow:0 6px 36px rgba(198,40,40,.7);}}
@media(max-width:768px){.sathi-hdr h1{font-size:1.4rem;}.stButton>button{height:44px!important;font-size:.95rem!important;}}
@media(max-width:480px){.sathi-hdr{flex-direction:column;text-align:center;}.stButton>button{height:40px!important;font-size:.85rem!important;}}
button[title="View fullscreen"]{display:none!important;}
#MainMenu,footer,header{visibility:hidden!important;}
.block-container{padding-top:.8rem!important;}
</style>
""", unsafe_allow_html=True)
 
# ─────────────────────────────────────────────────────────────────────────────
# 11. SESSION STATE
# ─────────────────────────────────────────────────────────────────────────────
for k, v in {
    "typed": "", "caps": True, "talking": False,
    "lang": "hinglish", "last_audio": None,
    "last_reply": "", "last_summary": "",
    "last_api_call": 0,
}.items():
    if k not in st.session_state:
        st.session_state[k] = v
 
NOW = datetime.datetime.now()
lang = st.session_state.lang
ui   = UI[lang]
 
# ─────────────────────────────────────────────────────────────────────────────
# 12. HEADER
# ─────────────────────────────────────────────────────────────────────────────
st.markdown(f"""
<div class="sathi-hdr">
  <span style="font-size:2.8rem;">🏥</span>
  <div>
    <h1>Sathi-AI <span class="badge">v5</span>
        <span class="grok-badge">⚡ Grok</span></h1>
    <p>Aapka Swasthya Saathi — Your Caring Health Companion</p>
  </div>
  <div style="margin-left:auto;text-align:right;font-size:.95rem;opacity:.85;">
    📅 {NOW.strftime('%d %b %Y')}<br>🕐 {NOW.strftime('%I:%M %p')}
  </div>
</div>
""", unsafe_allow_html=True)
 
# Language bar
lc = st.columns([1,1,1,5])
with lc[0]:
    if st.button("🇮🇳 Hinglish", key="l1"): st.session_state.lang="hinglish"; st.rerun()
with lc[1]:
    if st.button("🕉️ Hindi",    key="l2"): st.session_state.lang="hindi";    st.rerun()
with lc[2]:
    if st.button("🇬🇧 English", key="l3"): st.session_state.lang="english";  st.rerun()
with lc[3]:
    st.markdown(f"<span style='color:#2E7D32;font-weight:700;'>Active: {LANG_LABEL[lang]}</span>",
                unsafe_allow_html=True)
 
# ─────────────────────────────────────────────────────────────────────────────
# 13. TABS
# ─────────────────────────────────────────────────────────────────────────────
tab1, tab2, tab3, tab4 = st.tabs([ui["t1"], ui["t2"], ui["t3"], ui["t4"]])
 
# ══════════════════════════════════════════════════════════════════════════════
# TAB 1 — SATHI BOT
# ══════════════════════════════════════════════════════════════════════════════
with tab1:
    st.markdown(f'<div class="card"><b style="font-size:1.3rem;">💬 {ui["greet"]}</b>'
                '<br>Koi bhi sawaal poochhein — sehat, dawai, ya zindagi ke baare mein.</div>',
                unsafe_allow_html=True)
 
    bot_q = st.text_area("Aapka Sawaal:", height=100, placeholder=ui["hint"], key="bot_q")
 
    b1, b2 = st.columns([3,1])
    with b1:
        ask = st.button(ui["ask"], key="bot_ask", type="primary", use_container_width=True)
    with b2:
        st.markdown('<div class="rp">', unsafe_allow_html=True)
        st.button("🎙️ Mic", key="mc_bot", use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)
 
    audio_bot = st.audio_input("🎙️ Ya yahan bolein:", key="ab")
 
    if time.time() - st.session_state.last_api_call < 2:
        st.warning("Thoda ruko... 🙏"); st.stop()
 
    if ask or audio_bot:
        query = bot_q.strip()
        if query:
            with st.spinner("Sathi soch raha hai..."):
                try:
                    system = (
                        f"{LANG_PROMPT[lang]}\n"
                        "You are Sathi, a warm companion for elderly people in India. "
                        "Answer simply and kindly. Avoid complex medical jargon."
                    )
                    reply = call_ai(prompt=f"Question: {query}", system=system)
                    st.markdown(
                        f'<div class="doc-resp"><b>🤖 Sathi:</b><br>{reply}</div>',
                        unsafe_allow_html=True)
                    audio = speak(reply)
                    if audio:
                        st.session_state.last_audio = audio
                        st.audio(audio, format="audio/mp3", autoplay=True)
                    db_write(
                        "INSERT INTO health_logs (date,user_msg,ai_reply,tags) VALUES (?,?,?,?)",
                        (NOW.strftime("%Y-%m-%d %H:%M"), query, reply, "Sathi Bot"))
                except Exception as e:
                    st.error(f"⚠️ Error: {e}")
        else:
            st.warning("Kuch toh likhein! 🙏")
 
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
    av_col, inp_col = st.columns([1,1], gap="large")
 
    with av_col:
        show_avatar(st.session_state.talking)
        status_txt = ui["talking"] if st.session_state.talking else ui["ready"]
        st.markdown(
            f'<div style="text-align:center;font-weight:700;color:#2E7D32;'
            f'font-size:1rem;margin-top:8px;">{status_txt}</div>',
            unsafe_allow_html=True)
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
 
    if st.session_state.last_reply:
        st.markdown(
            f'<div class="doc-resp"><b>👨‍⚕️ Dr. Sathi:</b><br>'
            f'{st.session_state.last_reply}</div>', unsafe_allow_html=True)
        if st.session_state.last_summary:
            st.markdown(
                f'<div class="sum-box">📋 <b>Summary:</b> {st.session_state.last_summary}</div>',
                unsafe_allow_html=True)
 
    # ── 3D Keyboard ──────────────────────────────────────────────────────
    st.markdown("---")
    disp = st.session_state.typed if st.session_state.typed else ui["hint"]
    st.markdown(f'<div class="kb-wrap"><div class="kb-display">{disp}</div>', unsafe_allow_html=True)
 
    for row in [list("QWERTYUIOP"), list("ASDFGHJKL"), list("ZXCVBNM")]:
        cols = st.columns(len(row))
        for i, ch in enumerate(row):
            lbl = ch if st.session_state.caps else ch.lower()
            if cols[i].button(lbl, key=f"k_{ch}"):
                st.session_state.typed += lbl; st.rerun()
 
    r1,r2,r3,r4,r5 = st.columns([1.1,1.1,3.5,1.2,1.8])
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
        send_clicked = st.button(ui["send"], key="send_k", type="primary", use_container_width=True)
    st.markdown('</div>', unsafe_allow_html=True)
 
    # ── SEND LOGIC ───────────────────────────────────────────────────────
    if time.time() - st.session_state.last_api_call < 2:
        st.warning("Thoda ruko... 🙏"); st.stop()
 
    if send_clicked:
        user_text = st.session_state.typed.strip()
        pil_img   = None
        if cam_photo: pil_img = Image.open(cam_photo)
        elif up_img:  pil_img = Image.open(up_img)
 
        if not user_text and not pil_img:
            st.warning("Kuch likhein ya photo lo pehle! 🙏")
        else:
            st.session_state.talking = True
            system = f"""
{LANG_PROMPT[lang]}
You are Dr. Sathi — caring experienced Indian doctor speaking to elderly patient.
Time: {NOW.strftime('%I:%M %p, %d %B %Y')}.
RULES:
1. Be warm, patient, respectful. Use "Aap" in Hindi/Hinglish.
2. If image: analyse it (medicine label→purpose/dosage; injury→first aid; prescription→simple summary).
3. End with: SUMMARY: [one clear sentence]
4. For medicine/dosage: ALARM: [time] | [Medicine] | [Dosage] | [Duration]
5. If serious: URGENT: [advice]
6. Close with kind encouraging sentence.
"""
            with st.spinner("Doctor soch rahe hain..."):
                try:
                    raw   = call_ai(
                        prompt=f"Patient: {user_text or '(analyse image only)'}",
                        system=system,
                        pil_image=pil_img,
                    )
                    clean = parse_alarms(raw)
 
                    summary, urgent = "", ""
                    if "SUMMARY:" in clean:
                        p = clean.split("SUMMARY:"); clean = p[0].strip()
                        summary = p[1].strip().split("\n")[0]
                    if "URGENT:" in clean:
                        p = clean.split("URGENT:");  clean = p[0].strip()
                        urgent  = p[1].strip().split("\n")[0]
 
                    st.session_state.last_reply   = clean
                    st.session_state.last_summary = summary
 
                    db_write(
                        "INSERT INTO health_logs (date,user_msg,ai_reply,summary,tags) VALUES (?,?,?,?,?)",
                        (NOW.strftime("%Y-%m-%d %H:%M"), user_text or "(Image)", clean, summary, "Doctor Visit"))
 
                    st.markdown(f'<div class="doc-resp"><b>👨‍⚕️ Dr. Sathi:</b><br>{clean}</div>',
                                unsafe_allow_html=True)
                    if summary:
                        st.markdown(f'<div class="sum-box">📋 <b>Summary:</b> {summary}</div>',
                                    unsafe_allow_html=True)
                    if urgent:
                        st.markdown(f'<div class="urgent">🚨 <b>URGENT:</b> {urgent}</div>',
                                    unsafe_allow_html=True)
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
            m1,m2,m3 = st.columns(3)
            with m1: at = st.text_input("Samay (e.g. 8:00 AM)", key="at")
            with m2: am = st.text_input("Dawai ka naam", key="am")
            with m3:
                st.write(""); st.write("")
                if st.button("✅ Set", key="set_al"):
                    if at and am:
                        db_write("INSERT INTO reminders (set_date,alarm_time,medicine) VALUES (?,?,?)",
                                 (NOW.strftime("%Y-%m-%d %H:%M"), at, am))
                        st.success(ui["alarm_saved"]); st.rerun()
                    else: st.warning("Samay aur dawai dono bharen!")
 
        alarms = db_read("SELECT id,set_date,alarm_time,medicine,done FROM reminders ORDER BY id DESC")
        if alarms:
            for aid,adate,atime,amed,adone in alarms:
                icon = "✅" if adone else "⏰"
                bg   = "#f5f5f5" if adone else "#FFF8E1"
                bc   = "#bbb"    if adone else "#FF8F00"
                st.markdown(f"""
                <div style="background:{bg};border:2px solid {bc};border-radius:12px;
                     padding:12px 16px;margin:6px 0;">
                  <b>{icon} {atime}</b> — {amed}
                  <div style="font-size:.82rem;color:#666;">Set: {adate}</div>
                </div>""", unsafe_allow_html=True)
                c1,c2 = st.columns(2)
                with c1:
                    if not adone and st.button("✔ Done", key=f"d_{aid}"):
                        db_write("UPDATE reminders SET done=1 WHERE id=?", (aid,)); st.rerun()
                with c2:
                    if st.button("🗑 Del", key=f"da_{aid}"):
                        db_write("DELETE FROM reminders WHERE id=?", (aid,)); st.rerun()
        else:
            st.info("Koi alarm nahi hai.")
 
    with s2:
        st.markdown("### 💊 Prescriptions")
        pres = db_read("SELECT date,medicine,dosage,duration FROM prescriptions ORDER BY id DESC")
        if pres:
            for pdate,pmed,pdos,pdur in pres:
                st.markdown(f"""
                <div class="presc-box">💊 <b>{pmed}</b>
                  {f'— {pdos}' if pdos else ''} {f'({pdur})' if pdur else ''}
                  <div style="font-size:.82rem;color:#888;">📅 {pdate}</div>
                </div>""", unsafe_allow_html=True)
        else:
            st.info("Koi prescription nahi hai abhi.")
 
    with s3:
        st.markdown("### 📜 Health History")
        logs = db_read("SELECT date,user_msg,ai_reply,summary,tags FROM health_logs ORDER BY id DESC LIMIT 20")
        if logs:
            for ldate,luser,lreply,lsum,ltag in logs:
                with st.expander(f"🕐 {ldate}  |  🏷 {ltag or 'General'}"):
                    st.markdown(f"**🗣 Aapne kaha:** {luser}")
                    st.markdown(f'<div style="background:#f9f9f9;border-radius:8px;padding:10px;font-size:.95rem;">{lreply}</div>',
                                unsafe_allow_html=True)
                    if lsum: st.markdown(f"**📋 Summary:** {lsum}")
        else:
            st.info("Koi history nahi hai abhi.")
 
 
# ══════════════════════════════════════════════════════════════════════════════
# TAB 4 — SOS
# ══════════════════════════════════════════════════════════════════════════════
with tab4:
    st.markdown("### 🆘 Emergency & Doctor Contact")
    st.markdown("""
    <div class="card" style="border-left-color:#C62828;">
      <b style="color:#C62828;font-size:1.15rem;">⚠️ Zaruri Suchna</b><br>
      Agar aapko bahut takleef hai — neeche diye button se seedha call karein.
    </div>""", unsafe_allow_html=True)
 
    for role,name,phone in db_read("SELECT role,name,phone FROM contacts"):
        icon  = "🆘" if role=="Emergency" else "👨‍⚕️"
        color = "#C62828" if role=="Emergency" else "#1565C0"
        st.markdown(f"""
        <div style="background:white;border:2px solid {color};border-radius:14px;
             padding:16px 20px;margin:10px 0;display:flex;align-items:center;
             gap:14px;box-shadow:0 4px 16px rgba(0,0,0,.1);">
          <span style="font-size:2.2rem;">{icon}</span>
          <div style="flex:1;">
            <div style="font-size:1.15rem;font-weight:800;color:{color};">{name}</div>
            <div style="font-size:1.4rem;font-weight:700;letter-spacing:1px;">{phone}</div>
          </div>
          <a href="tel:{phone}" style="background:{color};color:white;padding:12px 22px;
             border-radius:10px;font-weight:800;font-size:1rem;text-decoration:none;">📞 Call</a>
        </div>""", unsafe_allow_html=True)
 
    st.markdown("---")
    st.markdown("### ➕ Naya Contact Jorhein")
    nc1,nc2,nc3 = st.columns(3)
    with nc1: nr  = st.text_input("Role",         key="nr")
    with nc2: nn  = st.text_input("Naam",         key="nn")
    with nc3: np_ = st.text_input("Phone Number", key="np")
    if st.button("✅ Contact Save Karein", key="sc"):
        if nr and nn and np_:
            db_write("INSERT OR REPLACE INTO contacts VALUES (?,?,?)", (nr,nn,np_))
            st.success(f"✅ {nn} ka number save ho gaya!"); st.rerun()
        else: st.warning("Teeno fields bharna zaroori hai.")
 
    st.markdown("---")
    st.markdown("### 📋 Real Doctor ke liye Summary Banayein")
    sym = st.text_area("Aapki takleef:",
                        placeholder="Jaise: Teen din se bukhar, sar dard...",
                        height=120, key="sym")
    if st.button("📄 Summary Banao", key="sum_btn", type="primary"):
        if sym.strip():
            with st.spinner("Summary ban rahi hai..."):
                try:
                    system = (
                        f"{LANG_PROMPT[lang]}\n"
                        "Create a clear professional medical summary for a real doctor. "
                        "Include: Chief Complaint, Duration, Associated Symptoms, Medicines taken. "
                        "Format neatly with bullet points."
                    )
                    sumtxt = call_ai(prompt=f"Patient: {sym}", system=system)
                    st.markdown(
                        f'<div class="doc-resp"><b>📋 Doctor ke liye Summary:</b><br><br>{sumtxt}</div>',
                        unsafe_allow_html=True)
                    st.info("👆 Yeh summary WhatsApp ya print karke doctor ko dikha sakte hain.")
                except Exception as e:
                    st.error(f"Summary nahi bani: {e}")
        else:
            st.warning("Pehle apni takleef likhein!")
