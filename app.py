import streamlit as st
import google.generativeai as genai
import os
import time
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

# --- CACHED FUNCTIONS (THE FIX) ---
# @st.cache_data tells Streamlit: "If the input 'persona_desc' hasn't changed, 
# return the saved text immediately. Do NOT call the API."
@st.cache_data(show_spinner=False)
def generate_context_blurb(persona_desc):
    try:
        model = genai.GenerativeModel(os.getenv("GEMINI_MODEL_2"))
        context_prompt = f"""
        Based on this student persona: "{persona_desc}"
        Please write a 2-sentence context introduction for the tutor. 
        Include the student's approximate age/grade and the specific subject.
        """
        response = model.generate_content(context_prompt)
        return response.text
    except Exception as e:
        return "Simulation Context: High School Math Session. (API Quota Limit Reached - Using Default)"

# --- INITIALIZE SESSION STATE ---
if "goal_progress" not in st.session_state:
    st.session_state.goal_progress = {} 

if "sim_progress" not in st.session_state:
    st.session_state.sim_progress = set()

# --- HELPER FUNCTIONS ---
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
                    # We can use basic error handling here too
                    try:
                        feedback = goal_setting.evaluate_tutor_response(tutor_response, current_scenario)
                        st.session_state.goal_progress[scenario_id] = feedback
                        st.success("Evaluation Complete! Progress Saved.")
                        st.markdown(f"### Feedback:\n{feedback}")
                    except Exception as e:
                        st.error(f"Error: {e}. Please wait a moment and try again.")

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
        
        # --- NEW: USE CACHED GENERATION ---
        # This will only call the API once per persona, ever.
        if "context_blurb" not in st.session_state:
            with st.spinner("Setting the scene..."):
                blurb = generate_context_blurb(selected_persona['description'])
                st.session_state.context_blurb = blurb

        st.info(f"**Simulation Context:** {st.session_state.context_blurb}")

        # Initialize Chat Session
        model_2 = genai.GenerativeModel(os.getenv("GEMINI_MODEL_2"))
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
                 # Soft fail if rate limited on start
                st.warning("Rate limit hit. Please wait 30 seconds and refresh.")

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
                st.error("⚠️ AI is overloaded. Please wait a moment and try again.")

        st.divider()
        if st.button("End Simulation & Get Feedback"):
            if len(st.session_state.messages) < 2:
                st.warning("Please have a conversation before generating feedback.")
            else:
                conversation_log = [f"{msg['role'].title()}: {msg['content']}" for msg in st.session_state.messages]
                with st.spinner("Analyzing conversation dynamics..."):
                    try:
                        training_plan = feedback_training.generate_training_plan(conversation_log)
                        st.session_state.sim_progress.add(selected_persona_name)
                        st.markdown("### 📝 Personalized Training Plan")
                        st.write(training_plan)
                    except Exception:
                        st.error("Rate limit hit during feedback generation. Try again in 1 minute.")

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
st.sidebar.image("https://cdn-icons-png.flaticon.com/512/4762/4762311.png", width=100)
st.sidebar.title("Tutor Tutor AI")
st.sidebar.markdown("---")
page = st.sidebar.radio("Navigate:", ["Home", "Methodology & Criteria", "Technical Architecture", "Future Roadmap", "Try the Prototype"])

# ==========================================
# PAGE 1: HOME (Problem & Solution)
# ==========================================
if page == "Home":
    st.title("Tutor Tutor AI")
    st.subheader("An AI Tutor for Tutors")
    st.markdown("---")
    
    # PROBLEM SECTION
    st.header("The Problem")
    col1, col2 = st.columns(2)
    
    with col1:
        st.image("https://images.unsplash.com/photo-1544716278-ca5e3f4abd8c?q=80&w=1974&auto=format&fit=crop")
    
    with col2:
        st.warning("Tutoring is a **$20B dollar industry**.")
        st.markdown("""
        Yet, non-professional educators are often vetted based solely on **content knowledge**, not on **teaching ability**.
        * Most tutors lack the pedagogical skills needed to be good educators.
        * **"There is a difference between knowing Calculus and being able to teach it."**
        """)
    st.markdown("---")
    
    # SOLUTION SECTION
    st.header("The Solution")
    st.info("Tutor Tutor AI provides an **accessible and scalable** tutor training solution.")
    colA, colB, colC = st.columns(3)
    
    with colA:
        st.markdown("### 🧠 Active Learning")
        st.write("Realistic, interactive scenario-based simulations.")
    with colB:
        st.markdown("### ⚖️ Diverse Assessment")
        st.write("Considers ethics, communication skills, and soft skills.")
    with colC:
        st.markdown("### 📝 Tailored Feedback")
        st.write("Provides feedback and recommendations unique to each tutor.")

    st.markdown("---")
    if st.button("Start Training Now 🚀"):
         st.info("👈 Click 'Try the Prototype' in the sidebar to begin simulations!")

