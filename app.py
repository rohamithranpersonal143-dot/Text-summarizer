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
# MODELS
# ==========================================
VISION_MODEL = "meta-llama/llama-4-scout-17b-16e-instruct"
TEXT_MODEL = "llama-3.3-70b-versatile"
# ==========================================
# SIDEBAR SETTINGS
# ==========================================
st.sidebar.title("⚙️ Settings")

# API KEY (secrets OR manual input)
if "GROQ_API_KEY" in st.secrets:
    api_key = st.secrets["GROQ_API_KEY"]
else:
    api_key = st.sidebar.text_input(
        "🔑 Enter Groq API Key",
        type="password"
    )

# LANGUAGE
selected_language = st.sidebar.selectbox(
    "🌐 Output Language",
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

# DIFFICULTY
difficulty_level = st.sidebar.selectbox(
    "🎯 Difficulty Level",
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
st.sidebar.caption("Multi-prompt AI system enabled")

# ==========================================
# API SAFETY CHECK
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

if "concepts" not in st.session_state:
    st.session_state.concepts = ""

if "quiz_data" not in st.session_state:
    st.session_state.quiz_data = []

if "user_answers" not in st.session_state:
    st.session_state.user_answers = {}

if "quiz_checked" not in st.session_state:
    st.session_state.quiz_checked = False

if "input_text" not in st.session_state:
    st.session_state.input_text = ""

# pipeline control (IMPORTANT for multi-prompt system)
if "processing_done" not in st.session_state:
    st.session_state.processing_done = False
# ==========================================
# PROCESS BUTTON (MULTI-PROMPT PIPELINE)
# ==========================================
if st.button("🚀 Process Text"):

    if not st.session_state.input_text.strip():
        st.warning("Please enter or upload text first.")
        st.stop()

    text = st.session_state.input_text

    # RESET OLD DATA
    st.session_state.summary = ""
    st.session_state.concepts = ""
    st.session_state.quiz_data = []

    # ==========================================
    # PROMPT 1 — SUMMARY (CLEAR + SIMPLE)
    # ==========================================
    summary_prompt = f"""
Create a clear 5-bullet summary.

Language: {selected_language}
Difficulty: {difficulty_level}

Focus on main ideas.

TEXT:
{text}
"""

    summary_response = client.chat.completions.create(
        model=TEXT_MODEL,
        messages=[{"role": "user", "content": summary_prompt}]
    )

    st.session_state.summary = summary_response.choices[0].message.content


    # ==========================================
    # PROMPT 2 — CONCEPT UNDERSTANDING (IMPORTANT FIX)
    # This solves your "doesn't understand examples" issue
    # ==========================================
    concept_prompt = f"""
Extract key concepts and EXPLAIN examples from the text.

Rules:
- You MUST explain any example in simple words
- Do NOT copy sentences
- Break into short points
- Make it easy for students

Language: {selected_language}
Difficulty: {difficulty_level}

TEXT:
{text}
"""

    concept_response = client.chat.completions.create(
        model=TEXT_MODEL,
        messages=[{"role": "user", "content": concept_prompt}]
    )

    st.session_state.concepts = concept_response.choices[0].message.content


    # ==========================================
    # PROMPT 3 — QUIZ GENERATION (STRICT JSON)
    # ==========================================
    quiz_prompt = f"""
You are an exam question generator.

Create 10 MCQs ONLY.

Rules:
- Must test understanding of concepts AND examples
- No copying sentences
- No summary
- Must be valid JSON only

Language: {selected_language}
Difficulty: {difficulty_level}

FORMAT:
{{
  "questions": [
    {{
      "question": "...",
      "options": ["A","B","C","D"],
      "correct_index": 0
    }}
  ]
}}

TEXT:
{text}
"""

    quiz_response = client.chat.completions.create(
        model=TEXT_MODEL,
        messages=[{"role": "user", "content": quiz_prompt}],
        response_format={"type": "json_object"}
    )

    parsed = json.loads(quiz_response.choices[0].message.content)
    st.session_state.quiz_data = parsed["questions"]

    # RESET QUIZ STATE
    st.session_state.user_answers = {}
    st.session_state.quiz_checked = False

    st.session_state.processing_done = True

    st.rerun()
# ==========================================
# INPUT AREA (TEXT ENTRY)
# ==========================================
st.title("📚 My Study Buddy")

input_mode = st.radio("Input Mode", ["Paste Text", "Upload PDF"])

text_input = ""

# --------------------------
# PASTE TEXT
# --------------------------
if input_mode == "Paste Text":
    text_input = st.text_area("Enter your text here", height=200)

# --------------------------
# PDF INPUT
# --------------------------
else:
    file = st.file_uploader("Upload PDF", type=["pdf"])

    if file:
        reader = pypdf.PdfReader(file)
        text_input = "\n".join([page.extract_text() or "" for page in reader.pages])

# store globally for pipeline
st.session_state.input_text = text_input


# ==========================================
# DISPLAY RESULTS
# ==========================================
if st.session_state.processing_done:

    # --------------------------
    # SUMMARY
    # --------------------------
    if st.session_state.summary:
        st.divider()
        st.header("📝 Summary")
        st.write(st.session_state.summary)

    # --------------------------
    # CONCEPTS (IMPORTANT FIX FOR EXAMPLES)
    # --------------------------
    if st.session_state.concepts:
        st.divider()
        st.header("🧠 Key Concepts (Explained Simply)")
        st.write(st.session_state.concepts)

    # --------------------------
    # QUIZ SECTION
    # --------------------------
    if st.session_state.quiz_data:

        st.divider()
        st.header("🧠 Quiz")

        for i, q in enumerate(st.session_state.quiz_data):

            st.subheader(f"Q{i+1}: {q['question']}")

            options = q["options"]

            saved = st.session_state.user_answers.get(f"q_{i}")
            index = options.index(saved) if saved in options else 0

            chosen = st.radio(
                "Choose answer:",
                options,
                key=f"q_{i}",
                index=index
            )

            st.session_state.user_answers[f"q_{i}"] = chosen

            # show results after grading
            if st.session_state.quiz_checked:
                correct = options[q["correct_index"]]

                if chosen == correct:
                    st.success("✅ Correct")
                else:
                    st.error(f"❌ Correct answer: {correct}")

            st.write("---")

        # --------------------------
        # GRADE BUTTON
        # --------------------------
        if not st.session_state.quiz_checked:

            if st.button("📊 Grade Quiz"):
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
# RUN PIPELINE BUTTON
# ==========================================
if st.button("🚀 Process Text"):

    if not st.session_state.input_text.strip():
        st.warning("No text provided.")
        st.stop()

    # trigger multi-prompt pipeline
    st.session_state.processing_done = False

    st.rerun()
