import streamlit as st
from groq import Groq
import json
from PIL import Image
import io
import base64
import pypdf

# =====================================================
# PAGE CONFIG
# =====================================================
st.set_page_config(
    page_title="Study Buddy Pro",
    page_icon="📘",
    layout="centered"
)

# =====================================================
# MODELS
# =====================================================
VISION_MODEL = "meta-llama/llama-4-scout-17b-16e-instruct"
TEXT_MODEL = "llama-3.3-70b-versatile"

# =====================================================
# SIDEBAR
# =====================================================
st.sidebar.title("⚙️ Settings")

api_key = st.secrets.get("GROQ_API_KEY") or st.sidebar.text_input(
    "Groq API Key",
    type="password"
)

language = st.sidebar.selectbox(
    "Language",
    ["English", "Malay", "Tamil", "Spanish", "French", "German", "Chinese", "Japanese", "Arabic"]
)

difficulty = st.sidebar.selectbox(
    "Difficulty",
    ["Kindergarten", "Year 1", "Year 2", "Year 3", "Year 4", "Year 5", "Year 6",
     "Secondary (Basic)", "Secondary (Advanced)"]
)

if not api_key:
    st.info("Enter API key to continue")
    st.stop()

client = Groq(api_key=api_key)

# =====================================================
# SESSION STATE
# =====================================================
st.session_state.setdefault("scan_text", "")
st.session_state.setdefault("camera_on", False)

st.session_state.setdefault("study_summary", "")
st.session_state.setdefault("study_quiz", [])
st.session_state.setdefault("study_answers", {})
st.session_state.setdefault("study_checked", False)

# =====================================================
# CAMERA SCANNER
# =====================================================
st.title("📷 Scanner")

col1, col2 = st.columns(2)

with col1:
    if st.button("📷 Toggle Camera"):
        st.session_state.camera_on = not st.session_state.camera_on

with col2:
    if st.button("🧹 Clear Scan"):
        st.session_state.scan_text = ""

if st.session_state.camera_on:
    img = st.camera_input("Capture text")

    if img:
        image = Image.open(img)

        buffer = io.BytesIO()
        image.save(buffer, format="JPEG")
        b64 = base64.b64encode(buffer.getvalue()).decode()

        response = client.chat.completions.create(
            model=VISION_MODEL,
            messages=[{
                "role": "user",
                "content": [
                    {"type": "text", "text": "Extract all text exactly."},
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64}"}}
                ]
            }]
        )

        st.session_state.scan_text = response.choices[0].message.content

# =====================================================
# SHOW SCANNED TEXT
# =====================================================
if st.session_state.scan_text:

    st.subheader("Extracted Text")
    st.code(st.session_state.scan_text)

    if st.button("🧠 Generate Quiz from Scan"):

        quiz_prompt = f"""
You are an exam generator.

RULES:
- Generate EXACTLY 10 questions
- JSON ONLY
- No explanations

Format:
{{
  "questions": [
    {{
      "question": "string",
      "options": ["A","B","C","D"],
      "correct_index": 0
    }}
  ]
}}

TEXT:
{st.session_state.scan_text}
"""

        summary_prompt = f"""
You are a strict extractor.

Rules:
- No interpretation
- No philosophy
- No emotion
- Only factual bullets
- Exactly 5 bullets

TEXT:
{st.session_state.scan_text}
"""

        summary_res = client.chat.completions.create(
            model=TEXT_MODEL,
            messages=[{"role": "user", "content": summary_prompt}]
        )

        quiz_res = client.chat.completions.create(
            model=TEXT_MODEL,
            messages=[{"role": "user", "content": quiz_prompt}],
            response_format={"type": "json_object"}
        )

        st.session_state.study_summary = summary_res.choices[0].message.content
        st.session_state.study_quiz = json.loads(quiz_res.choices[0].message.content)

        st.session_state.study_answers = {}
        st.session_state.study_checked = False

        st.rerun()

# =====================================================
# PDF / TEXT INPUT
# =====================================================
st.divider()
st.title("📚 Study Buddy")

mode = st.radio("Input Type", ["Paste Text", "Upload PDF"])

text = ""

if mode == "Paste Text":
    text = st.text_area("Enter text", height=200)

else:
    file = st.file_uploader("Upload PDF", type=["pdf"])
    if file:
        reader = pypdf.PdfReader(file)
        text = "\n".join(page.extract_text() or "" for page in reader.pages)

# =====================================================
# PROCESS TEXT
# =====================================================
if st.button("Process Text"):

    if not text.strip():
        st.warning("No text found")
        st.stop()

    summary_prompt = f"""
You are a strict extractor.

Rules:
- Only facts from text
- No interpretation
- No philosophy
- No storytelling
- Exactly 5 bullet points

TEXT:
{text}
"""

    quiz_prompt = f"""
You are an exam generator.

RULES:
- Generate EXACTLY 10 MCQs
- JSON ONLY

Format:
{{
  "questions": [
    {{
      "question": "string",
      "options": ["A","B","C","D"],
      "correct_index": 0
    }}
  ]
}}

TEXT:
{text}
"""

    summary_res = client.chat.completions.create(
        model=TEXT_MODEL,
        messages=[{"role": "user", "content": summary_prompt}]
    )

    quiz_res = client.chat.completions.create(
        model=TEXT_MODEL,
        messages=[{"role": "user", "content": quiz_prompt}],
        response_format={"type": "json_object"}
    )

    st.session_state.study_summary = summary_res.choices[0].message.content
    st.session_state.study_quiz = json.loads(quiz_res.choices[0].message.content)

    st.session_state.study_answers = {}
    st.session_state.study_checked = False

    st.rerun()

# =====================================================
# QUIZ DISPLAY
# =====================================================
if st.session_state.study_summary:
    st.subheader("📝 Summary")
    st.write(st.session_state.study_summary)

if st.session_state.study_quiz:

    st.subheader("🧠 Quiz")

    for i, q in enumerate(st.session_state.study_quiz["questions"]):

        st.write(q["question"])

        answer = st.radio(
            "Select answer",
            q["options"],
            key=f"q_{i}"
        )

        st.session_state.study_answers[f"q_{i}"] = answer

        if st.session_state.study_checked:
            correct = q["options"][q["correct_index"]]
            if answer == correct:
                st.success("Correct")
            else:
                st.error(f"Correct answer: {correct}")

# =====================================================
# GRADE + RESET
# =====================================================
if st.session_state.study_quiz:

    col1, col2 = st.columns(2)

    with col1:
        if st.button("📊 Grade Quiz"):
            st.session_state.study_checked = True
            st.rerun()

    with col2:
        if st.button("🔄 Reset Quiz"):
            st.session_state.study_answers = {}
            st.session_state.study_checked = False
            st.rerun()
