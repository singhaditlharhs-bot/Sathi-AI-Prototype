import streamlit as st
import os
import tempfile
from streamlit_mic_recorder import mic_recorder
import google.generativeai as genai

# --- INITIALIZE API ---
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-1.5-flash')

# --- PAGE CONFIGURATION ---
st.set_page_config(page_title="Sathi-AI", page_icon="📻", layout="centered")

# --- RETRO SKEUOMORPHIC CSS ---
st.markdown("""
    <style>
    /* Warm Wood Background */
    .stApp {
        background-color: #5c3a21;
        background-image: repeating-linear-gradient(45deg, transparent, transparent 10px, rgba(0,0,0,0.05) 10px, rgba(0,0,0,0.05) 20px);
    }
    
    /* Ivory Console Container */
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
        border: 3px solid #5a0e0e !important;
        box-shadow: 0px 15px 0px #701010, 0px 20px 25px rgba(0,0,0,0.5) !important;
        transition: all 0.1s ease;
        text-shadow: 2px 2px 4px rgba(0,0,0,0.5);
    }
    
    /* The 'Depress' Animation when active */
    .stButton>button:active, .stButton>button:focus {
        transform: translateY(15px) !important;
        box-shadow: 0px 0px 0px #701010, 0px 5px 10px rgba(0,0,0,0.5) !important;
        background: linear-gradient(to bottom, #cc0000, #990000) !important;
        color: white !important;
    }

    /* Pulsing Animation for System Status */
    @keyframes pulse {
        0% { opacity: 0.6; transform: scale(0.98); }
        50% { opacity: 1; transform: scale(1.02); }
        100% { opacity: 0.6; transform: scale(0.98); }
    }
    .pulsing-text {
        animation: pulse 1.5s infinite;
        color: #b30000;
        font-size: 24px;
        font-weight: bold;
        text-align: center;
        margin-top: 20px;
        padding: 10px;
        background-color: #fbe9e7;
        border-radius: 10px;
        border: 2px dashed #b30000;
    }

    /* Retro Typography */
    .main-text {
        font-size: 35px;
        font-weight: 800;
        text-align: center;
        color: #3e2723;
        font-family: 'Courier New', Courier, monospace;
        border-bottom: 2px solid #8b4513;
        padding-bottom: 15px;
        margin-bottom: 30px;
    }
    
    .instruction-text {
        font-size: 24px;
        color: #5d4037;
        text-align: center;
        font-weight: bold;
    }
    </style>
    """, unsafe_allow_html=True)

# --- APP HEADER ---
st.markdown('<p class="main-text">📻 SATHI - Digital Sahayak</p>', unsafe_allow_html=True)

# --- INSTRUCTIONS ---
st.markdown('<p class="instruction-text">Lal button dabayein aur baat karein<br>(Press the red button and speak)</p>', unsafe_allow_html=True)
st.write("") 

# --- THE MICROPHONE BUTTON ---
audio = mic_recorder(
    start_prompt="🎤 LAL BUTTON DABAYEIN (TAP TO TALK)",
    stop_prompt="🛑 BAS KAREIN (TAP TO STOP)",
    key='recorder'
)

# --- SATHI'S BRAIN (GEMINI INTEGRATION) ---
if audio:
    st.audio(audio['bytes'])
    
    # 1. Show the pulsing listening indicator
    st.markdown('<p class="pulsing-text">📻 Sathi is thinking... Please wait.</p>', unsafe_allow_html=True)
    
    try:
        # 2. Save the audio safely to a temporary file
        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as temp_audio:
            temp_audio.write(audio['bytes'])
            temp_audio_path = temp_audio.name
            
        # 3. Upload the audio file to Gemini
        voice_file = genai.upload_file(path=temp_audio_path)
        
        # 4. The strict instructions from your Sathi-AI Medical Research Document
        prompt = """
        You are Sathi, a warm and respectful digital companion for Indian elders.
        Listen to the audio and respond based on these strict rules:
        1. Tone: Always use respectful kinship terms (e.g., "Ji Dada ji", "Mata ji") and be empathetic.
        2. Format: Keep your response extremely short (2-3 simple sentences). Use English or Hinglish.
        3. Medical Rule: You are NOT a doctor. Do not prescribe medicines or change doses. 
        4. Emergency Rule: If they mention chest pain, sudden weakness, breathlessness, or heavy bleeding, immediately urge them to call emergency services or family.
        
        What should Sathi say back to the user?
        """
        
        # 5. Get the response
        response = model.generate_content([prompt, voice_file])
        
        # 6. Show the response on screen
        st.success(response.text)
        
        # 7. Clean up the temporary file
        os.remove(temp_audio_path)
        
    except Exception as e:
        st.error(f"Network error, please try again. Error details: {e}")
