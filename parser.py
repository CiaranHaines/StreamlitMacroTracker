import pandas as pd
import re

def parse_gemini_table(text):
    """
    Parses a multi-line text block (e.g. from a Gemini chat) into a Pandas DataFrame.
    It uses a right-to-left heuristic to separate the food name from the 5 trailing numeric values.
    Also ignores headers and rows containing 'total'.
    """
    lines = text.strip().split('\n')
    parsed_data = []
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
            
        # Skip header-like lines or 'total' lines
        lower_line = line.lower()
        if 'food item' in lower_line or 'calories' in lower_line or 'total' in lower_line:
            continue
            
        # Split by whitespace
        tokens = line.split()
        
        # We expect at least a food name and 5 numeric values
        if len(tokens) < 6:
            continue
            
        # Try to extract the last 5 tokens as numbers, ignoring commas
        try:
            fiber = float(tokens[-1].replace(',', ''))
            carbs = float(tokens[-2].replace(',', ''))
            fat = float(tokens[-3].replace(',', ''))
            protein = float(tokens[-4].replace(',', ''))
            calories = float(tokens[-5].replace(',', ''))
            
            # The rest of the tokens make up the food name
            food_name = ' '.join(tokens[:-5]).strip()
            
            parsed_data.append({
                'food_name': food_name,
                'calories': calories,
                'protein': protein,
                'fat': fat,
                'carbs': carbs,
                'fiber': fiber
            })
        except ValueError:
            # If the last 5 tokens aren't numbers, this line doesn't match our strict format
            continue
            
    return pd.DataFrame(parsed_data)
