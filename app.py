import streamlit as st
from groq import Groq
import json
from PIL import Image
import io
import base64

# ==========================================
# PAGE SETUP
# ==========================================
st.set_page_config(
    page_title="My Study Buddy",
    page_icon="📱",
    layout="centered"
)

# ==========================================
# API KEY
# ==========================================
if "GROQ_API_KEY" in st.secrets:
    api_key = st.secrets["GROQ_API_KEY"]
else:
    api_key = st.sidebar.text_input(
        "🔑 Enter Groq API Key:",
        type="password"
    )

# ==========================================
# SIDEBAR CONTROLS
# ==========================================
selected_language = st.sidebar.selectbox(
    "🌐 Choose Output Language:",
    ["English", "Spanish", "French", "German", "Chinese", "Malay", "Japanese", "Arabic"]
)

difficulty_level = st.sidebar.selectbox(
    "🎯 Choose Difficulty Level:",
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

if not api_key:
    st.info("Add your Groq API key to continue.")
    st.stop()

client = Groq(api_key=api_key)

VISION_MODEL = "meta-llama/llama-4-scout-17b-16e-instruct"
TEXT_MODEL = "llama-3.3-70b-versatile"
# ==========================================
# SESSION STATE
# ==========================================
for key in ["summary", "quiz_data", "user_answers", "quiz_checked", "scanned_text", "camera_on"]:
    if key not in st.session_state:
        if key == "quiz_data":
            st.session_state[key] = []
        elif key == "user_answers":
            st.session_state[key] = {}
        else:
            st.session_state[key] = "" if key != "quiz_checked" else False


# ==========================================
# DISPLAY FUNCTION
# ==========================================
def display_summary_and_quiz():

    if st.session_state.summary:
        st.divider()
        st.header("📝 Smart Summary")
        st.write(st.session_state.summary)

    if st.session_state.quiz_data:

        st.divider()
        st.header("🧠 Practice Quiz")

        for q_idx, q_item in enumerate(st.session_state.quiz_data):

            st.subheader(f"Q{q_idx+1}: {q_item['question']}")

            saved = st.session_state.user_answers.get(f"q_{q_idx}")
            options = q_item["options"]

            index = options.index(saved) if saved in options else 0

            chosen = st.radio(
                "Select answer:",
                options,
                key=f"q_{q_idx}",
                index=index
            )

            st.session_state.user_answers[f"q_{q_idx}"] = chosen

            if st.session_state.quiz_checked:
                correct = options[q_item["correct_index"]]
                if chosen == correct:
                    st.success("✅ Correct")
                else:
                    st.error(f"❌ Correct answer: {correct}")

            st.write("---")

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
# NAVIGATION
# ==========================================
app_mode = st.selectbox(
    "🗺️ Choose Feature:",
    [
        "📷 Text Scanner (Google Lens Mode)",
        "📚 Summarizer & Quizzer"
    ]
)

# ==========================================
# FEATURE 1
# ==========================================
if app_mode == "📷 Text Scanner (Google Lens Mode)":

    st.title("📷 Mobile Text Scanner")

    if st.session_state.camera_on:
        if st.button("🔴 Turn Camera OFF"):
            st.session_state.camera_on = False
            st.rerun()
    else:
        if st.button("📷 Turn Camera ON"):
            st.session_state.camera_on = True
            st.rerun()

    if st.session_state.camera_on:

        img_file = st.camera_input("Capture text")

        if img_file:

            with st.spinner("Reading text..."):

                img = Image.open(img_file)
                buf = io.BytesIO()
                img.save(buf, format="JPEG")

                b64 = base64.b64encode(buf.getvalue()).decode()

                prompt = "Extract all text exactly. No explanation."

                response = client.chat.completions.create(
                    model=VISION_MODEL,
                    messages=[{
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64}"}}
                        ]
                    }],
                    temperature=0
                )

                st.session_state.scanned_text = response.choices[0].message.content
if st.session_state.scanned_text:

        st.success("Text extracted")
        st.code(st.session_state.scanned_text)

        if st.button("Send to Quiz Generator"):

            st.session_state.summary = ""
            st.session_state.quiz_data = []

            master_prompt = f"""
Analyze the text.

Language: {selected_language}
Difficulty: {difficulty_level}

Rules:
- Adjust vocabulary and reasoning level to difficulty
- Kindergarten: very simple facts
- Year 1–3: basic comprehension
- Year 4–6: inference questions
- Secondary: analytical reasoning

OUTPUT 1: 5 bullet summary

OUTPUT 2: 10 MCQs in JSON:
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

        display_summary_and_quiz()
else:

    st.title("📚 My Study Buddy")

    input_type = st.radio("Input Type", ["Paste Text", "Upload PDF"])

    text = ""

    if input_type == "Paste Text":
        text = st.text_area("Paste here", height=200)

    else:
        file = st.file_uploader("Upload PDF", type=["pdf"])

        if file:
            import pypdf
            reader = pypdf.PdfReader(file)
            text = "\n".join([p.extract_text() or "" for p in reader.pages])

    if st.button("Process"):

        if not text.strip():
            st.warning("No text")
            st.stop()

        summary_prompt = f"""
Create 5 bullet points.

Language: {selected_language}
Difficulty: {difficulty_level}

TEXT:
{text}
"""

        quiz_prompt = f"""
Return JSON only.

Language: {selected_language}
Difficulty: {difficulty_level}

Generate 10 MCQs adapted to difficulty.

TEXT:
{text}
"""

        summary = client.chat.completions.create(
            model=TEXT_MODEL,
            messages=[{"role": "user", "content": summary_prompt}]
        )

        quiz = client.chat.completions.create(
            model=TEXT_MODEL,
            messages=[{"role": "user", "content": quiz_prompt}],
            response_format={"type": "json_object"}
        )

        st.session_state.summary = summary.choices[0].message.content
        parsed = json.loads(quiz.choices[0].message.content)

        st.session_state.quiz_data = parsed.get("questions", parsed)

        st.session_state.user_answers = {}
        st.session_state.quiz_checked = False

        st.rerun()

    display_summary_and_quiz()
