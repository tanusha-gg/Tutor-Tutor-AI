import os
import google.generativeai as genai
from dotenv import load_dotenv

# API keys and configuration
load_dotenv()
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

MODEL_NAME = os.getenv("GEMINI_MODEL_3")
if not MODEL_NAME:
    raise ValueError("Error: GEMINI_MODEL is not set in your .env file")

def generate_training_plan(conversation_log):
    model = genai.GenerativeModel(MODEL_NAME)
    # We turn the list of log entries into a single block of text
    transcript_text = "\n".join(conversation_log)
    prompt = f"""
    ROLE:
    You are an expert evaluator for educational tutors. You have just observed a simulation between a candidate tutor and a student named 'Alex' (who is shy/low-confidence).
    
    DATA:
    Transcript:
    {transcript_text}
    
    TASK:
    Determine if the responses are:
    1. highly appropriate (demonstrating empathy, perspective-taking, and skillful intervention)
    2. moderately appropriate  (showing some understanding but missed opportunities) 
    3. inappropriate responses (avoidant, dismissive, or reactive approaches). 
    
    Evaluate whether the educator response demonstrates:
    1. Emotional Recognition: Does the response acknowledge or name the student's emotional state? Does it avoid dismissing, minimizing, or ignoring emotions?​
    2. Perspective-Taking: Does the response reflect understanding of the situation from the student's viewpoint, not just the educator's view?​
    3. Alignment with Emotional Intensity: Does the response appropriately match the emotional intensity of the situation, neither underreacting ("this is easy") nor overreacting? Does the response validate feelings, normalize experiences, demonstrate perspective-taking?
    4. Non-judgmental Stance: Does the response avoid labeling the student negatively or projecting assumptions?​ Does the response refrain from assuming the student's experience or cultural context?
    5. Pause and Reflection: Does the response suggest the educator has regulated their own emotional response before acting? Language like "I noticed," "I paused to consider," or "Let me understand your perspective first" signals regulation.​
    6. Collaborative Problem-Solving Language: Does the response invite the student into problem-solving rather than imposing solutions?
    7. Expression of Genuine Care: Does the response communicate that the educator cares about the student as a person, not just their academic performance?​
    8. Noticing and Appreciation: Does the response show specific attention to the student's strengths, experiences, or perspectives?​ Does the response include listening, asking open-ended questions, reflecting emotions, labeling student experience?
    9. Follow-Through Intent: Does the response suggest ongoing support or relationship-building, not just addressing the immediate problem?
    10. Seeking to Understand: Does the response invite the student to explain their context rather than the educator imposing interpretation?
    11. Equity Awareness: Does the response demonstrate awareness that students have different lived experiences and that the same classroom situation may feel different depending on background?
    
    
    Identify common professional pitfalls—like minimizing student emotions, avoiding necessary confrontation, overfocusing on situational details instead of student needs, or responding to surface behavior without understanding underlying needs.
    

    Generate a concise Training Plan that considers:
    1. STRENGTHS (What to keep doing)
    2. WEAKNESSES/AREAS FOR GROWTH (Specific moments where they lost the student)
    3. ACTIONABLE PRACTICE (A specific exercise to try next time)
    
    OUTPUT FORMAT:
    Please organize the response clearly with bold headers. Do no explicitly restate the criteria, reframe the feedback specific to the simulation.
    """
    
    response = model.generate_content(prompt)
    return response.text

# --- MAIN EXECUTION (Testing Mode) ---
if __name__ == "__main__":
    # Since we aren't running the full simulation right now, 
    # we create a 'Fake' log to test the Feedback Module.
    
    print("--- AI Feedback & Training Module ---")
    print("Loading sample transcript...\n")
    
    dummy_log = [
        "Tutor: Hi Alex, let's do math.",
        "Student: I don't want to. I'm bad at it.",
        "Tutor: You're not bad, you just need to work harder. Look at this equation.",
        "Student: ... okay.",
        "Tutor: So, what is X?",
        "Student: I don't know."
    ]
        
    print("Generating Training Plan...")
    plan = generate_training_plan(dummy_log)
    
    print("\n" + "="*30)
    print("   PERSONALIZED TRAINING PLAN   ")
    print("="*30)
    print(plan)