"""
ASA Physical Status Classification using Claude API.

ASA 1 — Normal healthy patient
ASA 2 — Mild systemic disease, well-controlled
ASA 3 — Severe systemic disease with functional limitation
ASA 4 — Life-threatening systemic disease

For direct colonoscopy scheduling: ASA 1 or 2 only.
ASA 3+ requires a pre-procedure office visit.
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from config import ANTHROPIC_API_KEY


ASA_PROMPT = """You are a board-certified anesthesiologist reviewing an outpatient colonoscopy candidate for an ambulatory surgery center under moderate (MAC) sedation.

Classify this patient's ASA Physical Status based on the history below.

ASA Definitions for outpatient colonoscopy context:
- ASA 1: Healthy, no active medical problems, non-smoker, no or minimal alcohol use
- ASA 2: Mild systemic disease, well-controlled. Examples: well-controlled HTN, well-controlled T2DM (A1c <8), mild obesity (BMI 30-39), current smoker, pregnancy, social alcohol use, mild lung disease, controlled thyroid disease, controlled seizure disorder
- ASA 3: Severe systemic disease with functional limitation. Examples: poorly controlled HTN or DM (A1c ≥8), morbid obesity (BMI ≥40), active hepatitis, alcohol dependence, implanted cardiac device (pacemaker/ICD), history of MI, CVA, or TIA (>3 months ago), moderate COPD, CKD stage 4+, ESRD on dialysis, CVA with residual deficit, history of premature birth (<60 weeks post-conceptual age), BMI ≥40, poorly controlled DM, history of drug abuse
- ASA 4: Life-threatening disease. Examples: recent MI (<3 months), unstable angina, decompensated heart failure, severe valvular disease, severe COPD, active sepsis, active malignancy with organ dysfunction, ESRD not on scheduled dialysis

Patient History:
Past Medical History: {pmh}
Past Surgical History: {psh}
Social History: {sochx}
Current Medications: {medications}
Allergies: {allergies}

Be CONSERVATIVE — when borderline, assign the higher classification.
For outpatient colonoscopy, ASA 3 and above requires an office visit before scheduling.

Respond ONLY with valid JSON in this exact format:
{{"asa_class": 2, "reasoning": "One to two sentence clinical reasoning.", "key_factors": ["factor1", "factor2"]}}"""


def classify_asa(pmh: str, psh: str, sochx: str, medications: str, allergies: str) -> dict:
    """
    Classify ASA physical status. Returns dict with:
    - asa_class (int 1-4)
    - reasoning (str)
    - key_factors (list of str)
    """
    if not ANTHROPIC_API_KEY:
        return _fallback_classify(pmh, medications, sochx)

    try:
        import anthropic
        client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

        prompt = ASA_PROMPT.format(
            pmh=pmh or "None reported",
            psh=psh or "None reported",
            sochx=sochx or "None reported",
            medications=medications or "None reported",
            allergies=allergies or "None reported",
        )

        response = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=400,
            messages=[{"role": "user", "content": prompt}],
        )

        raw = response.content[0].text.strip()
        # Strip markdown code blocks if present
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        result = json.loads(raw.strip())
        result["asa_class"] = int(result.get("asa_class", 3))
        return result

    except Exception as e:
        return {
            "asa_class": 3,
            "reasoning": f"Automatic classification unavailable. Manual review required before scheduling. ({type(e).__name__})",
            "key_factors": ["Could not auto-classify — please call office"],
        }


def _fallback_classify(pmh: str, medications: str, sochx: str) -> dict:
    """
    Simple keyword-based fallback when no API key is set.
    Conservative: flags common ASA 3 conditions.
    """
    text = f"{pmh} {medications} {sochx}".lower()

    asa3_keywords = [
        "dialysis", "esrd", "renal failure", "heart failure", "chf",
        "pacemaker", "icd", "defibrillator", "copd", "poorly controlled",
        "uncontrolled", "morbid obesity", "bmi 40", "oxygen",
        "stroke", "tia", "mi ", "myocardial", "hepatitis", "cirrhosis",
        "chemotherapy", "active cancer", "oxygen dependent",
    ]

    for kw in asa3_keywords:
        if kw in text:
            return {
                "asa_class": 3,
                "reasoning": f"Possible complex medical history detected ('{kw}'). Manual review required.",
                "key_factors": [f"Flagged: {kw}"],
            }

    none_indicators = ["none", "no history", "healthy", "no medical", "no medications"]
    if all(ind in text for ind in ["none"]):
        return {
            "asa_class": 1,
            "reasoning": "No significant medical history reported.",
            "key_factors": ["No active conditions"],
        }

    return {
        "asa_class": 2,
        "reasoning": "Medical history noted. Appears appropriate for outpatient scheduling based on reported history.",
        "key_factors": ["Based on reported history"],
    }
