def calculate_bmi(weight_kg, height_m):
    """
    Calculate BMI.
    Formula: weight (kg) / (height (m) ^ 2)
    """
    if height_m <= 0:
        raise ValueError("Height must be greater than zero.")
    if weight_kg <= 0:
        raise ValueError("Weight must be greater than zero.")
    return weight_kg / (height_m ** 2)

def get_category_info(bmi):
    """
    Classify the BMI into standard health categories.
    Returns a dictionary containing the category name, hex color, and a soft background hex color.
    """
    if bmi < 18.5:
        return {
            "category": "Underweight",
            "color": "#3498db",  # Blue
            "bg": "#ebf5fb",
            "desc": "You are underweight. Consider discussing with a healthcare professional."
        }
    elif bmi < 25.0:
        return {
            "category": "Normal weight",
            "color": "#2ecc71",  # Green
            "bg": "#eafaf1",
            "desc": "Great! You have a healthy weight. Keep maintaining a balanced lifestyle."
        }
    elif bmi < 30.0:
        return {
            "category": "Overweight",
            "color": "#f39c12",  # Amber/Orange
            "bg": "#fef5e7",
            "desc": "You are slightly overweight. Consider active exercises and diet balancing."
        }
    else:
        return {
            "category": "Obese",
            "color": "#e74c3c",  # Red
            "bg": "#fdedec",
            "desc": "You are in the obese category. It is recommended to seek medical advice."
        }

def convert_imperial_to_metric(lbs, feet, inches):
    """
    Convert Imperial measurements to Metric:
    lbs -> kg
    feet and inches -> meters
    """
    if lbs < 0 or feet < 0 or inches < 0:
        raise ValueError("Measurements cannot be negative.")
    
    total_inches = (feet * 12) + inches
    if total_inches <= 0:
        raise ValueError("Height must be greater than zero.")
    
    height_m = total_inches * 0.0254
    weight_kg = lbs * 0.45359237
    return weight_kg, height_m

def convert_metric_to_imperial(weight_kg, height_m):
    """
    Convert Metric measurements to Imperial (for user reference):
    kg -> lbs
    meters -> feet and inches
    """
    if weight_kg <= 0 or height_m <= 0:
        raise ValueError("Measurements must be positive.")
    
    lbs = weight_kg / 0.45359237
    total_inches = height_m / 0.0254
    feet = int(total_inches // 12)
    inches = total_inches % 12
    return lbs, feet, inches

def validate_numeric(val, field_name):
    """
    Validate that an input can be parsed to a positive float.
    Raises ValueError with a friendly message if invalid.
    """
    try:
        f_val = float(val)
    except (ValueError, TypeError):
        raise ValueError(f"Please enter a valid numeric value for {field_name}.")
    
    if f_val <= 0:
        raise ValueError(f"{field_name.capitalize()} must be a positive number greater than zero.")
    
    return f_val
