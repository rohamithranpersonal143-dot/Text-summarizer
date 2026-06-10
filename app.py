import streamlit as st
import google.generativeai as genai
import json

# Mobile UI Optimization
st.set_page_config(page_title="EduSummarizer", page_icon="📚", layout="centered")

st.title("📚 Lecture Summarizer & Quizzer")
st.write("Upload text or a PDF to instantly get key summaries and a custom practice quiz.")

# 1. Secure API Key Setup
# On Streamlit Cloud, go to App Settings -> Secrets and add: GEMINI_API_KEY = "your_key"
# If not set in secrets, we provide a text input fallback directly in the app.
if "GEMINI_API_KEY" in st.secrets:
    api_key = st.secrets["GEMINI_API_KEY"]
else:
    api_key = st.sidebar.text_input("🔑 Enter Gemini API Key:", type="password")

if not api_key:
    st.info("💡 To start, please enter your free Gemini API Key in the sidebar or add it to Streamlit Secrets!")
    st.stop()

# Configure the Gemini Model
genai.configure(api_key=api_key)
model = genai.GenerativeModel('gemini-2.5-flash') # Ultra-fast, perfect for text processing

# Initialize Session States to keep data alive on mobile page refreshes
if "summary" not in st.session_state:
    st.session_state.summary = ""
if "quiz_data" not in st.session_state:
    st.session_state.quiz_data = []
if "user_answers" not in st.session_state:
    st.session_state.user_answers = {}
if "quiz_checked" not in st.session_state:
    st.session_state.quiz_checked = False

# 2. Input Methods
input_type = st.radio("Choose Input Type:", ["📋 Paste Lecture Text", "📄 Upload PDF (Text-based)"])
lecture_text = ""

if input_type == "📋 Paste Lecture Text":
    lecture_text = st.text_area("Paste your study material or lecture notes here:", height=200, placeholder="Paste paragraphs, slides, or chapters...")
else:
    uploaded_file = st.file_uploader("Upload a text-based PDF file", type=["pdf"])
    if uploaded_file is not None:
        try:
            import pypdf
            pdf_reader = pypdf.PdfReader(uploaded_file)
            extracted_pages = [page.extract_text() for page in pdf_reader.pages if page.extract_text()]
            lecture_text = "\n".join(extracted_pages)
            st.success(f"Successfully extracted text from {len(pdf_reader.pages)} pages!")
        except ImportError:
            st.error("Error: Please make sure 'pypdf' is added to your requirements.txt file.")
            st.stop()

# 3. Process Button
if st.button("🚀 Process Material", use_container_width=True):
    if not lecture_text.strip():
        st.warning("Please provide some lecture text or a PDF first!")
    else:
        with st.spinner("🧠 AI is analyzing and generating your study kit..."):
            try:
                # Prompt 1: Generate Summary
                summary_prompt = f"Analyze the following lecture notes. Provide a highly structured summary consisting of exactly 5 critical bullet points. Keep it clear and optimized for quick mobile reading:\n\n{lecture_text}"
                summary_response = model.generate_content(summary_prompt)
                st.session_state.summary = summary_response.text

                # Prompt 2: Generate JSON Quiz Data
                quiz_prompt = (
                    f"Based on the following lecture notes, generate exactly 3 multiple-choice practice questions. "
                    f"You must return the response ONLY as a valid JSON array of objects. Do not include markdown code block formatting (like ```json). "
                    f"Each object must have exactly these keys: 'question', 'options' (an array of 4 text strings), and 'correct_index' (the 0, 1, 2, or 3 index of the right answer).\n\n"
                    f"Lecture Notes:\n{lecture_text}"
                )
                quiz_response = model.generate_content(quiz_prompt)
                
                # Clean up potential markdown wrappers from API string responses safely
                raw_json = quiz_response.text.strip().replace("```json", "").replace("```", "")
                st.session_state.quiz_data = json.loads(raw_json)
                
                # Reset quiz states for the new session
                st.session_state.user_answers = {}
                st.session_state.quiz_checked = False
                st.rerun()
            except Exception as e:
                st.error(f"Failed to process material. Error details: {e}")

# 4. Display Results
if st.session_state.summary:
    st.divider()
    st.header("📝 Smart Summary")
    st.write(st.session_state.summary)

if st.session_state.quiz_data:
    st.divider()
    st.header("🧠 Practice Quiz")
    
    # Render quiz questions dynamically using mobile-friendly radio items
    for q_idx, q_item in enumerate(st.session_state.quiz_data):
        st.subheader(f"Q{q_idx + 1}: {q_item['question']}")
        
        # Save choice inside session state safely
        chosen_option = st.radio(
            "Select your answer:", 
            q_item['options'], 
            key=f"q_{q_idx}", 
            index=None if f"q_{q_idx}" not in st.session_state.user_answers else q_item['options'].index(st.session_state.user_answers[f"q_{q_idx}"])
        )
        if chosen_option:
            st.session_state.user_answers[f"q_{q_idx}"] = chosen_option

        # Feedback reveal mechanic
        if st.session_state.quiz_checked:
            correct_ans = q_item['options'][q_item['correct_index']]
            if chosen_option == correct_ans:
                st.success("✅ Correct!")
            else:
                st.error(f"❌ Incorrect. The correct answer was: {correct_ans}")
        st.write("---")

    # Quiz grading interaction logic
    if not st.session_state.quiz_checked:
        if st.button("📊 Grade My Quiz", use_container_width=True):
            if len(st.session_state.user_answers) < len(st.session_state.quiz_data):
                st.warning("Please answer all questions before grading!")
            else:
                st.session_state.quiz_checked = True
                st.rerun()
    else:
        if st.button("🔄 Reset Quiz", use_container_width=True):
            st.session_state.user_answers = {}
            st.session_state.quiz_checked = False
            st.rerun()
