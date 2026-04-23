"""
ASA screening via explicit checklist.
Replaces AI interpretation with deterministic yes/no questions.
"""

ASA3_CONDITIONS = [
    "I have a pacemaker or implanted defibrillator (ICD)",
    "I am on dialysis or have kidney failure",
    "I have heart failure or severe heart disease",
    "I use home oxygen",
    "I have cirrhosis or severe liver disease",
    "My diabetes is poorly controlled (A1c above 8, or my doctor says it is uncontrolled)",
    "My blood pressure is poorly controlled (my doctor says it is uncontrolled)",
    "I have severe COPD or severe lung disease",
    "My BMI is 45 or above (morbid obesity)",
    "I have had a heart attack or stroke in the last 6 months",
]
