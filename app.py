import streamlit as st
from groq import Groq
import json
from PIL import Image
import io, base64
import pypdf

st.set_page_config("My Study Buddy", "📱", layout="centered")

VISION_MODEL = "meta-llama/llama-4-scout-17b-16e-instruct"
TEXT_MODEL = "llama-3.3-70b-versatile"

# API
api_key = st.secrets.get("GROQ_API_KEY") or st.sidebar.text_input("API Key", type="password")
if not api_key:
    st.stop()

client = Groq(api_key=api_key)
def render_quiz():

    if st.session_state.study_summary:
        st.header("📝 Summary")
        st.write(st.session_state.study_summary)

    if st.session_state.study_quiz:

        st.header("🧠 Quiz")

        for i, q in enumerate(st.session_state.study_quiz):

            st.subheader(q["question"])

            chosen = st.radio(
                "Answer",
                q["options"],
                key=f"study_q_{i}"   # 🔥 FIXED UNIQUE KEY
            )

            st.session_state.study_answers[f"q_{i}"] = chosen

            if st.session_state.study_checked:
                correct = q["options"][q["correct_index"]]
                if chosen == correct:
                    st.success("Correct")
                else:
                    st.error(f"Correct: {correct}")

        if not st.session_state.study_checked:
            if st.button("📊 Grade Quiz"):
                st.session_state.study_checked = True
                st.rerun()
        else:
            score = sum(
                st.session_state.study_answers.get(f"q_{i}") ==
                q["options"][q["correct_index"]]
                for i, q in enumerate(st.session_state.study_quiz)
            )
            st.success(f"Score: {score}/{len(st.session_state.study_quiz)}")

            if st.button("Reset"):
                st.session_state.study_answers = {}
                st.session_state.study_checked = False
                st.rerun()
                st.title("📷 Scanner")

if st.button("Toggle Camera"):
    st.session_state.camera_on = not st.session_state.get("camera_on", False)
    st.rerun()

if st.session_state.get("camera_on"):

    img = st.camera_input("Capture")

    if img:
        image = Image.open(img)

        buf = io.BytesIO()
        image.save(buf, "JPEG")
        b64 = base64.b64encode(buf.getvalue()).decode()

        res = client.chat.completions.create(
            model=VISION_MODEL,
            messages=[{
                "role": "user",
                "content": [
                    {"type": "text", "text": "Extract text only"},
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64}"}}
                ]
            }]
        )

        st.session_state.scan_text = res.choices[0].message.content
        if st.session_state.scan_text:

    st.code(st.session_state.scan_text)

    if st.button("Generate Quiz from Scan"):

        prompt = f"""
Text:
{st.session_state.scan_text}

Return:
5 bullet summary + JSON MCQ list
"""

        res = client.chat.completions.create(
            model=TEXT_MODEL,
            messages=[{"role": "user", "content": prompt}]
        )

        raw = res.choices[0].message.content

        st.session_state.study_summary = raw  # simplified safe version

        start = raw.find("[")
        end = raw.rfind("]") + 1

        if start != -1 and end != -1:
            st.session_state.study_quiz = json.loads(raw[start:end])

        st.session_state.study_answers = {}
        st.session_state.study_checked = False

        st.rerun()
        st.title("📚 Study Buddy")

mode = st.radio("Input", ["Text", "PDF"])

text = ""

if mode == "Text":
    text = st.text_area("Enter text")

else:
    file = st.file_uploader("PDF")
    if file:
        reader = pypdf.PdfReader(file)
        text = "\n".join(p.extract_text() or "" for p in reader.pages)

if st.button("Process Text"):

    summary = client.chat.completions.create(
        model=TEXT_MODEL,
        messages=[{"role": "user", "content": f"Summarize:\n{text}"}]
    ).choices[0].message.content

    quiz = client.chat.completions.create(
        model=TEXT_MODEL,
        messages=[{"role": "user", "content": f"Make MCQ JSON:\n{text}"}],
        response_format={"type": "json_object"}
    )

    st.session_state.study_summary = summary
    st.session_state.study_quiz = json.loads(quiz.choices[0].message.content).get("questions", [])

    st.session_state.study_answers = {}
    st.session_state.study_checked = False

    st.rerun()

# 🔥 ONLY ONCE (THIS IS THE KEY FIX)
render_quiz()

# ---------------- STATES (SEPARATED SYSTEMS) ----------------
st.session_state.setdefault("scan_text", "")
st.session_state.setdefault("scan_summary", "")
st.session_state.setdefault("scan_quiz", [])

st.session_state.setdefault("study_summary", "")
st.session_state.setdefault("study_quiz", [])
st.session_state.setdefault("study_answers", {})
st.session_state.setdefault("study_checked", False)
