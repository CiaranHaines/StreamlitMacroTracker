import pytest
import pandas as pd
from parser import parse_gemini_table

# The exact text provided by the user
USER_TEST_TEXT = """
Food Item Calories Protein (g) Fat (g) Carbs (g) Fiber (g)
Fruit & Spinach Smoothie 138 2.2 0.6 34.5 6.4
Greek Yogurt (40g) 38 1.6 3.6 1.5 0.0
Pork & Shrimp Dumplings (4) 320 16.0 14.0 32.0 1.5
Tesco Finest Pork Sausage 215 11.2 17.5 2.8 0.5
2x Coffees w/ Milk 40 2.0 2.2 3.0 0.0
Half of "Big Salad" 684 51.9 27.5 63.0 22.7
2x Eggs (Spray Oil) 144 12.6 9.5 0.8 0.0
Kimchi (50g) 15 1.1 0.2 2.4 1.2
Greek Yogurt (100g) 95 4.0 9.0 3.8 0.0
Peanut Butter (1 tbsp) 95 4.0 8.0 3.0 1.0
Honey (1 tsp) 21 0.0 0.0 6.0 0.0
Guinness 0.0 (440ml) 75 0.6 0.0 17.0 0.0
DAILY TOTAL 1,880 107.2 92.1 169.8 33.3
"""

def test_parse_removes_headers_and_totals():
    df = parse_gemini_table(USER_TEST_TEXT)
    
    # Check that headers ('Food Item...') and totals ('DAILY TOTAL...') are missing
    assert 'food item' not in df['food_name'].str.lower().values
    assert 'daily total' not in df['food_name'].str.lower().values
    assert 'total' not in df['food_name'].str.lower().values
    
    # Should have 12 rows of actual food data
    assert len(df) == 12

def test_correct_extraction_of_numbers_in_names():
    df = parse_gemini_table(USER_TEST_TEXT)
    
    # Find the smoothie
    smoothie = df[df['food_name'] == 'Fruit & Spinach Smoothie'].iloc[0]
    assert smoothie['calories'] == 138.0
    assert smoothie['protein'] == 2.2
    
    # Find the Guinness (testing numbers inside the name)
    guinness = df[df['food_name'] == 'Guinness 0.0 (440ml)'].iloc[0]
    assert guinness['calories'] == 75.0
    assert guinness['carbs'] == 17.0
    
    # Find the eggs (testing symbols and numbers)
    eggs = df[df['food_name'] == '2x Eggs (Spray Oil)'].iloc[0]
    assert eggs['calories'] == 144.0
    assert eggs['fat'] == 9.5
    
    # Find the salad (testing quotes)
    salad = df[df['food_name'] == 'Half of "Big Salad"'].iloc[0]
    assert salad['calories'] == 684.0

def test_handles_commas_in_numbers():
    text_with_comma = "Huge Meal 1,500 50,2 10 100 5"
    df = parse_gemini_table(text_with_comma)
    assert len(df) == 1
    assert df.iloc[0]['calories'] == 1500.0
