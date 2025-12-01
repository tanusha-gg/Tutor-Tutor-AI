import os
import google.generativeai as genai
from dotenv import load_dotenv

# API keys and configuration
load_dotenv()
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

MODEL_NAME = os.getenv("GEMINI_MODEL_2")
if not MODEL_NAME:
    raise ValueError("Error: GEMINI_MODEL is not set in your .env file")

# Evaluate the response, takes in:
    # custom_persona (str): personality description
def run_simulation(custom_persona=None):
    model = genai.GenerativeModel(MODEL_NAME)

    if custom_persona:
        student_persona = custom_persona
    else:
        # Default fallback (Alex)
        student_persona = """
        You are 'Alex', a 10th-grade math student.
        PERSONALITY: Extremely shy, low confidence.
        BEHAVIOR: Speak in short sentences. Shut down if the tutor is too aggressive.
        GOAL: The tutor must be gentle and encouraging to get you to open up.
        """
    
    # Keep AI in character until end
    try:
        chat = model.start_chat(history=[
            {"role": "user", "parts": [f"System Instruction: Roleplay this student strictly.\n\n{student_persona}"]},
            {"role": "model", "parts": ["Understood. I am in character."]}
        ])
    except Exception as e:
        print(f"Error starting chat: {e}")
        return []

    print(f"\n--- SIMULATION START ---")
    print("(The student is waiting. Type your greeting. Type 'END' to finish.)")
    
    conversation_log = []

    while True:
        try:
            tutor_input = input("You (Tutor): ")
        except KeyboardInterrupt:
            break
            
        if tutor_input.strip().upper() == "END":
            break
        
        try:
            response = chat.send_message(tutor_input)
            print(f"Student: {response.text}")
            conversation_log.append(f"Tutor: {tutor_input}")
            conversation_log.append(f"Student: {response.text}")
            
        except Exception as e:
            print(f"Connection Error: {e}")
            break

    return conversation_log

# --- MAIN EXECUTION (Testing) ---
if __name__ == "__main__":
    run_simulation()