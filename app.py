import streamlit as st
from groq import Groq
import json
from PIL import Image
import io
import base64
import pypdf

# ==========================================
# APP CONFIG
# ==========================================
st.set_page_config(
    page_title="AI Study System",
    page_icon="📚",
    layout="centered"
)

VISION_MODEL = "meta-llama/llama-4-scout-17b-16e-instruct"
TEXT_MODEL = "llama-3.3-70b-versatile"

# ==========================================
# SIDEBAR
# ==========================================
st.sidebar.title("⚙️ Settings")

if "GROQ_API_KEY" in st.secrets:
    api_key = st.secrets["GROQ_API_KEY"]
else:
    api_key = st.sidebar.text_input("🔑 Groq API Key", type="password")

language = st.sidebar.selectbox(
    "🌐 Language",
    ["English","Malay","Tamil","Spanish","French","German","Chinese","Japanese","Arabic"]
)

difficulty = st.sidebar.selectbox(
    "🎯 Difficulty",
    ["Kindergarten","Year 1","Year 2","Year 3","Year 4","Year 5","Year 6","Secondary (Basic)","Secondary (Advanced)"]
)

if not api_key:
    st.stop()

client = Groq(api_key=api_key)

# ==========================================
# SESSION STATE (CLEAN STRUCTURE)
# ==========================================
defaults = {
    "summary": "",
    "concepts": "",
    "quiz": [],
    "answers": {},
    "scan_text": "",
    "history": []
}

for k, v in defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v
# ==========================================
# PART 2/5 — CORE FUNCTIONS
# ==========================================

# ---------- Language + Difficulty Maps ----------
LANGUAGES = {
    "English": "English",
    "Malay": "Malay",
    "Chinese (Simplified)": "Simplified Chinese",
    "Tamil": "Tamil"
}

DIFFICULTY_LEVELS = {
    "Kindergarten": "very easy, simple words",
    "Primary": "easy, basic understanding",
    "Year 6": "moderate difficulty, exam level",
    "Secondary": "advanced school level",
}

# ---------- JSON Cleaner ----------
def safe_json_loads(raw_text: str):
    """
    Safely parse JSON from model output.
    Handles cases where extra text exists outside JSON.
    """
    try:
        return json.loads(raw_text)
    except:
        try:
            start = raw_text.find("{")
            end = raw_text.rfind("}") + 1
            return json.loads(raw_text[start:end])
        except:
            return None


# ---------- Prompt Builder ----------
def build_prompt(text, task_type, language, difficulty):
    return f"""
You are an educational assistant.

Task: {task_type}
Difficulty: {difficulty}
Output Language: {language}

Input Text:
{text}

Rules:
- Keep output clear and structured
- Avoid unnecessary complexity
- If summarizing, keep key points only
- If generating quiz, include questions + answers clearly
"""


# ---------- Groq API Call ----------
def call_groq(client, prompt):
    """
    Sends request to Groq and returns raw response text.
    """
    response = client.chat.completions.create(
        model="llama3-70b-8192",
        messages=[
            {"role": "system", "content": "You are a helpful education assistant."},
            {"role": "user", "content": prompt}
        ],
        temperature=0.5
    )

    return response.choices[0].message.content
# ==========================================
# PART 3/5 — STREAMLIT UI LAYOUT
# ==========================================

st.set_page_config(page_title="Study Buddy", layout="wide")

st.title("📚 My Study Buddy")

# ---------- SIDEBAR ----------
st.sidebar.header("⚙️ Settings")

task_type = st.sidebar.selectbox(
    "Choose Task Type",
    ["Summary", "Quiz", "Explain", "Flashcards"]
)

language = st.sidebar.selectbox(
    "Output Language",
    list(LANGUAGES.keys())
)

difficulty = st.sidebar.selectbox(
    "Difficulty Level",
    list(DIFFICULTY_LEVELS.keys())
)

input_mode = st.sidebar.radio(
    "Input Mode",
    ["Paste Text", "Upload PDF"]
)

st.sidebar.markdown("---")
st.sidebar.info("Tip: Longer text = better summaries & quizzes")

# ---------- MAIN INPUT AREA ----------
text_input = ""

if input_mode == "Paste Text":
    text_input = st.text_area(
        "Enter your text here",
        height=300,
        placeholder="Paste your notes, chapter, or article here..."
    )

