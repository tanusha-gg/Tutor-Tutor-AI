import json
import random

def load_data():
    """Loads the JSON file into a Python Dictionary"""
    try:
        with open('scenarios.json', 'r') as file:
            return json.load(file)
    except FileNotFoundError:
        print("Error: scenarios.json not found!")
        return None

def get_training_batch():
    """
    Randomly selects 2 Goal Scenarios and 2 Judgment Personas.
    Returns them as a dictionary.
    """
    data = load_data()
    if not data:
        return None
    selected_goals = random.sample(data['goal_setting_scenarios'], 2)
    selected_judgments = random.sample(data['judgment_personas'], 2)

    return {
        "goals": selected_goals,
        "judgments": selected_judgments
    }