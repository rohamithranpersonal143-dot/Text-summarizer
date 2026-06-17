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
# LANGUAGE SELECTOR
# ==========================================
selected_language = st.sidebar.selectbox(
    "🌐 Choose Output Language:",
    [
        "English",
        "Spanish",
        "French",
        "German",
        "Chinese",
        "Malay",
        "Japanese",
        "Arabic"
    ]
)

if not api_key:
    st.info(
        "💡 Please add your Groq API Key in the sidebar or Streamlit Secrets to begin."
    )
    st.stop()

# ==========================================
# GROQ CLIENT
# ==========================================
client = Groq(api_key=api_key)

VISION_MODEL = "meta-llama/llama-4-scout-17b-16e-instruct"
TEXT_MODEL = "llama-3.3-70b-versatile"

# ==========================================
# SESSION STATE
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
# DISPLAY SUMMARY + QUIZ
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

            st.subheader(
                f"Q{q_idx + 1}: {q_item['question']}"
            )

            saved_answer = st.session_state.user_answers.get(
                f"q_{q_idx}"
            )

            if (
                saved_answer
                and saved_answer in q_item["options"]
            ):
                radio_index = q_item["options"].index(
                    saved_answer
                )
            else:
                radio_index = 0

            chosen_option = st.radio(
                "Select answer:",
                q_item["options"],
                key=f"q_{q_idx}",
                index=radio_index
            )

            st.session_state.user_answers[
                f"q_{q_idx}"
            ] = chosen_option

            if st.session_state.quiz_checked:

                correct_answer = q_item["options"][
                    q_item["correct_index"]
                ]

                if chosen_option == correct_answer:
                    st.success("✅ Correct!")
                else:
                    st.error(
                        f"❌ Incorrect. Correct answer: {correct_answer}"
                    )

            st.write("---")

        if not st.session_state.quiz_checked:

            if st.button(
                "📊 Grade My Quiz",
                use_container_width=True
            ):
                st.session_state.quiz_checked = True
                st.rerun()

        else:

            score = 0

            for i, q in enumerate(
                st.session_state.quiz_data
            ):

                selected = st.session_state.user_answers.get(
                    f"q_{i}"
                )

                correct = q["options"][
                    q["correct_index"]
                ]

                if selected == correct:
                    score += 1

            st.success(
                f"🎯 Score: {score}/{len(st.session_state.quiz_data)}"
            )

            if st.button(
                "🔄 Reset Quiz",
                use_container_width=True
            ):
                st.session_state.user_answers = {}
                st.session_state.quiz_checked = False
                st.rerun()


