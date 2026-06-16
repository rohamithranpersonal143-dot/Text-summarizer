import streamlit as st
from google import genai  # Modern production SDK
from google.genai import types  # Required for configuration types
import json
from PIL import Image

# Mobile Layout Setup
st.set_page_config(page_title="My Study Buddy", page_icon="📱", layout="centered")

# 1. Secure API Key Authentication
if "GEMINI_API_KEY" in st.secrets:
    api_key = st.secrets["GEMINI_API_KEY"]
else:
    api_key = st.sidebar.text_input("🔑 Enter Gemini API Key:", type="password")

# Language Selection
selected_language = st.sidebar.selectbox(
    "🌐 Choose Output Language:",
    ["English", "Spanish", "French", "German", "Chinese", "Malay", "Japanese", "Arabic"]
)

if not api_key:
    st.info("💡 Please add your Gemini API Key in the sidebar or Streamlit Secrets to begin.")
    st.stop()

# Initialize the modern standard client and model configuration
client = genai.Client(api_key=api_key)
MODEL_NAME = "gemini-2.5-flash"

# Initialize ALL session states at the top to prevent missing attribute errors
if "summary" not in st.session_state:
    st.session_state.summary = ""
if "quiz_data" not in st.session_state:
    st.session_state.quiz_data = []
if "user_answers" not in st.session_state:
    st.session_state.user_answers = {}
if "quiz_checked" not in st.session_state:
    st.session_state.quiz_checked = False
if "scanned_text" not in st.session_state:
    st.session_state.scanned_text = ""
if "camera_on" not in st.session_state:
    st.session_state.camera_on = False
if "last_processed_image" not in st.session_state:
    st.session_state.last_processed_image = None


# Helper function to display quiz results cleanly across tabs
def display_summary_and_quiz():
    # Display Summary Results
    if st.session_state.summary:
        st.divider()
        st.header("📝 Smart Summary")
        st.write(st.session_state.summary)

    # Display Quiz Results
    if st.session_state.quiz_data:
        st.divider()
        st.header("🧠 Practice Quiz")
        for q_idx, q_item in enumerate(st.session_state.quiz_data):
            st.subheader(f"Q{q_idx + 1}: {q_item['question']}")

            # Safely calculate index
            saved_answer = st.session_state.user_answers.get(f"q_{q_idx}")
            current_index = q_item['options'].index(saved_answer) if saved_answer in q_item['options'] else None

            # Form-based tracking for selected radio values
            chosen_option = st.radio(
                "Select answer:",
                q_item['options'],
                key=f"q_{q_idx}",
                index=current_index
            )
            if chosen_option:
                st.session_state.user_answers[f"q_{q_idx}"] = chosen_option

            if st.session_state.quiz_checked:
                correct_ans = q_item['options'][q_item['correct_index']]
                if chosen_option == correct_ans:
                    st.success("✅ Correct!")
                else:
                    st.error(f"❌ Incorrect. Correct answer: {correct_ans}")
            st.write("---")

        if not st.session_state.quiz_checked:
            if st.button("📊 Grade My Quiz", use_container_width=True):
                st.session_state.quiz_checked = True
                st.rerun()
        else:
            if st.button("🔄 Reset Quiz", use_container_width=True):
                st.session_state.user_answers = {}
                st.session_state.quiz_checked = False
                st.rerun()


# 2. Top Navigation Menu for Mobile
app_mode = st.selectbox("🗺️ Choose Feature:",
                        ["📷 1. Text Scanner (Google Lens Mode)", "📚 2. Text/PDF Summarizer & Quizzer"])

