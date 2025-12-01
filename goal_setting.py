import os
import google.generativeai as genai
from dotenv import load_dotenv

# API keys and configuration
load_dotenv()
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

MODEL_NAME = os.getenv("GEMINI_MODEL_1")
if not MODEL_NAME:
    raise ValueError("Error: GEMINI_MODEL is not set in your .env file")

# Evaluate the response, takes in:
    # tutor_input (str): user input
    # scenario_data (dict): scenarios.json

def evaluate_tutor_response(tutor_input, scenario_data=None):
    model = genai.GenerativeModel(MODEL_NAME)

    if scenario_data:
        p_goal = scenario_data['parent']
        s_goal = scenario_data['student']
        conflict_type = scenario_data['conflict type']
    else:
        # Default fallback (if run alone for testing)
        p_goal = "I am paying for results. Alex needs an A on this physics lab report to salvage his GPA. I don't care how you get him there—edit it, rewrite it, whatever helps. If he fails this assignment, I don't see the point in continuing these expensive sessions."
        s_goal = "I don't understand the material and I'm freaking out. My dad is going to kill me if I get a bad grade. Please, can you just write the analysis section for me? I'll do the rest, but I need you to guarantee this part is perfect."
        conflict_type = "Ethical"

    full_prompt = f"""
    ROLE:
    You are an expert evaluator for educational tutors. 

    YOUR TASK:
    Your task is to grade a Tutor's response to conflicting requests between a student and their parent.
    Parent Request: "{p_goal}"
    Student Request: "{s_goal}"
    Conflict type: '{conflict_type}
    
    Evaluate the Tutor's response below to see if they resolved the conflict.
    
    TUTOR RESPONSE:
    "{tutor_input}"
    
    EVALUATION CONSTRAINTS:

    If the conflict type is Ethical and the tutor's response explicitly violates academic integrity and commits academic dishonesty, risks safety, or violates professional boundaries, the maximum score possible is a 2.
    If the conflict type is Process and the tutor's response completely ignores one party, the maximum score is a 5.

    EVALUATION CRITERIA AND ALGORITHM:
    
    Evaluate the Tutor Response against these weighted criteria:
    1. Pedagogical Integrity (25%): Does the solution result in the student doing cognitive work and learning?
    2. Stakeholder Alignment (20%): Does the tutor address the Parent's concerns and the Student's concerns without caving to the unethical demand or ignoring the conflict overall?
    3. Tone (10%): Does the response tone de-escalate the situation? Does the tutor avoid defensiveness, stubborness, and hostility?
    4. Empathy (10%): Does the response avoid judgement and demonstrates emotional understanding?
    5. Compromise (25%): Does the response prioritize solutions with compromise when possible? If compromise is not reasonable, does the tutor explain why to upkeep trust?
    6. Communication(10%): Is the response clear, specific, and actionable?

    OUTPUT FORMAT:

    Score the response as an integer between 1-10. Provide a concise explaination of the score, do not directly reference or state the criteria in the explaination. Provide postive feedback if score is above 2. Provide negative feedback outlining areas for improvement.
    """

    try:
        response = model.generate_content(full_prompt)
        return response.text
    except Exception as e:
        return f"AI Error: {e}"

# --- MAIN EXECUTION (Testing) ---
if __name__ == "__main__":
    print("--- Test Mode ---")
    user_in = input("Enter dummy response: ")
    print(evaluate_tutor_response(user_in))