# ==========================================
# NAVIGATION
# ==========================================
app_mode = st.selectbox(
    "🗺️ Choose Feature:",
    [
        "📷 1. Text Scanner (Google Lens Mode)",
        "📚 2. Text/PDF Summarizer & Quizzer"
    ]
)
# ==========================================
# FEATURE 1: CAMERA TEXT SCANNER
# ==========================================
if app_mode == "📷 1. Text Scanner (Google Lens Mode)":

    st.title("📷 Mobile Text Scanner")
    st.write(
        "Snap a photo of a book, paper, or screen to instantly extract and copy the text."
    )

    if st.session_state.camera_on:

        if st.button(
            "🔴 Turn Camera OFF",
            use_container_width=True
        ):
            st.session_state.camera_on = False
            st.rerun()

    else:

        if st.button(
            "📷 Turn Camera ON",
            use_container_width=True
        ):
            st.session_state.camera_on = True
            st.rerun()

    # =============================
    # CAMERA INPUT
    # =============================
    if st.session_state.camera_on:

        img_file = st.camera_input(
            "Position your text clearly in the frame:"
        )

        if img_file is not None:

            with st.spinner(
                "🔍 AI is reading the text..."
            ):

                try:

                    img = Image.open(img_file)

                    img_byte_arr = io.BytesIO()
                    img.save(
                        img_byte_arr,
                        format="JPEG"
                    )

                    base64_image = base64.b64encode(
                        img_byte_arr.getvalue()
                    ).decode("utf-8")

                    prompt = """
Extract ALL visible text from this image.

Requirements:
- Preserve formatting where possible
- Do NOT summarize
- Do NOT explain
- Return only the extracted text
"""

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
                                            "url": f"data:image/jpeg;base64,{base64_image}"
                                        }
                                    }
                                ]
                            }
                        ],
                        temperature=0
                    )

                    st.session_state.scanned_text = (
                        response.choices[0].message.content
                    )

                except Exception as e:

                    st.error(
                        f"Failed to scan text: {e}"
                    )

    # =============================
    # DISPLAY OCR RESULT
    # =============================
    if st.session_state.scanned_text:

        st.success("✨ Text Extracted!")

        st.code(
            st.session_state.scanned_text,
            language="text"
        )

        if st.button(
            "🧠 Send to Summarizer & Quizzer",
            use_container_width=True
        ):

            st.session_state.summary = ""
            st.session_state.quiz_data = []

            with st.spinner(
                f"Building study materials in {selected_language}..."
            ):

                try:

                    master_prompt = f"""
Analyze the source text below.

OUTPUT 1:
Create EXACTLY 5 bullet points.

Language:
{selected_language}

OUTPUT 2:
Generate EXACTLY 10 multiple choice questions.

Return OUTPUT 2 as a STRICT JSON ARRAY.

Example:

[
  {{
    "question": "Question",
    "options": [
      "Option A",
      "Option B",
      "Option C",
      "Option D"
    ],
    "correct_index": 0
  }}
]

Separate OUTPUT 1 and OUTPUT 2 using:

===SPLIT_HERE===

SOURCE TEXT:
{st.session_state.scanned_text}
"""

                    response = client.chat.completions.create(
                        model=TEXT_MODEL,
                        messages=[
                            {
                                "role": "user",
                                "content": master_prompt
                            }
                        ]
                    )

                    raw_output = (
                        response.choices[0]
                        .message.content
                    )

                    if "===SPLIT_HERE===" in raw_output:

                        summary_part, quiz_part = (
                            raw_output.split(
                                "===SPLIT_HERE===",
                                1
                            )
                        )

                        st.session_state.summary = (
                            summary_part.strip()
                        )

                        start_idx = quiz_part.find("[")
                        end_idx = (
                            quiz_part.rfind("]")
                            + 1
                        )

                        if (
                            start_idx != -1
                            and end_idx > 0
                        ):

                            clean_json = (
                                quiz_part[
                                    start_idx:end_idx
                                ]
                            )

                            st.session_state.quiz_data = (
                                json.loads(
                                    clean_json
                                )
                            )

                        else:

                            quiz_part = (
                                quiz_part
                                .replace(
                                    "```json",
                                    ""
                                )
                                .replace(
                                    "```",
                                    ""
                                )
                                .strip()
                            )

                            st.session_state.quiz_data = (
                                json.loads(
                                    quiz_part
                                )
                            )

                    else:

                        st.session_state.summary = (
                            raw_output
                        )

                        st.warning(
                            "Quiz section could not be parsed."
                        )

                    st.session_state.user_answers = {}
                    st.session_state.quiz_checked = False

                    st.toast(
                        "✅ Study kit generated!"
                    )

                    st.rerun()

                except Exception as e:

                    st.error(
                        f"Processing failed: {e}"
                    )

        display_summary_and_quiz()
