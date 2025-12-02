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

# --- INITIALIZE SESSION STATE ---
if "goal_progress" not in st.session_state:
    st.session_state.goal_progress = {} 

if "sim_progress" not in st.session_state:
    st.session_state.sim_progress = set()

# --- HELPER FUNCTIONS FOR PROTOTYPE LOGIC ---
# These functions wrap your previous code so we can call them cleanly in the new layout

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
                    feedback = goal_setting.evaluate_tutor_response(tutor_response, current_scenario)
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
                context_response = model_2.generate_content(context_prompt)
                st.session_state.context_blurb = context_response.text

        st.info(f"**Simulation Context:** {st.session_state.context_blurb}")

        # Initialize Chat Session
        if st.session_state.chat_session is None:
            history = [
                {"role": "user", "parts": [f"System Instruction: Roleplay this student strictly.\n\n{selected_persona['description']}"]},
                {"role": "model", "parts": ["Understood. I am in character."]}
            ]
            st.session_state.chat_session = model_2.start_chat(history=history)
            try:
                initial_response = st.session_state.chat_session.send_message("Start conversation now.")
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

def run_progress_checklist():
    st.subheader("✅ Training Progress")
    data = data_manager.load_data()
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("#### Goal Setting Scenarios")
        if data:
            all_scenarios = data['goal_setting_scenarios']
            completed_ids = st.session_state.goal_progress.keys()
            progress_val = len(completed_ids) / len(all_scenarios)
            st.progress(progress_val)
            st.write(f"**{len(completed_ids)} / {len(all_scenarios)} Completed**")
            
            for s in all_scenarios:
                icon = "✅" if s['id'] in completed_ids else "⬜"
                st.write(f"{icon} Case {s['id']}")

    with col2:
        st.markdown("#### Judgment Simulations")
        if data:
            all_personas = [p['name'] for p in data['judgment_personas']]
            completed_sims = st.session_state.sim_progress
            progress_val_sim = len(completed_sims) / len(all_personas)
            st.progress(progress_val_sim)
            st.write(f"**{len(completed_sims)} / {len(all_personas)} Completed**")
            
            for name in all_personas:
                icon = "✅" if name in completed_sims else "⬜"
                st.write(f"{icon} {name}")


# --- MAIN NAVIGATION ---
st.sidebar.image("https://cdn-icons-png.flaticon.com/512/4762/4762311.png", width=100) # Placeholder Logo
st.sidebar.title("Tutor Tutor AI")
st.sidebar.markdown("---")
page = st.sidebar.radio("Navigate:", ["Home", "About the Project", "Try the Prototype", "Contact Us"])

# ==========================================
# PAGE 1: HOME (Marketing Hook)
# ==========================================
if page == "Home":
    # Hero Section
    st.title("Making Tutors Better, Faster.")
    st.markdown("### An AI-based platform for evaluating and training tutors with a focus on pedagogical and interpersonal skills.")
    
    st.image("https://images.unsplash.com/photo-1524178232363-1fb2b075b655?q=80&w=2070&auto=format&fit=crop", caption="Empowering the next generation of educators.")
    
    st.markdown("---")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.header("💡 Identify")
        st.write("Assess soft skills beyond subject expertise.")
    with col2:
        st.header("🤝 Engage")
        st.write("Simulate realistic student interactions.")
    with col3:
        st.header("📈 Grow")
        st.write("Receive actionable feedback to improve teaching.")
        
    st.markdown("---")
    if st.button("Try the Prototype Now 🚀"):
        # Note: Streamlit buttons can't easily force navigation without extra logic, 
        # so we usually just direct them to the sidebar
        st.info("👈 Click 'Try the Prototype' in the sidebar to start!")

# ==========================================
# PAGE 2: ABOUT THE PROJECT (Proposal Content)
# ==========================================
elif page == "About the Project":
    st.title("Why Tutor Tutor AI?")
    
    # PROBLEM STATEMENT
    st.subheader("⚠️ The Problem")
    st.markdown("""
    The tutoring market is growing rapidly, yet **skills required for tutoring extend beyond content knowledge.** Many tutors (especially peer tutors) have little formal training in pedagogy. While they have "social congruence" with students, they often lack critical soft skills:
    * **Pedagogical competencies** (How to teach, not just what to teach)
    * **Social-Emotional Learning (SEL)**
    * **Interpersonal awareness**
    
    *Current platforms only vet for transcripts, leaving a gap in client-oriented training.*
    """)
    
    st.divider()

    # PROPOSED SOLUTION
    st.subheader("🛠️ The Solution")
    st.markdown("""
    We are developing a scalable AI-based assessment and training program providing realistic, scenario-based interactions.
    
    **Core Modules:**
    1.  **Goal-Setting Evaluation:** Handling conflicting goals between parents and students.
    2.  **Judgment Call Simulations:** "Interviewing" with an AI student to test empathy and adaptability.
    3.  **AI Feedback & Training:** Automated, actionable feedback based on expert pedagogical frameworks.
    """)
    
    # TARGET AUDIENCE
    st.divider()
    st.subheader("🎯 Target Audience")
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("#### For Tutors")
        st.markdown("- Peer tutors (High school/College)\n- Adult independent tutors\n- Professionals seeking certification")
    with col2:
        st.markdown("#### For Platforms")
        st.markdown("- Tutoring agencies (Varsity Tutors, etc.)\n- Schools launching peer-mentoring programs")

# ==========================================
# PAGE 3: TRY THE PROTOTYPE (The Tool)
# ==========================================
elif page == "Try the Prototype":
    st.title("🖥️ Live Prototype")
    st.markdown("Select a module below to test the AI assessment capabilities.")
    
    # Tabs to organize the tool functions cleanly
    tab1, tab2, tab3 = st.tabs(["Goal Setting Evaluation", "Judgment Simulation", "Progress Checklist"])
    
    with tab1:
        run_goal_setting_mode()
        
    with tab2:
        run_simulation_mode()
        
    with tab3:
        run_progress_checklist()

# ==========================================
# PAGE 4: CONTACT / FEEDBACK
# ==========================================
elif page == "Contact Us":
    st.title("📬 Get in Touch")
    st.markdown("We are currently in the prototyping phase (Hackathon Project). We value your feedback!")
    
    with st.form("feedback_form"):
        name = st.text_input("Name")
        email = st.text_input("Email")
        role = st.selectbox("I am a...", ["Student", "Tutor", "Parent", "Educator", "Developer", "Other"])
        message = st.text_area("Feedback or Inquiries")
        
        submitted = st.form_submit_button("Submit Feedback")
        
        if submitted:
            st.success(f"Thanks {name}! We've received your feedback.")
            # In a real app, you would save this to a database here.
