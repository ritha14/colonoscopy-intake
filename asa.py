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


ASA_PROMPT = """You are a board-certified anesthesiologist reviewing an outpatient colonoscopy candidate for an ambulatory surgery center under moderate sedation.

Classify this patient's ASA Physical Status. Be ACCURATE — do not over-classify. Most patients presenting for elective colonoscopy are ASA 1 or 2.

ASA DEFINITIONS:
- ASA 1: Healthy, no active medical problems
- ASA 2: Mild, well-controlled systemic disease — NO functional limitation.
  Examples (these are ALL ASA 2, not ASA 3):
  * Hypothyroidism on any thyroid medication (levothyroxine, NP Thyroid, Armour Thyroid, Synthroid) = ASA 2
  * Hypertension on medication (well-controlled) = ASA 2
  * Type 2 diabetes, A1c < 8, no end-organ damage = ASA 2
  * Mild obesity (BMI 30-39) = ASA 2
  * Hyperlipidemia on statin = ASA 2
  * GERD, anxiety, depression (well-controlled on medication) = ASA 2
  * History of cancer with no current active disease = ASA 2
  * Mild asthma (uses inhaler occasionally) = ASA 2
  * Current smoker = ASA 2
  * Social alcohol use — "social EtOH", "occasional alcohol", "social drinker", "1-2 drinks" = ASA 2 (NOT ASA 3)
  * Prior orthopedic surgery (knee, hip, shoulder) with no current issues = does NOT affect ASA
  * Single well-controlled chronic condition on medication = ASA 2

  IMPORTANT: "Social EtOH" or "social alcohol" means occasional social drinking = ASA 2. Only alcohol DEPENDENCE or ABUSE = ASA 3.

- ASA 3: Severe systemic disease WITH functional limitation or poor control.
  Examples (these must be genuinely severe):
  * Poorly controlled HTN or DM (A1c ≥ 8, uncontrolled BP)
  * Morbid obesity (BMI ≥ 40)
  * Implanted pacemaker or ICD
  * History of MI, CVA, or TIA within the past year
  * COPD requiring daily inhaler or home oxygen
  * ESRD on dialysis
  * Active hepatitis or cirrhosis
  * Alcohol dependence (not just social drinking)
  * Multiple poorly controlled conditions

- ASA 4: Life-threatening. Recent MI < 3 months, unstable angina, decompensated heart failure, severe valvular disease, active sepsis.

RULE: If a condition is described as "controlled," "well-controlled," or the patient is on a single medication managing it — that is ASA 2, not ASA 3. Do not upgrade to ASA 3 without a clear reason.

Patient History:
Past Medical History: {pmh}
Past Surgical History: {psh}
Social History: {sochx}
Current Medications: {medications}
Allergies: {allergies}

Respond ONLY with valid JSON:
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
        "pacemaker", "icd", "defibrillator",
        "poorly controlled", "uncontrolled",
        "morbid obesity", "bmi 40",
        "home oxygen", "oxygen dependent", "oxygen at home",
        "hepatitis", "cirrhosis",
        "alcohol dependence", "alcohol abuse",
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