# ==========================================
# FEATURE 2: SUMMARIZER & QUIZZER
# ==========================================
else:

    st.title("📚 My Study Buddy")
    st.write(
        "Upload a file or paste text to generate summaries and quizzes."
    )

    input_type = st.radio(
        "Choose Input Type:",
        [
            "📋 Paste Text",
            "📄 Upload PDF"
        ]
    )

    lecture_text = ""

    # =============================
    # PASTE TEXT
    # =============================
    if input_type == "📋 Paste Text":

        lecture_text = st.text_area(
            "Paste material here:",
            height=200
        )

    # =============================
    # PDF UPLOAD
    # =============================
    else:

        uploaded_file = st.file_uploader(
            "Upload PDF",
            type=["pdf"]
        )

        if uploaded_file is not None:

            try:

                import pypdf

                pdf_reader = pypdf.PdfReader(
                    uploaded_file
                )

                pages = []

                for page in pdf_reader.pages:

                    text = page.extract_text()

                    if text:
                        pages.append(text)

                lecture_text = "\n".join(
                    pages
                )

                st.success(
                    f"Loaded {len(pdf_reader.pages)} pages."
                )

            except Exception as e:

                st.error(
                    f"Failed to read PDF: {e}"
                )

    # =============================
    # PROCESS BUTTON
    # =============================
    if st.button(
        "🚀 Process Material",
        use_container_width=True
    ):

        if not lecture_text.strip():

            st.warning(
                "Please paste some text or upload a PDF."
            )

        else:

            with st.spinner(
                f"🧠 Building your study kit in {selected_language}..."
            ):

                try:

                    # =============================
                    # SUMMARY
                    # =============================
                    summary_prompt = f"""
Create EXACTLY 5 important bullet points.

Language:
{selected_language}

TEXT:
{lecture_text}
"""

                    summary_response = (
                        client.chat.completions.create(
                            model=TEXT_MODEL,
                            messages=[
                                {
                                    "role": "user",
                                    "content": summary_prompt
                                }
                            ]
                        )
                    )

                    st.session_state.summary = (
                        summary_response
                        .choices[0]
                        .message.content
                    )

                    # =============================
                    # QUIZ
                    # =============================
                    quiz_prompt = f"""
Return ONLY valid JSON.

Format:

{{
  "questions": [
    {{
      "question": "Question text",
      "options": [
        "Option A",
        "Option B",
        "Option C",
        "Option D"
      ],
      "correct_index": 0
    }}
  ]
}}

Requirements:
- Exactly 10 questions
- Exactly 4 options per question
- correct_index must be between 0 and 3
- Language: {selected_language}

TEXT:
{lecture_text}
"""

                    quiz_response = (
                        client.chat.completions.create(
                            model=TEXT_MODEL,
                            messages=[
                                {
                                    "role": "user",
                                    "content": quiz_prompt
                                }
                            ],
                            response_format={
                                "type": "json_object"
                            }
                        )
                    )

                    raw_json = (
                        quiz_response
                        .choices[0]
                        .message.content
                        .strip()
                    )

                    raw_json = (
                        raw_json
                        .replace("```json", "")
                        .replace("```", "")
                        .strip()
                    )

                    try:

                        parsed_data = json.loads(
                            raw_json
                        )

                    except json.JSONDecodeError:

                        st.error(
                            "AI returned invalid JSON."
                        )

                        st.code(
                            raw_json,
                            language="json"
                        )

                        st.stop()

                    if (
                        isinstance(parsed_data, dict)
                        and "questions" in parsed_data
                    ):

                        st.session_state.quiz_data = (
                            parsed_data["questions"]
                        )

                    elif (
                        isinstance(parsed_data, dict)
                        and len(parsed_data.keys()) == 1
                    ):

                        st.session_state.quiz_data = (
                            list(
                                parsed_data.values()
                            )[0]
                        )

                    else:

                        st.session_state.quiz_data = (
                            parsed_data
                        )

                    st.session_state.user_answers = {}
                    st.session_state.quiz_checked = False

                    st.toast(
                        "✅ Study kit generated!"
                    )

                    st.rerun()

                except Exception as e:

                    st.error(
                        f"Error processing: {e}"
                    )

    # =============================
    # DISPLAY RESULTS
    # =============================
    display_summary_and_quiz()