# ==========================================
# PAGE 2: METHODOLOGY
# ==========================================
elif page == "Methodology & Criteria":
    st.title("Training Structure & Evaluation")
    st.markdown("""
    Our AI transforms subjective language into objective, trainable science. 
    Simulations are instructed to have **high psychological fidelity**, mirroring real classroom dynamics.
    """)
    

    tab1, tab2 = st.tabs(["Goal Setting / Conflict Resolution", "Interpersonal Simulation"])
    
    with tab1:
        st.subheader("Conflict Resolution Criteria")
        st.markdown("We evaluate how tutors balance conflicting requests from parents and students based on these weighted metrics:")
        c1, c2 = st.columns(2)
        with c1:
            st.markdown("**1. Pedagogical Integrity (25%)**")
            st.caption("Does the solution result in the student doing cognitive work and learning?")
            st.markdown("**2. Compromise (25%)**")
            st.caption("Does the response prioritize solutions with compromise? If not, does the tutor explain why to maintain trust?")
            st.markdown("**3. Alignment (20%)**")
            st.caption("Are both concerns addressed without caving to unethical demands or ignoring the conflict?")
        with c2:
            st.markdown("**4. Empathy (10%)**")
            st.caption("Does the response avoid judgment and demonstrate emotional understanding?")
            st.markdown("**5. Tone (10%)**")
            st.caption("Does the tone de-escalate the situation? Avoids defensiveness or hostility.")
            st.markdown("**6. Communication (10%)**")
            st.caption("Is the response clear, specific, and actionable?")

    with tab2:
        st.subheader("Simulation Criteria")
        st.markdown("During the live chat simulation, the AI monitors the tutor for the following soft skills:")
        st.success("**Core Competencies:**")
        col_a, col_b = st.columns(2)
        with col_a:
            st.markdown("- **Emotional Recognition:** Acknowledging the student's state.")
            st.markdown("- **Expression of Genuine Care:** Valuing the student as a person.")
            st.markdown("- **Empathy/Perspective-Taking:** Seeing the student's view.")
            st.markdown("- **Non-judgmental Stance:** Avoiding labeling or assumptions.")
            st.markdown("- **Pause and Reflection:** Regulating own emotions before acting.")
        with col_b:
            st.markdown("- **Collaborative Solution Language:** Inviting the student to solve the problem.")
            st.markdown("- **Noticing and Appreciation:** Attending to strengths.")
            st.markdown("- **Seeking to Understand:** Asking before telling.")
            st.markdown("- **Equity Awareness:** Awareness of lived experiences.")

# ==========================================
# PAGE 3: TECHNICAL ARCHITECTURE
# ==========================================
elif page == "Technical Architecture":
    st.title("Technical Foundation")
    st.markdown("How Tutor Tutor AI is built.")
    
    
    col1, col2 = st.columns([1, 2])
    with col1:
        st.markdown("### 🖥️ Frontend")
        st.write("**Streamlit Web Application**")
        st.caption("Accessible, user-friendly interface for tutors.")
    with col2:
        st.code("import streamlit as st", language="python")

    st.divider()

    col1, col2 = st.columns([1, 2])
    with col1:
        st.markdown("### 🧠 AI Engine")
        st.write("**Google Gemini**")
        st.caption("Acts as the Simulated Student & The Expert Evaluator.")
    with col2:
        st.code("""
import google.generativeai as genai
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
        """, language="python")

    st.divider()

    col1, col2 = st.columns([1, 2])
    with col1:
        st.markdown("### 📂 Data & Logic")
        st.write("**Python Modules & JSON**")
        st.caption("Scenario library stored in JSON; separate logic modules for maintenance.")
    with col2:
        st.code("""
import data_manager
import goal_setting
import feedback_training
        """, language="python")

# ==========================================
# PAGE 4: FUTURE ROADMAP
# ==========================================
elif page == "Future Roadmap":
    st.title("Next Steps")
    st.markdown("Our roadmap to make high-level training scalable and accessible.")
    st.info("### 1. Integrate Checklist & Progress Tracking")
    st.write("Ensure tutors can visualize their growth over time.")
    st.info("### 2. Iterative Feedback Loops")
    st.write("Have each simulation iteration incorporate feedback from prior sessions to increase difficulty.")
    st.info("### 3. Auto-Generate Cases")
    st.write("Potentially auto-generate cases and scenarios to specifically target user weaknesses detected in previous sessions.")
    st.info("### 4. UI/UX Improvements")
    st.write("Improve clarity of instructions and user interface.")

# ==========================================
# PAGE 5: TRY THE PROTOTYPE
# ==========================================
elif page == "Try the Prototype":
    st.title("🖥️ Live Prototype")
    st.markdown("Select a module below to test the AI assessment capabilities.")
    
    tab1, tab2, tab3 = st.tabs(["Goal Setting Evaluation", "Judgment Simulation", "Progress Checklist"])
    
    with tab1:
        run_goal_setting_mode()
        
    with tab2:
        run_simulation_mode()
        
    with tab3:
        run_progress_checklist()
