import streamlit as st
from google import genai
import json
from PIL import Image

st.set_page_config(page_title="My Study Buddy", page_icon="📱", layout="centered")

if "GEMINI_API_KEY" in st.secrets:
    api_key = st.secrets["GEMINI_API_KEY"]
else:
    api_key = st.sidebar.text_input("🔑 Enter Gemini API Key:", type="password")

if not api_key:
    st.info("💡 Please add your Gemini API Key in the sidebar or Streamlit Secrets to begin.")
    st.stop()

client = genai.Client(api_key=api_key)
MODEL_NAME = "gemini-2.5-flash"

LANGUAGE = st.sidebar.selectbox(
    "🌍 Study Language",
    [
        "English",
        "Bahasa Melayu",
        "中文 (Chinese)",
        "தமிழ் (Tamil)",
        "日本語 (Japanese)",
        "한국어 (Korean)",
        "Español (Spanish)",
        "Français (French)",
        "Deutsch (German)"
    ]
)

defaults = {
    "summary": "",
    "quiz_data": [],
    "user_answers": {},
    "quiz_checked": False,
    "scanned_text": "",
    "camera_on": False
}

for k, v in defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v


def extract_json_array(text):
    if not text:
        raise ValueError("Empty response from Gemini")

    text = text.replace("```json", "").replace("```", "").strip()

    start = text.find("[")
    end = text.rfind("]")

    if start == -1 or end == -1:
        raise ValueError(f"No JSON array found:\n{text[:500]}")

    return json.loads(text[start:end + 1])


def display_summary_and_quiz():
    if st.session_state.summary:
        st.divider()
        st.header("📝 Smart Summary")
        st.write(st.session_state.summary)

    if st.session_state.quiz_data:
        st.divider()
        st.header("🧠 Practice Quiz")

        for q_idx, q_item in enumerate(st.session_state.quiz_data):
            st.subheader(f"Q{q_idx + 1}: {q_item['question']}")

            selected = st.radio(
                "Select answer:",
                q_item["options"],
                key=f"q_{q_idx}",
                index=None
            )

            if selected:
                st.session_state.user_answers[f"q_{q_idx}"] = selected

            if st.session_state.quiz_checked:
                correct = q_item["options"][q_item["correct_index"]]

                if selected == correct:
                    st.success("✅ Correct!")
                else:
                    st.error(f"❌ Correct answer: {correct}")

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


def generate_study_material(text_source):
    master_prompt = f"""
Analyze the source material.

OUTPUT 1:
Exactly 5 critical bullet points.
Write entirely in {LANGUAGE}.

OUTPUT 2:
Exactly 3 multiple-choice questions.
Write entirely in {LANGUAGE}.

Return OUTPUT 2 as JSON only.

Use:
===SPLIT_HERE===

JSON format:

[
  {{
    "question":"Question",
    "options":["A","B","C","D"],
    "correct_index":0
  }}
]

Source:
{text_source}
"""

    response = client.models.generate_content(
        model=MODEL_NAME,
        contents=master_prompt
    )

    raw_output = response.text

    if "===SPLIT_HERE===" not in raw_output:
        st.session_state.summary = raw_output
        return

    summary_part, quiz_part = raw_output.split("===SPLIT_HERE===", 1)

    st.session_state.summary = summary_part.strip()
    st.session_state.quiz_data = extract_json_array(quiz_part)
    st.session_state.user_answers = {}
    st.session_state.quiz_checked = False


app_mode = st.selectbox(
    "🗺️ Choose Feature:",
    ["📷 1. Text Scanner (Google Lens Mode)",
     "📚 2. Text/PDF Summarizer & Quizzer"]
)

if app_mode.startswith("📷"):
    st.title("📷 Mobile Text Scanner")

    if st.session_state.camera_on:
        if st.button("🔴 Turn Camera OFF", use_container_width=True):
            st.session_state.camera_on = False
            st.rerun()
    else:
        if st.button("📷 Turn Camera ON", use_container_width=True):
            st.session_state.camera_on = True
            st.rerun()

    if st.session_state.camera_on:
        img_file = st.camera_input("Take a photo")

        if img_file:
            try:
                img = Image.open(img_file)

                response = client.models.generate_content(
                    model=MODEL_NAME,
                    contents=[
                        "Extract all visible text exactly as written.",
                        img
                    ]
                )

                st.session_state.scanned_text = response.text

            except Exception as e:
                st.error(f"OCR failed: {e}")

    if st.session_state.scanned_text:
        st.code(st.session_state.scanned_text)

        if st.button("🧠 Send to Summarizer & Quizzer", use_container_width=True):
            try:
                generate_study_material(st.session_state.scanned_text)
                st.rerun()
            except Exception as e:
                st.error(f"Processing failed: {e}")

        display_summary_and_quiz()

else:
    st.title("📚 My Study Buddy")

    input_type = st.radio(
        "Choose Input Type:",
        ["📋 Paste Text", "📄 Upload PDF"]
    )

    lecture_text = ""

    if input_type == "📋 Paste Text":
        lecture_text = st.text_area("Paste material here:", height=200)

    else:
        uploaded_file = st.file_uploader("Upload PDF", type=["pdf"])

        if uploaded_file:
            import pypdf

            reader = pypdf.PdfReader(uploaded_file)

            lecture_text = "\\n".join(
                page.extract_text()
                for page in reader.pages
                if page.extract_text()
            )

    if st.button("🚀 Process Material", use_container_width=True):

        if not lecture_text.strip():
            st.warning("Please provide text first.")
        else:
            try:
                generate_study_material(lecture_text)
                st.rerun()

            except Exception as e:
                st.error(f"Error processing: {e}")

    display_summary_and_quiz()
