import streamlit as st
import google.generativeai as genai
import os
from dotenv import load_dotenv

# Import your existing modules
import data_manager
import goal_setting
import feedback_training

# 1. SETUP & CONFIGURATION
load_dotenv()
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

st.set_page_config(page_title="AI Tutor Trainer", layout="wide")

# --- INITIALIZE SESSION STATE (To track progress) ---
if "goal_progress" not in st.session_state:
    st.session_state.goal_progress = {} 

if "sim_progress" not in st.session_state:
    st.session_state.sim_progress = set()

# --- SIDEBAR NAVIGATION ---
st.sidebar.title("Navigation")
page = st.sidebar.radio("Go to:", ["Goal Setting Evaluation", "Judgment Call Simulation", "Progress Checklist"])

# ==========================================
# PAGE 1: GOAL SETTING EVALUATION
# ==========================================
if page == "Goal Setting Evaluation":
    st.title("🎯 Goal Setting Evaluation")
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

        # Display Scenario
        col1, col2 = st.columns(2)
        with col1:
            st.info(f"**Parent says:**\n\n\"{current_scenario['parent']}\"")
        with col2:
            st.warning(f"**Student says:**\n\n\"{current_scenario['student']}\"")

        # Response Input
        st.subheader("Your Response")
        tutor_response = st.text_area("How would you respond?", height=150, key=f"text_{scenario_id}")

        if st.button("Evaluate Response"):
            if not tutor_response:
                st.error("Please enter a response first.")
            else:
                with st.spinner("AI is grading your response..."):
                    feedback = goal_setting.evaluate_tutor_response(tutor_response, current_scenario)
                    
                st.session_state.goal_progress[scenario_id] = feedback
                
                st.success("Evaluation Complete! Progress Saved.")
                st.markdown(f"### Feedback:\n{feedback}")

# ==========================================
# PAGE 2: JUDGMENT CALL SIMULATION
# ==========================================
elif page == "Judgment Call Simulation":
    st.title("🗣️ Judgment Call Simulation")
    st.markdown("Chat with a simulated student.")

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
            # Clear the context blurb so it regenerates for the new student
            if "context_blurb" in st.session_state:
                del st.session_state.context_blurb
        
        # --- NEW LOGIC START: Generate Context Blurb ---
        # We need the model initialized to generate the blurb
        model_2 = genai.GenerativeModel(os.getenv("GEMINI_MODEL_2"))

        # Generate the blurb only if it doesn't exist yet for this session
        if "context_blurb" not in st.session_state:
            with st.spinner("Setting the scene..."):
                context_prompt = f"""
                Based on this student persona: "{selected_persona['description']}"
                
                Please write a 2-sentence context introduction for the tutor. 
                Include the student's approximate age/grade and the specific subject or assignment they are working on right now.
                Do not include dialogue, just the setting.
                """
                context_response = model_2.generate_content(context_prompt)
                st.session_state.context_blurb = context_response.text

        # Display the generated context
        st.info(f"**Simulation Context:** {st.session_state.context_blurb}")
        # --- NEW LOGIC END ---

        # Initialize Chat Session (Roleplay)
        if st.session_state.chat_session is None:
            
            # System instructions
            history = [
                {"role": "user", "parts": [f"System Instruction: Roleplay this student strictly.\n\n{selected_persona['description']}"]},
                {"role": "model", "parts": ["Understood. I am in character."]}
            ]
            st.session_state.chat_session = model_2.start_chat(history=history)
            
            # Generate initial greeting from the Student (AI)
            try:
                initial_response = st.session_state.chat_session.send_message("Start the conversation now with a short opening sentence as the student.")
                st.session_state.messages.append({"role": "assistant", "content": initial_response.text})
            except Exception as e:
                st.error(f"Error starting chat: {e}")

        # Display Chat History
        for message in st.session_state.messages:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])

        # Chat Input
        if prompt := st.chat_input("Type your response here..."):
            with st.chat_message("user"):
                st.markdown(prompt)
            st.session_state.messages.append({"role": "user", "content": prompt})

            try:
                response = st.session_state.chat_session.send_message(prompt)
                ai_reply = response.text
                with st.chat_message("assistant"):
                    st.markdown(ai_reply)
                st.session_state.messages.append({"role": "assistant", "content": ai_reply})
            except Exception as e:
                st.error(f"Error: {e}")

        st.divider()
        if st.button("End Simulation & Get Feedback"):
            if len(st.session_state.messages) < 2:
                st.warning("Please have a conversation before generating feedback.")
            else:
                conversation_log = [f"{msg['role'].title()}: {msg['content']}" for msg in st.session_state.messages]
                
                with st.spinner("Analyzing conversation dynamics..."):
                    training_plan = feedback_training.generate_training_plan(conversation_log)
                
                st.session_state.sim_progress.add(selected_persona_name)
                
                st.markdown("### 📝 Personalized Training Plan")
                st.write(training_plan)

# ==========================================
# PAGE 3: PROGRESS CHECKLIST
# ==========================================
elif page == "Progress Checklist":
    st.title("✅ Training Progress")
    
    data = data_manager.load_data()
    
    # 1. Goal Setting Progress
    st.subheader("Goal Setting Scenarios")
    if data:
        all_scenarios = data['goal_setting_scenarios']
        completed_ids = st.session_state.goal_progress.keys()
        
        progress_val = len(completed_ids) / len(all_scenarios)
        st.progress(progress_val)
        st.write(f"**{len(completed_ids)} / {len(all_scenarios)} Completed**")
        
        for s in all_scenarios:
            s_id = s['id']
            is_done = s_id in completed_ids
            
            icon = "✅" if is_done else "⬜"
            with st.expander(f"{icon} Case {s_id}"):
                if is_done:
                    st.markdown("**Your previous feedback:**")
                    st.write(st.session_state.goal_progress[s_id])
                else:
                    st.write("Not attempted yet.")

    st.divider()

    # 2. Judgment Call Progress
    st.subheader("Judgment Call Simulations")
    if data:
        all_personas = [p['name'] for p in data['judgment_personas']]
        completed_sims = st.session_state.sim_progress
        
        progress_val_sim = len(completed_sims) / len(all_personas)
        st.progress(progress_val_sim)
        st.write(f"**{len(completed_sims)} / {len(all_personas)} Completed**")
        
        for name in all_personas:
            is_done = name in completed_sims
            icon = "✅" if is_done else "⬜"
            st.write(f"{icon} {name}")
