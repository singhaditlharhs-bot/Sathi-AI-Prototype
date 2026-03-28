import streamlit as st
import os
import tempfile
from streamlit_mic_recorder import mic_recorder
import google.generativeai as genai

# --- INITIALIZE API ---
# Fixed the model name to the most stable 'gemini-1.5-flash-latest'
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-1.5-flash-latest')

# --- PAGE CONFIGURATION ---
st.set_page_config(page_title="Sathi-AI", page_icon="📻", layout="centered")

# --- RETRO SKEUOMORPHIC CSS ---
st.markdown("""
    <style>
    /* Warm Wood Background for a 'Household Furniture' feel */
    .stApp {
        background-color: #5c3a21;
        background-image: repeating-linear-gradient(45deg, transparent, transparent 10px, rgba(0,0,0,0.05) 10px, rgba(0,0,0,0.05) 20px);
    }
    
    /* Ivory/Aged Paper Console (High Contrast for Eyesight) */
    .block-container {
        background-color: #f4ecd8;
        border-radius: 20px;
        padding: 40px;
        box-shadow: 10px 10px 30px rgba(0,0,0,0.5), inset 0px 0px 15px rgba(139, 69, 19, 0.2);
        border: 4px solid #8b4513;
        margin-top: 2rem;
    }

    /* THE ULTIMATE 3D TACTILE BUTTON */
    .stButton>button {
        width: 100%;
        height: 160px; 
        border-radius: 30px;
        font-size: 30px !important;
        font-weight: 900;
        background: linear-gradient(to bottom, #e63946, #b30000) !important;
        color: white !important;
        /* Thick bottom border creates the 'depth' look */
        border-top: 2px solid #ff6b6b !important;
        border-left: 2px solid #ff6b6b !important;
        border-right: 4px solid #5a0e0e !important;
        border-bottom: 12px solid #5a0e0e !important; 
        box-shadow: 0px 15px 25px rgba(0,0,0,0.5) !important;
        transition: all 0.1s ease;
        text-shadow: 2px 2px 4px rgba(0,0,0,0.5);
    }
    
    /* The 'Depress' Animation - it physically sinks into the screen */
    .stButton>button:active {
        transform: translateY(10px) !important;
        border-bottom: 2px solid #5a0e0e !important;
        box-shadow: 0px 5px 10px rgba(0,0,0,0.5) !important;
    }

    /* Pulsing Status Indicator */
    @keyframes pulse {
        0% { opacity: 0.6; }
        50% { opacity: 1; }
        100% { opacity: 0.6; }
    }
    .pulsing-text {
        animation: pulse 1.5s infinite;
        color: #b30000;
        font-size: 24px;
        font-weight: bold;
        text-align: center;
        margin-top: 20px;
        padding: 15px;
        background-color: #fff9c4;
        border: 2px dashed #8b4513;
        border-radius: 10px;
    }

    .main-text {
        font-size: 38px;
        font-weight: 800;
        text-align: center;
        color: #3e2723;
        font-family: 'Courier New', Courier, monospace;
        border-bottom: 3px double #8b4513;
        padding-bottom: 10px;
        margin-bottom: 25px;
    }
    
    .instruction-text {
        font-size: 26px;
        color: #5d4037;
        text-align: center;
        font-weight: bold;
        margin-bottom: 10px;
    }
    </style>
    """, unsafe_allow_html=True)

# --- APP HEADER ---
st.markdown('<p class="main-text">📻 SATHI - Digital Sahayak</p>', unsafe_allow_html=True)

# --- INSTRUCTIONS ---
st.markdown('<p class="instruction-text">Lal button dabayein aur baat karein</p>', unsafe_allow_html=True)
st.write("") 

# --- THE MICROPHONE BUTTON ---
audio = mic_recorder(
    start_prompt="🎤 TAP TO TALK (BOLIYE)",
    stop_prompt="🛑 TAP TO STOP (BAS)",
    key='recorder'
)

# --- SATHI'S BRAIN (GEMINI INTEGRATION) ---
if audio:
    st.audio(audio['bytes'])
    st.markdown('<p class="pulsing-text">📻 Sathi sun raha hai... Ek minute rukye.</p>', unsafe_allow_html=True)
    
    try:
        # Save audio to temp file
        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as temp_audio:
            temp_audio.write(audio['bytes'])
            temp_audio_path = temp_audio.name
            
        # Upload to Gemini
        voice_file = genai.upload_file(path=temp_audio_path)
        
        # SYSTEM PROMPT: Grounding Sathi in your Project Guidelines
        prompt = """
        You are Sathi, a respectful Digital Sahayak for Indian seniors (60-80 years old).
        1. PERSPECTIVE: Speak like a caring grandson/granddaughter. Use 'Ji' and 'Mata ji/Dada ji'.
        2. LANGUAGE: Use simple Hinglish (Hindi + English). 
        3. SAFETY: If they mention chest pain, dizziness, or falling, tell them IMMEDIATELY to call their children or an ambulance.
        4. MEDICINE: Do NOT give dosages. If they ask about taking Isabgol with medicine, tell them to keep a 1-hour gap.
        
        Keep your reply under 40 words.
        """
        
        response = model.generate_content([prompt, voice_file])
        
        # Display response in a large, readable font
        st.markdown(f"""
            <div style="background-color: white; padding: 20px; border-radius: 10px; border-left: 10px solid #4CAF50; margin-top: 20px;">
                <p style="font-size: 24px; color: #1b5e20; font-weight: bold;">{response.text}</p>
            </div>
        """, unsafe_allow_html=True)
        
        os.remove(temp_audio_path)
        
    except Exception as e:
        st.error(f"Sathi ko connect karne mein dikkat ho rahi hai. Kripya dobara koshish karein.")
