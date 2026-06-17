import streamlit as st
from groq import Groq
import json
from PIL import Image
import io
import base64
import pypdf

st.set_page_config(page_title="My Study Buddy", page_icon="📱", layout="centered")

VISION_MODEL = "meta-llama/llama-4-scout-17b-16e-instruct"
TEXT_MODEL = "llama-3.3-70b-versatile"

# --------------------------
# SIDEBAR
# --------------------------
st.sidebar.title("⚙️ Settings")

api_key = st.secrets.get("GROQ_API_KEY") or st.sidebar.text_input("🔑 Groq API Key", type="password")

selected_language = st.sidebar.selectbox(
    "🌐 Language",
    ["English","Malay","Tamil","Spanish","French","German","Chinese","Japanese","Arabic"]
)

difficulty_level = st.sidebar.selectbox(
    "🎯 Difficulty",
    ["Kindergarten","Year 1","Year 2","Year 3","Year 4","Year 5","Year 6","Secondary (Basic)","Secondary (Advanced)"]
)

if not api_key:
    st.info("Enter API key")
    st.stop()

client = Groq(api_key=api_key)

# --------------------------
# STATE (SEPARATED SYSTEMS)
# --------------------------

# Scanner system
st.session_state.setdefault("scan_text", "")
st.session_state.setdefault("camera_on", False)

# Study system
st.session_state.setdefault("study_summary", "")
st.session_state.setdefault("study_quiz", [])
st.session_state.setdefault("study_answers", {})
st.session_state.setdefault("study_checked", False)
st.session_state.setdefault("study_text", "")
st.title("📷 Text Scanner")

if st.session_state.camera_on:
    if st.button("🔴 Turn Camera OFF"):
        st.session_state.camera_on = False
        st.rerun()
else:
    if st.button("📷 Turn Camera ON"):
        st.session_state.camera_on = True
        st.rerun()

if st.session_state.camera_on:
    img_file = st.camera_input("Capture")

    if img_file:
        img = Image.open(img_file)

        buf = io.BytesIO()
        img.save(buf, format="JPEG")
        b64 = base64.b64encode(buf.getvalue()).decode()

        response = client.chat.completions.create(
            model=VISION_MODEL,
            messages=[{
                "role": "user",
                "content": [
                    {"type": "text", "text": "Extract text exactly"},
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64}"}}
                ]
            }]
        )

        st.session_state.scan_text = response.choices[0].message.content
      if st.session_state.scan_text:
    st.success("Extracted Text")
    st.code(st.session_state.scan_text)

    if st.button("🧠 Generate Quiz from Scan"):
        prompt = f"""
Language: {selected_language}
Difficulty: {difficulty_level}

Create:
1) 5 bullet summary
2) 10 MCQs JSON

Format:
===SPLIT===
SUMMARY
===SPLIT===
[{{"question":"","options":["A","B","C","D"],"correct_index":0}}]

TEXT:
{st.session_state.scan_text}
"""

        res = client.chat.completions.create(
            model=TEXT_MODEL,
            messages=[{"role": "user", "content": prompt}]
        )

        raw = res.choices[0].message.content

        if "===SPLIT===" in raw:
            parts = raw.split("===SPLIT===")

            st.session_state.study_summary = parts[1].strip()

            start = raw.find("[")
            end = raw.rfind("]") + 1

            st.session_state.study_quiz = json.loads(raw[start:end])
            st.session_state.study_answers = {}
            st.session_state.study_checked = False

            st.rerun()
          def show_quiz():

    if st.session_state.study_summary:
        st.header("📝 Summary")
        st.write(st.session_state.study_summary)

    if st.session_state.study_quiz:

        st.header("🧠 Quiz")

        for i, q in enumerate(st.session_state.study_quiz):

            st.subheader(q["question"])

            saved = st.session_state.study_answers.get(f"q_{i}")

            index = q["options"].index(saved) if saved in q["options"] else 0

            chosen = st.radio(
                "Answer",
                q["options"],
                key=f"quiz_q_{i}",   # ✅ FIXED UNIQUE PREFIX
                index=index
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

            if st.button("🔄 Reset Quiz"):
                st.session_state.study_answers = {}
                st.session_state.study_checked = False
                st.rerun()
              st.title("📚 Study Buddy")

mode = st.radio("Input Type", ["Paste Text", "Upload PDF"])

text = ""

if mode == "Paste Text":
    text = st.text_area("Enter text", height=200)

else:
    file = st.file_uploader("Upload PDF", type=["pdf"])
    if file:
        reader = pypdf.PdfReader(file)
        text = "\n".join([p.extract_text() or "" for p in reader.pages])

if st.button("Process Text"):
    if not text.strip():
        st.warning("No text")
        st.stop()

    summary_prompt = f"Summarize in 5 bullets. Language:{selected_language}\n{text}"
    quiz_prompt = f"""
Return JSON MCQs only.
Difficulty:{difficulty_level}
Text:{text}
"""

    summary = client.chat.completions.create(
        model=TEXT_MODEL,
        messages=[{"role": "user", "content": summary_prompt}]
    ).choices[0].message.content

    quiz = client.chat.completions.create(
        model=TEXT_MODEL,
        messages=[{"role": "user", "content": quiz_prompt}],
        response_format={"type": "json_object"}
    )

    st.session_state.study_summary = summary
    parsed = json.loads(quiz.choices[0].message.content)
    st.session_state.study_quiz = parsed.get("questions", parsed)

    st.session_state.study_answers = {}
    st.session_state.study_checked = False

    st.rerun()

# FINAL DISPLAY (ONLY ONCE — IMPORTANT)
show_quiz()
          
