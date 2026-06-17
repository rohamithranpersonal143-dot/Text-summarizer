import streamlit as st
from groq import Groq
import json
from PIL import Image
import io
import base64
import pypdf

# ==========================================
# PAGE SETUP
# ==========================================
st.set_page_config(
    page_title="My Study Buddy",
    page_icon="📱",
    layout="centered"
)

# ==========================================
# MODEL CONFIG
# ==========================================
VISION_MODEL = "meta-llama/llama-4-scout-17b-16e-instruct"
TEXT_MODEL = "llama-3.3-70b-versatile"
# ==========================================
# SIDEBAR SETTINGS
# ==========================================
st.sidebar.title("⚙️ Settings")

# API KEY (secrets or manual input)
if "GROQ_API_KEY" in st.secrets:
    api_key = st.secrets["GROQ_API_KEY"]
else:
    api_key = st.sidebar.text_input(
        "🔑 Enter Groq API Key:",
        type="password"
    )

# LANGUAGE (includes Tamil 🗿)
selected_language = st.sidebar.selectbox(
    "🌐 Output Language:",
    [
        "English",
        "Malay",
        "Tamil",
        "Spanish",
        "French",
        "German",
        "Chinese",
        "Japanese",
        "Arabic"
    ]
)

# DIFFICULTY LEVEL
difficulty_level = st.sidebar.selectbox(
    "🎯 Difficulty Level:",
    [
        "Kindergarten",
        "Year 1",
        "Year 2",
        "Year 3",
        "Year 4",
        "Year 5",
        "Year 6",
        "Secondary (Basic)",
        "Secondary (Advanced)"
    ]
)

st.sidebar.markdown("---")
st.sidebar.caption("Settings apply to all features")

# ==========================================
# API VALIDATION
# ==========================================
if not api_key:
    st.info("Please enter your Groq API key to continue.")
    st.stop()

client = Groq(api_key=api_key)
# ==========================================
# SESSION STATE INITIALIZATION
# ==========================================
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


# ==========================================
# DISPLAY FUNCTION (SUMMARY + QUIZ)
# ==========================================
def display_summary_and_quiz():

    # --------------------------
    # SUMMARY SECTION
    # --------------------------
    if st.session_state.summary:
        st.divider()
        st.header("📝 Smart Summary")
        st.write(st.session_state.summary)

    # --------------------------
    # QUIZ SECTION
    # --------------------------
    if st.session_state.quiz_data:

        st.divider()
        st.header("🧠 Practice Quiz")

        for q_idx, q_item in enumerate(st.session_state.quiz_data):

            st.subheader(f"Q{q_idx+1}: {q_item['question']}")

            options = q_item["options"]
            saved = st.session_state.user_answers.get(f"q_{q_idx}")

            # safe index handling
            index = options.index(saved) if saved in options else 0

            chosen = st.radio(
                "Select answer:",
                options,
                key=f"q_{q_idx}",
                index=index
            )

            st.session_state.user_answers[f"q_{q_idx}"] = chosen

            # show answers after grading
            if st.session_state.quiz_checked:
                correct = options[q_item["correct_index"]]

                if chosen == correct:
                    st.success("✅ Correct")
                else:
                    st.error(f"❌ Correct answer: {correct}")

            st.write("---")

        # --------------------------
        # GRADING BUTTON
        # --------------------------
        if not st.session_state.quiz_checked:

            if st.button("📊 Grade My Quiz"):
                st.session_state.quiz_checked = True
                st.rerun()

        else:
            score = 0

            for i, q in enumerate(st.session_state.quiz_data):
                if st.session_state.user_answers.get(f"q_{i}") == q["options"][q["correct_index"]]:
                    score += 1

            st.success(f"🎯 Score: {score}/{len(st.session_state.quiz_data)}")

            if st.button("🔄 Reset Quiz"):
                st.session_state.user_answers = {}
                st.session_state.quiz_checked = False
                st.rerun()
# ==========================================
# FEATURE 1: TEXT SCANNER
# ==========================================
st.title("📷 Mobile Text Scanner")

# Camera toggle
if st.session_state.camera_on:
    if st.button("🔴 Turn Camera OFF"):
        st.session_state.camera_on = False
        st.rerun()
else:
    if st.button("📷 Turn Camera ON"):
        st.session_state.camera_on = True
        st.rerun()