# ==========================================
# FEATURE 1: CAMERA TEXT SCANNER
# ==========================================
if app_mode == "📷 1. Text Scanner (Google Lens Mode)":
    st.title("📷 Mobile Text Scanner")
    st.write("Snap a photo of a book, paper, or screen to instantly extract and copy the text.")

    if st.session_state.camera_on:
        if st.button("🔴 Turn Camera OFF", use_container_width=True):
            st.session_state.camera_on = False
            st.rerun()
    else:
        if st.button("📷 Turn Camera ON", use_container_width=True):
            st.session_state.camera_on = True
            st.rerun()

    if st.session_state.camera_on:
        img_file = st.camera_input("Position your text clearly in the frame:")
        if img_file is not None:
            # Avoid re-running OCR if the image hasn't changed
            if st.session_state.last_processed_image != img_file.getvalue():
                with st.spinner("🔍 AI is reading the text..."):
                    try:
                        img = Image.open(img_file)
                        prompt = "Look at this image. Extract every piece of text visible in it. Format it cleanly exactly as it appears. Do not summarize or add chat text, just give the text."
                        response = client.models.generate_content(
                            model=MODEL_NAME,
                            contents=[prompt, img]
                        )
                        st.session_state.scanned_text = response.text
                        st.session_state.last_processed_image = img_file.getvalue()
                        st.rerun()
                    except Exception as e:
                        st.error(f"Failed to scan text: {e}")

    if st.session_state.scanned_text:
        st.success("✨ Text Extracted!")

        st.code(st.session_state.scanned_text, language="text")

        if st.button("🧠 Send to Summarizer & Quizzer", use_container_width=True):
            st.session_state.summary = "" 
            st.session_state.quiz_data = [] 
            
            with st.spinner(f"Parsing text into study materials in {selected_language}..."):
                try:
                    master_prompt = f"Analyze the following source text. Provide two distinct outputs formatted precisely as requested. Both outputs must be completely written in the following language: {selected_language}.\n\nOUTPUT 1: A highly structured summary consisting of exactly 5 critical bullet points written in {selected_language}.\n\nOUTPUT 2: Exactly 3 multiple-choice practice questions from this text. The questions, choices, and data must be written in {selected_language}. Format this section strictly as a valid JSON array of objects with keys: 'question', 'options' (array of 4 strings), and 'correct_index' (integer 0-3).\n\nSeparate OUTPUT 1 and OUTPUT 2 clearly using the delimiter line: '===SPLIT_HERE==='\n\nSource Text:\n{st.session_state.scanned_text}"
                    
                    response = client.models.generate_content(model=MODEL_NAME, contents=master_prompt)
                    raw_output = response.text
                    
                    if "===SPLIT_HERE===" in raw_output:
                        summary_part, quiz_part = raw_output.split("===SPLIT_HERE===", 1)
                        st.session_state.summary = summary_part.strip()
                        
                        start_idx = quiz_part.find("[")
                        end_idx = quiz_part.rfind("]") + 1
                        
                        if start_idx != -1 and end_idx != 0:
                            clean_json = quiz_part[start_idx:end_idx]
                            st.session_state.quiz_data = json.loads(clean_json)
                        else:
                            st.session_state.quiz_data = json.loads(quiz_part.strip().replace("```json", "").replace("```", ""))
                    else:
                        st.session_state.summary = raw_output
                        st.warning("Could not cleanly separate the quiz. Please try again.")

                    st.session_state.user_answers = {}
                    st.session_state.quiz_checked = False
                    st.toast("Generated! See your summary and quiz below.")
                    st.rerun()
                    
                except Exception as e:
                    if "429" in str(e):
                        st.error("⏳ Google's free tier limit reached. Please wait 30-60 seconds before trying again!")
                    else:
                        st.error(f"Processing failed: {e}")

        display_summary_and_quiz()

# ==========================================
# FEATURE 2: SUMMARIZER & QUIZZER
# ==========================================
else:
    st.title("📚 My Study Buddy")
    st.write("Upload a file or paste text to generate custom summaries and quizzes.")

    input_type = st.radio("Choose Input Type:", ["📋 Paste Text", "📄 Upload PDF"])
    lecture_text = ""

    if input_type == "📋 Paste Text":
        lecture_text = st.text_area("Paste material here:", height=150)
    else:
        uploaded_file = st.file_uploader("Upload text PDF", type=["pdf"])
        if uploaded_file is not None:
            import pypdf
            try:
                pdf_reader = pypdf.PdfReader(uploaded_file)
                lecture_text = "\n".join([page.extract_text() for page in pdf_reader.pages if page.extract_text()])
            except Exception as e:
                st.error(f"Failed to read PDF file: {e}")

    if st.button("🚀 Process Material", use_container_width=True):
        if not lecture_text.strip():
            st.warning("Please provide text or a PDF file first!")
        else:
            st.session_state.summary = "" 
            st.session_state.quiz_data = []
            
            with st.spinner(f"🧠 AI is building your study kit in {selected_language}..."):
                try:
                    # Single master prompt approach used here to keep it identical to the camera processing logic
