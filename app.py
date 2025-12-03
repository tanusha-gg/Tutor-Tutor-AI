import streamlit as st
import google.generativeai as genai
import os
import time
from dotenv import load_dotenv
from google.api_core.exceptions import ResourceExhausted

# Import your existing modules
import data_manager
import goal_setting
import feedback_training

# 1. SETUP & CONFIGURATION
load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    st.error("GEMINI_API_KEY not found. Please check your .env file.")
    st.stop()

genai.configure(api_key=api_key)

st.set_page_config(
    page_title="Tutor Tutor AI",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- RETRY LOGIC HELPER ---
def safe_api_call(func, *args, **kwargs):
    """
    Wraps API calls with a retry mechanism for 429 errors.
    """
    retries = 3
    for attempt in range(retries):
        try:
            return func(*args, **kwargs)
        except ResourceExhausted:
            wait_time = 4 * (attempt + 1)  # Wait 4s, 8s, 12s
            st.toast(f"⏳ Rate limit hit. Retrying in {wait_time} seconds...", icon="⚠️")
            time.sleep(wait_time)
        except Exception as e:
            st.error(f"An unexpected error occurred: {e}")
            raise e
    st.error("❌ The AI is currently overloaded. Please wait a minute and try again.")
    return None

# --- INITIALIZE SESSION STATE ---
if "goal_progress" not in st.session_state:
    st.session_state.goal_progress = {} 

if "sim_progress" not in st.session_state:
    st.session_state.sim_progress = set()

# --- HELPER FUNCTIONS FOR PROTOTYPE LOGIC ---
def run_goal_setting_mode():
    st.subheader("🎯 Goal Setting Evaluation")
    st.markdown("Practice balancing conflicting requests from parents and students.")

    data = data_manager.load_data()
    
    if data:
        scenarios = data['goal_setting_scenarios']
        scenario_options = {f"Case {s['id']}": s for s in scenarios}
        selected_option = st.selectbox("Select a Scenario:", list(scenario_options.keys()))
        
        current_scenario = scenario_options[selected_option]
        scenario_id = current_scenario['id']

        if scenario_id in st.session_state.goal_progress:
            st.success("✅ You have completed this case.")

        col1, col2 = st.columns(2)
        with col1:
            st.info(f"**Parent says:**\n\n\"{current_scenario['parent']}\"")
        with col2:
            st.warning(f"**Student says:**\n\n\"{current_scenario['student']}\"")

        tutor_response = st.text_area("How would you respond?", height=150, key=f"text_{scenario_id}")

        if st.button("Evaluate Response", key=f"btn_{scenario_id}"):
            if not tutor_response:
                st.error("Please enter a response first.")
            else:
                with st.spinner("AI is grading your response..."):
                    # WRAPPED CALL: goal_setting.evaluate_tutor_response
                    feedback = safe_api_call(goal_setting.evaluate_tutor_response, tutor_response, current_scenario)
                
                if feedback:
                    st.session_state.goal_progress[scenario_id] = feedback
                    st.success("Evaluation Complete! Progress Saved.")
                    st.markdown(f"### Feedback:\n{feedback}")

def run_simulation_mode():
    st.subheader("🗣️ Judgment Call Simulation")
    st.markdown("Chat with a simulated student to practice empathy and intervention.")

    data = data_manager.load_data()
    if data:
        personas = data['judgment_personas']
        persona_options = {p['name']: p for p in personas}
        selected_persona_name = st.selectbox("Select Student Persona:", list(persona_options.keys()))
        selected_persona = persona_options[selected_persona_name]

        # Reset chat if persona changes
        if "messages" not in st.session_state or st.session_state.get("current_persona") != selected_persona_name:
            st.session_state.messages = []
            st.session_state.current_persona = selected_persona_name
            st.session_state.chat_session = None
            if "context_blurb" in st.session_state:
                del st.session_state.context_blurb
        
        # Generate Context Blurb
        model_2 = genai.GenerativeModel(os.getenv("GEMINI_MODEL_2"))
        if "context_blurb" not in st.session_state:
            with st.spinner("Setting the scene..."):
                context_prompt = f"""
                Based on this student persona: "{selected_persona['description']}"
                Please write a 2-sentence context introduction for the tutor. 
                Include the student's approximate age/grade and the specific subject.
                """
                # WRAPPED CALL: model.generate_content
                context_response = safe_api_call(model_2.generate_content, context_prompt)
                if context_response:
                    st.session_state.context_blurb = context_response.text

        if "context_blurb" in st.session_state:
            st.info(f"**Simulation Context:** {st.session_state.context_blurb}")

        # Initialize Chat Session
        if st.session_state.chat_session is None:
            history = [
                {"role": "user", "parts": [f"System Instruction: Roleplay this student strictly.\n\n{selected_persona['description']}"]},
                {"role": "model", "parts": ["Understood. I am in character."]}
            ]
            st.session_state.chat_session = model_2.start_chat(history=history)
            try:
                # WRAPPED CALL: chat.send_message
                initial_response = safe_api_call(st.session_state.chat_session.send_message, "Start conversation now.")
                if initial_response:
                    st.session_state.messages.append({"role": "assistant", "content": initial_response.text})
            except Exception as e:
                st.error(f"Error starting chat: {e}")

        # Display Chat History
        for message in st.session_state.messages:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])

        # Chat
