"""
Insurance card analyzer using Claude Vision.

Reads the uploaded insurance card (front + back) and determines:
- Carrier name and plan type
- Whether the plan is eligible for Federal IDR (No Surprises Act)
- Whether it's a government plan (Medicare, Medicaid, Tricare)
- Overall eligibility category for Dr. Belizaire's practice
"""
import base64
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from config import ANTHROPIC_API_KEY

SUPPORTED_TYPES = {
    "image/jpeg": ["jpg", "jpeg"],
    "image/png": ["png"],
    "image/gif": ["gif"],
    "image/webp": ["webp"],
}


def _media_type(filename: str) -> str | None:
    ext = Path(filename).suffix.lower().lstrip(".")
    for mt, exts in SUPPORTED_TYPES.items():
        if ext in exts:
            return mt
    return None


ANALYSIS_PROMPT = """You are an expert medical billing specialist helping a colorectal surgeon's office in Texas.

Dr. Belizaire performs colonoscopies and bills commercial insurance. Her rule is simple:
- PPO plans with out-of-network benefits = ELIGIBLE (she bills via No Surprises Act / IDR or gap exception)
- HMO plans = CASH PAY (no out-of-network coverage)
- Medicare Advantage = CASH PAY (not accepted)
- Traditional Medicare (Part A/B) = ELIGIBLE (in-network)
- Tricare = ELIGIBLE (in-network)
- Medicaid = NOT ELIGIBLE

IMPORTANT DEFAULTS:
- If the card shows PPO → always classify as ppo_oon (eligible) UNLESS you see clear HMO or Medicare Advantage indicators
- Most commercial PPO cards do NOT say "self-funded" on them — that's fine, assume PPO = eligible
- EPO plans: classify as hmo (no out-of-network benefits)
- POS plans: classify as ppo_oon if it shows out-of-network coverage language, otherwise hmo

Look for:
- Plan type label: PPO, HMO, EPO, POS
- Medicare Advantage markers: "Medicare Advantage", "MA", specific MA brand names (Humana Gold Plus, AARP Medicare Complete, WellCare, Devoted Health, Clover, Alignment Health, etc.)
- Medicaid markers: "Medicaid", "STAR", "CHIP", "Molina", "Community Health Choice", "Superior Health Plan", "TMPPM", "Texas Medicaid"
- Tricare markers: "Tricare", "Defense Health Agency", "DEERS"
- Traditional Medicare: "Medicare" card issued by CMS/federal government, NOT an MA plan

Respond ONLY with valid JSON in this exact format:
{
  "carrier_name": "Blue Cross Blue Shield of Texas",
  "plan_name": "BlueChoice PPO",
  "plan_type": "PPO",
  "is_traditional_medicare": false,
  "is_medicare_advantage": false,
  "is_medicaid": false,
  "is_tricare": false,
  "is_hmo": false,
  "confidence": "high",
  "insurance_category": "ppo_oon",
  "card_notes": "Any notable text from the card relevant to billing",
  "reasoning": "1-2 sentence explanation"
}

insurance_category must be exactly one of:
- traditional_medicare  (Original Medicare Part A/B issued by CMS)
- tricare               (military coverage)
- ppo_oon               (PPO — eligible via No Surprises Act / IDR)
- hmo                   (HMO or EPO — no out-of-network benefits)
- medicare_advantage    (any MA plan)
- medicaid              (Medicaid or Medicaid managed care)
- va_champva            (VA or CHAMPVA)
- unknown               (truly cannot determine)

When in doubt between ppo_oon and unknown, choose ppo_oon if you can see "PPO" anywhere on the card.
"""


def analyze_card(
    front_bytes: bytes,
    front_name: str,
    back_bytes: bytes = None,
    back_name: str = None,
) -> dict:
    """
    Analyze insurance card image(s) using Claude Vision.
    Returns analysis dict, or fallback dict if analysis fails.
    """
    if not ANTHROPIC_API_KEY:
        return _fallback("No API key configured.")

    try:
        import anthropic
        client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

        content = []

        # Front of card
        front_mt = _media_type(front_name or "card.jpg")
        if front_mt:
            content.append({
                "type": "text",
                "text": "Insurance card — FRONT:"
            })
            content.append({
                "type": "image",
                "source": {
                    "type": "base64",
                    "media_type": front_mt,
                    "data": base64.standard_b64encode(front_bytes).decode("utf-8"),
                },
            })
        else:
            return _fallback(f"Unsupported front image format: {front_name}")

        # Back of card (optional but recommended)
        if back_bytes and back_name:
            back_mt = _media_type(back_name)
            if back_mt:
                content.append({
                    "type": "text",
                    "text": "Insurance card — BACK:"
                })
                content.append({
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": back_mt,
                        "data": base64.standard_b64encode(back_bytes).decode("utf-8"),
                    },
                })

        content.append({"type": "text", "text": ANALYSIS_PROMPT})

        response = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=600,
            messages=[{"role": "user", "content": content}],
        )

        raw = response.content[0].text.strip()
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        result = json.loads(raw.strip())
        result["analyzed"] = True
        return result

    except Exception as e:
        return _fallback(f"Analysis error: {type(e).__name__}: {e}")


def _fallback(reason: str) -> dict:
    return {
        "analyzed": False,
        "fallback_reason": reason,
        "insurance_category": "unknown",
        "carrier_name": "",
        "plan_type": "",
        "confidence": "none",
        "reasoning": reason,
    }
