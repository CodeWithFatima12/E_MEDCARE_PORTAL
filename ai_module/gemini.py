from google import genai  # UPDATED: New SDK import
from django.conf import settings
import json

def generate_diet_plan(data_dict):
    """
    Accepts the dictionary from form.get_data_for_gemini()
    ses the new google-genai SDK.
    """
   
    # --- Step 0: Initialize Client ---
    # It is safer to use settings.GEMINI_API_KEY if you have it defined there
    api_key = getattr(settings, "GEMINI_API_KEY", None)
    client = genai.Client(api_key=api_key)

    # Extract data
    age = data_dict.get('age')
    height_inches = data_dict.get('height') 
    weight = data_dict.get('weight')  
    gender = data_dict.get('gender')         
    goal = data_dict.get('goal')             # 'lose' or 'gain'
    duration = data_dict.get('duration')
    # region = data_dict.get('region')
    country = data_dict.get('country') 
    selected_meals = data_dict.get('meals', [])
    # selected_meals = data_dict.get('meals', ['breakfast', 'lunch', 'dinner'])
    dislikes_list = data_dict.get('dislikes', [])

    # --- Step 1: Conversion & BMI Calculation ---
    
    # 1. Convert Inches to Centimeters (1 inch = 2.54 cm)
    height_cm = height_inches * 2.54
    
    # 2. Convert Centimeters to Meters for BMI formula
    height_m = height_cm / 100
    
    # 3. Calculate BMI: weight (kg) / [height (m)]^2
    bmi = round(weight / (height_m ** 2), 1)
    
    # --- Step 2: Sanity Check (Safety Shield) ---
    if bmi > 60 or bmi < 10:
        return {
            "error": f"Invalid height/weight combination. Calculated BMI: {bmi}. "
                     "Please ensure height is in total inches (e.g., 63 for 5'3\") "
                     "and weight is in kilograms."
        }
    
    status_message = ""
    actual_goal = goal 

    # BMI Thresholds
    if bmi < 18.5:
        current_status = "underweight"
    elif 18.5 <= bmi <= 24.9:
        current_status = "normal"
    else:
        current_status = "overweight"

    # CASE 1: User is Normal weight
    if current_status == "normal":
        if goal != "maintain":
            status_message = "You already have an ideal weight. There is no need to gain or lose weight. We have generated a maintenance plan for you."
        else:
            status_message = "Great! You are at an ideal weight. We've created a plan to help you maintain it."
        actual_goal = "maintain"

    # CASE 2: User is Overweight but wants to Maintain or Gain
    elif current_status == "overweight":
        if goal == "maintain" or goal == "gain":
            status_message = f"Note: Your BMI is {bmi} (Overweight). Instead of {goal}ing, we recommend a weight loss approach to reach a healthy range."
            actual_goal = "lose"
        else:
            status_message = f"Your BMI is {bmi} (Overweight). We have generated a weight loss plan to help you reach your goals safely."
            actual_goal = "lose"

    # CASE 3: User is Underweight but wants to Maintain or Lose
    elif current_status == "underweight":
        if goal == "maintain" or goal == "lose":
            status_message = f"Note: Your BMI is {bmi} (Underweight). Instead of {goal}ing, we recommend a weight gain approach to reach a healthy normal range."
            actual_goal = "gain"
        else:
            status_message = f"Your BMI is {bmi} (Underweight). We have generated a weight gain plan to help you improve your health."
            actual_goal = "gain"

# --- Step 4: Construct the Prompt ---
    meal_names = [m.replace('_', ' ').title() for m in selected_meals]
    meals_string = ", ".join(meal_names)

# To this (Use underscores instead of spaces):
    dynamic_sample = {name.replace(' ', '_'): "Food name and quantity in grams" for name in meal_names}
    dislike_text = ", ".join(dislikes_list) if dislikes_list else "none"

    prompt = f"""
    You are a professional nutritionist in {country}. 
    User Profile: Age {age}, Height {height_inches} inches ({round(height_cm, 1)}cm), Weight {weight}kg, BMI {bmi}.
    Goal: {actual_goal.upper()} weight.
    
    Task: Create a detailed {duration}-day diet plan for a {gender} user.
    
    CRITICAL INSTRUCTIONS:
    1. STRICT MEAL SELECTION: You MUST ONLY generate keys for these meals: {meals_string}. 
    2. ABSOLUTE FORBIDDEN: Do NOT include any meal type (like Breakfast, Lunch, or Dinner) if it is not in this specific list: {meals_string}.
    3. Use ingredients common in {country} and strictly EXCLUDE: {dislike_text}.
    4. Calculate daily calorie needs for a {gender} and specify quantities in GRAMS.
    5. Provide the plan for exactly {duration} days.
    6. If female, ensure adequate Iron and Calcium sources.
    7. If male, ensure protein portions are optimized for muscle maintenance.
    8.Strictly EXCLUDE these foods: {dislike_text}.
    9.Specify exact quantities in GRAMS for every food item (e.g., "150g Grilled Chicken", "200g Brown Rice").
    
    Output Format:
    Return ONLY a JSON object with this exact structure:
    {{
      "status_info": "{status_message}",
      "plan": {{
        "Day 1": {json.dumps(dynamic_sample)},
        "Day 2": {json.dumps(dynamic_sample)}
      }}
    }}
    """

    # --- Step 5: AI Generation ---
    try:
        # UPDATED: New syntax for content generation
        response = client.models.generate_content(
            model='gemini-2.5-flash-lite', 
<<<<<<< HEAD
=======
            # model='gemini-2.5-flash', 
>>>>>>> 753494074b90b5844b76cd1c3ad31159a0d84bf0
            contents=prompt,
            config={
                'response_mime_type': 'application/json',
            }
        )
        
        # Clean the response text (the new SDK is better at returning clean strings)
        text = response.text.strip()
        if "```json" in text:
            text = text.split("```json")[1].split("```")[0]
        
        return json.loads(text.strip())

    except Exception as e:
        print(f"Error: {str(e)}")
        return {"error": f"Failed to generate: {str(e)}"}