# Camera input
if st.session_state.camera_on:

    img_file = st.camera_input("Capture text")

    if img_file:

        with st.spinner("Reading text..."):

            # Open image
            img = Image.open(img_file)

            # Convert to bytes
            buf = io.BytesIO()
            img.save(buf, format="JPEG")

            # Base64 encode
            b64 = base64.b64encode(buf.getvalue()).decode()

            # PROMPT
            prompt = "Extract all text exactly. Do not explain."

            # ==========================================
            # FIXED VISION CALL (NO BRACKET ERRORS)
            # ==========================================
            response = client.chat.completions.create(
                model=VISION_MODEL,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": prompt
                            },
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/jpeg;base64,{b64}"
                                }
                            }
                        ]
                    }
                ],
                temperature=0
            )

            st.session_state.scanned_text = response.choices[0].message.content


# ==========================================
# SHOW SCANNED TEXT
# ==========================================
if st.session_state.scanned_text:

    st.success("Text extracted")
    st.code(st.session_state.scanned_text)

    if st.button("➡️ Send to Quiz Generator"):

        st.session_state.summary = ""
        st.session_state.quiz_data = []

        master_prompt = f"""
Analyze the text.

Language: {selected_language}
Difficulty: {difficulty_level}

Rules:
- Adjust difficulty properly
- Kindergarten = very simple
- Year 1-3 = basic understanding
- Year 4-6 = inference
- Secondary = analysis

OUTPUT 1: 5 bullet summary

OUTPUT 2: 10 MCQs JSON:
[
  {{
    "question": "...",
    "options": ["A","B","C","D"],
    "correct_index": 0
  }}
]

===SPLIT_HERE===

TEXT:
{st.session_state.scanned_text}
"""

        response = client.chat.completions.create(
            model=TEXT_MODEL,
            messages=[{"role": "user", "content": master_prompt}]
        )

        raw = response.choices[0].message.content

        if "===SPLIT_HERE===" in raw:

            summary, quiz = raw.split("===SPLIT_HERE===")

            st.session_state.summary = summary.strip()

            start = quiz.find("[")
            end = quiz.rfind("]") + 1

            st.session_state.quiz_data = json.loads(quiz[start:end])

        st.session_state.user_answers = {}
        st.session_state.quiz_checked = False

        st.rerun()

# show UI
display_summary_and_quiz()
# ==========================================
# FEATURE 2: STUDY BUDDY (TEXT + PDF)
# ==========================================
st.title("📚 My Study Buddy")

input_type = st.radio("Input Type", ["Paste Text", "Upload PDF"])

text = ""

# --------------------------
# TEXT INPUT
# --------------------------
if input_type == "Paste Text":
    text = st.text_area("Paste here", height=200)

# --------------------------
# PDF INPUT
# --------------------------
else:
    file = st.file_uploader("Upload PDF", type=["pdf"])

    if file:
        reader = pypdf.PdfReader(file)
        text = "\n".join([page.extract_text() or "" for page in reader.pages])


# --------------------------
# PROCESS BUTTON
# --------------------------
if st.button("Process"):

    if not text.strip():
        st.warning("No text found.")
        st.stop()

    # ==========================
    # SUMMARY PROMPT
    # ==========================
    summary_prompt = f"""
Create 5 bullet points.

Language: {selected_language}
Difficulty: {difficulty_level}

TEXT:
{text}
"""

    # ==========================
    # QUIZ PROMPT
    # ==========================
    quiz_prompt = f"""
Return JSON only.

Language: {selected_language}
Difficulty: {difficulty_level}

Generate 10 MCQs.

TEXT:
{text}

Format:
{{
  "questions": [
    {{
      "question": "...",
      "options": ["A","B","C","D"],
      "correct_index": 0
    }}
  ]
}}
"""

    # ==========================
    # GROQ CALLS
    # ==========================
    summary_response = client.chat.completions.create(
        model=TEXT_MODEL,
        messages=[{"role": "user", "content": summary_prompt}]
    )

    quiz_response = client.chat.completions.create(
        model=TEXT_MODEL,
        messages=[{"role": "user", "content": quiz_prompt}],
        response_format={"type": "json_object"}
    )

    # ==========================
    # STORE RESULTS
    # ==========================
    st.session_state.summary = summary_response.choices[0].message.content

    parsed = json.loads(quiz_response.choices[0].message.content)
    st.session_state.quiz_data = parsed.get("questions", parsed)

    # reset quiz state
    st.session_state.user_answers = {}
    st.session_state.quiz_checked = False

    st.rerun()


# ==========================================
# FINAL DISPLAY CALL
# ==========================================
display_summary_and_quiz()

