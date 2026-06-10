import streamlit as st
import google.generativeai as genai
import json
from PIL import Image

# Mobile Layout Setup
st.set_page_config(page_title="Pocket Lens & Study Kit", page_icon="📱", layout="centered")

# 1. Secure API Key Authentication
if "GEMINI_API_KEY" in st.secrets:
    api_key = st.secrets["GEMINI_API_KEY"]
else:
    api_key = st.sidebar.text_input("🔑 Enter Gemini API Key:", type="password")

if not api_key:
    st.info("💡 Please add your Gemini API Key in the sidebar or Streamlit Secrets to begin.")
    st.stop()

genai.configure(api_key=api_key)
model = genai.GenerativeModel('gemini-2.5-flash')

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

# 2. Top Navigation Menu for Mobile
app_mode = st.selectbox("🗺️ Choose Feature:", ["📷 1. Text Scanner (Google Lens Mode)", "📚 2. Text/PDF Summarizer & Quizzer"])

# ==========================================
# FEATURE 1: CAMERA TEXT SCANNER
# ==========================================
if app_mode == "📷 1. Text Scanner (Google Lens Mode)":
    st.title("📷 Mobile Text Scanner")
    st.write("Snap a photo of a book, paper, or screen to instantly extract and copy the text.")
    
    if "camera_on" not in st.session_state:
        st.session_state.camera_on = False

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
            with st.spinner("🔍 AI is reading the text..."):
                try:
                    img = Image.open(img_file)
                    prompt = "Look at this image. Extract every piece of text visible in it. Format it cleanly exactly as it appears. Do not summarize or add chat text, just give the text."
                    response = model.generate_content([prompt, img])
                    st.session_state.scanned_text = response.text
                except Exception as e:
                    st.error(f"Failed to scan text: {e}")

    if st.session_state.scanned_text:
        st.success("✨ Text Extracted!")
        st.code(st.session_state.scanned_text, language="text")
        st.copy_to_clipboard(st.session_state.scanned_text, before_copy_label="📋 Copy to Clipboard", after_copy_label="✅ Copied!")
        
        # Cool bonus feature: send this scanned text straight to the summarizer tool!
        if st.button("🧠 Send to Summarizer & Quizzer", use_container_width=True):
            st.session_state.summary = "" # Clear old summary
            st.session_state.quiz_data = [] # Clear old quiz
            # Run the AI logic using the scanned text
            with st.spinner("Parsing text into study materials..."):
                sum_prompt = f"Provide a highly structured summary consisting of exactly 5 critical bullet points:\n\n{st.session_state.scanned_text}"
                st.session_state.summary = model.generate_content(sum_prompt).text
                
                quiz_prompt = f"Generate exactly 3 multiple-choice practice questions from this text. Return ONLY a valid JSON array of objects with keys: 'question', 'options' (array of 4 strings), and 'correct_index' (integer 0-3).\n\n{st.session_state.scanned_text}"
                raw_json = model.generate_content(quiz_prompt).text.strip().replace("```json", "").replace("```", "")
                st.session_state.quiz_data = json.loads(raw_json)
                st.session_state.user_answers = {}
                st.session_state.quiz_checked = False
                st.toast("Sent! Switch to the Summarizer tab to view.")

# ==========================================
# FEATURE 2: SUMMARIZER & QUIZZER
# ==========================================
else:
    st.title("📚 Lecture Summarizer & Quizzer")
    st.write("Upload a file or paste text to generate custom summaries and quizzes.")
    
    input_type = st.radio("Choose Input Type:", ["📋 Paste Text", "📄 Upload PDF"])
    lecture_text = ""

    if input_type == "📋 Paste Text":
        lecture_text = st.text_area("Paste material here:", height=150)
    else:
        uploaded_file = st.file_uploader("Upload text PDF", type=["pdf"])
        if uploaded_file is not None:
            import pypdf
            pdf_reader = pypdf.PdfReader(uploaded_file)
            lecture_text = "\n".join([page.extract_text() for page in pdf_reader.pages if page.extract_text()])

    if st.button("🚀 Process Material", use_container_width=True):
        if not lecture_text.strip():
            st.warning("Please provide text or a PDF file first!")
        else:
            with st.spinner("🧠 AI is building your study kit..."):
                try:
                    st.session_state.summary = model.generate_content(f"Provide a summary of exactly 5 critical bullet points:\n\n{lecture_text}").text
                    
                    quiz_prompt = f"Generate exactly 3 multiple-choice questions. Return ONLY a valid JSON array of objects with keys: 'question', 'options' (array of 4 strings), and 'correct_index' (integer 0-3).\n\n{lecture_text}"
                    raw_json = model.generate_content(quiz_prompt).text.strip().replace("```json", "").replace("```", "")
                    st.session_state.quiz_data = json.loads(raw_json)
                    st.session_state.user_answers = {}
                    st.session_state.quiz_checked = False
                    st.rerun()
                except Exception as e:
                    st.error(f"Error processing: {e}")

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
            chosen_option = st.radio("Select answer:", q_item['options'], key=f"q_{q_idx}", index=None if f"q_{q_idx}" not in st.session_state.user_answers else q_item['options'].index(st.session_state.user_answers[f"q_{q_idx}"]))
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