elif input_mode == "Upload PDF":
    uploaded_file = st.file_uploader("Upload PDF", type=["pdf"])

    if uploaded_file is not None:
        import PyPDF2

        pdf_reader = PyPDF2.PdfReader(uploaded_file)
        extracted_text = ""

        for page in pdf_reader.pages:
            extracted_text += page.extract_text() or ""

        text_input = extracted_text

        st.success("PDF loaded successfully!")

# ---------- ACTION BUTTON ----------
generate = st.button("🚀 Generate")
# ==========================================
# PART 4/5 — GENERATION LOGIC + OUTPUT
# ==========================================

if generate and text_input.strip():

    # ---------- Convert selections ----------
    selected_language = LANGUAGES[language]
    selected_difficulty = DIFFICULTY_LEVELS[difficulty]

    # ---------- Build prompt ----------
    prompt = build_prompt(
        text=text_input,
        task_type=task_type,
        language=selected_language,
        difficulty=selected_difficulty
    )

    # ---------- Initialize Groq client ----------
    client = Groq(api_key=st.secrets["GROQ_API_KEY"])

    # ---------- Call API ----------
    with st.spinner("Generating response..."):
        raw_output = call_groq(client, prompt)

    # ---------- Display output ----------
    st.subheader("📌 Result")

    # ---------- Task-specific formatting ----------
    if task_type == "Summary":
        st.markdown("### 🧾 Summary")
        st.write(raw_output)

    elif task_type == "Explain":
        st.markdown("### 📖 Explanation")
        st.write(raw_output)

    elif task_type == "Flashcards":
        st.markdown("### 🧠 Flashcards")
        st.write(raw_output)

    elif task_type == "Quiz":
        st.markdown("### ❓ Quiz")

        parsed = safe_json_loads(raw_output)

        if parsed and isinstance(parsed, dict):
            questions = parsed.get("questions", [])

            for i, q in enumerate(questions, 1):
                st.markdown(f"**Q{i}: {q.get('question')}**")
                st.markdown(f"Answer: {q.get('answer')}")
                st.markdown("---")
        else:
            # fallback if model didn't return JSON
            st.warning("Model did not return structured quiz format. Showing raw output:")
            st.write(raw_output)

else:
    if generate:
        st.error("Please enter or upload some text first.")
# ==========================================
# PART 5/5 — FINAL POLISH + EXPORT + FIXES
# ==========================================

# ---------- Improve PDF text cleanup ----------
def clean_text(text):
    """
    Removes excessive whitespace and fixes broken extraction issues.
    """
    if not text:
        return ""
    return " ".join(text.split())


# ---------- Better JSON enforcement prompt (upgrade for quizzes) ----------
def build_quiz_prompt(text, language, difficulty):
    return f"""
You are a strict quiz generator.

Create a multiple-choice quiz ONLY in valid JSON format.

Rules:
- Output MUST be valid JSON only (no explanations, no markdown)
- Structure must be:
{{
  "questions": [
    {{
      "question": "...",
      "options": ["A", "B", "C", "D"],
      "answer": "..."
    }}
  ]
}}

Task:
Generate a quiz based on the text below.

Difficulty: {difficulty}
Language: {language}

Text:
{text}
"""


# ---------- Override prompt for quiz ----------
if generate and text_input.strip():

    selected_language = LANGUAGES[language]
    selected_difficulty = DIFFICULTY_LEVELS[difficulty]

    client = Groq(api_key=st.secrets["GROQ_API_KEY"])

    with st.spinner("Generating response..."):

        # Use strict quiz prompt if needed
        if task_type == "Quiz":
            prompt = build_quiz_prompt(
                text=text_input,
                language=selected_language,
                difficulty=selected_difficulty
            )
        else:
            prompt = build_prompt(
                text=text_input,
                task_type=task_type,
                language=selected_language,
                difficulty=selected_difficulty
            )

        raw_output = call_groq(client, prompt)

    st.subheader("📌 Result")

    st.write(raw_output)


    # ---------- Download feature ----------
    st.markdown("---")
    st.subheader("⬇️ Download Result")

    file_name = f"{task_type}_output.txt"

    st.download_button(
        label="Download as TXT",
        data=raw_output,
        file_name=file_name,
        mime="text/plain"
    )


# ---------- Extra UX improvement ----------
st.markdown("---")
st.caption("Study Buddy • AI-powered learning assistant")

