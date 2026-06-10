import streamlit as st
import google.generativeai as genai
from PIL import Image

# Mobile layout setup
st.set_page_config(page_title="Pocket Lens", page_icon="📷", layout="centered")

st.title("📷 Mobile Text Scanner")
st.write("Turn on your camera, snap a photo of any text, and let AI extract it instantly.")

# 1. API Key Authentication (Uses the same secrets setup as before)
if "GEMINI_API_KEY" in st.secrets:
    api_key = st.secrets["GEMINI_API_KEY"]
else:
    api_key = st.sidebar.text_input("🔑 Enter Gemini API Key:", type="password")

if not api_key:
    st.info("💡 Please add your Gemini API Key in the sidebar or Streamlit Secrets to begin.")
    st.stop()

genai.configure(api_key=api_key)
model = genai.GenerativeModel('gemini-2.5-flash')

# 2. Camera Toggle Switch
if "camera_on" not in st.session_state:
    st.session_state.camera_on = False

# Stateful button that switches between turning camera ON or OFF
if st.session_state.camera_on:
    if st.button("🔴 Turn Camera OFF", use_container_width=True):
        st.session_state.camera_on = False
        st.rerun()
else:
    if st.button("📷 Turn Camera ON", use_container_width=True):
        st.session_state.camera_on = True
        st.rerun()

# 3. Camera Engine & Visual Processing
if st.session_state.camera_on:
    # Opens your phone's native front/back camera feed
    img_file = st.camera_input("Position your text clearly inside the frame:")
    
    if img_file is not None:
        with st.spinner("🔍 Reading text from image..."):
            try:
                # Convert the raw browser upload into a format Python can read
                img = Image.open(img_file)
                
                # Visual Analysis Prompt instruction to Gemini
                prompt = (
                    "Look at this image. Extract every piece of text visible in it. "
                    "Format it cleanly exactly as it appears. Do not summarize or add conversational text, "
                    "just provide the extracted text so the user can copy it."
                )
                
                # Pass both the text instructions AND the raw image to the AI model
                response = model.generate_content([prompt, img])
                
                # 4. Display Extracted Text UI Box
                st.success("✨ Text Extracted Successfully!")
                
                # Code blocks display an automatic 'Copy' button on mobile view browsers
                st.code(response.text, language="text")
                
                # Native web copy button tool interface
                st.copy_to_clipboard(response.text, before_copy_label="📋 Copy Text to Clipboard", after_copy_label="✅ Text Copied!")
                
            except Exception as e:
                st.error(f"Failed to extract text. Error: {e}")
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
