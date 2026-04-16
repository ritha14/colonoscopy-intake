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

Dr. Belizaire (colorectal surgeon, Houston TX) needs to determine if this patient's insurance can be billed for an elective outpatient colonoscopy at an ambulatory surgery center.

Key facts about Dr. Belizaire's billing:
- IN-NETWORK with: Traditional Medicare (Part A/B only), Tricare
- OUT-OF-NETWORK with: all commercial insurance plans
- CANNOT ACCEPT: Medicaid or any Medicaid managed care plan
- For out-of-network commercial plans, she CAN get paid through:
  * Federal IDR (Independent Dispute Resolution, No Surprises Act) if the plan is SELF-FUNDED / ERISA
  * Gap Exception if the plan is FULLY-INSURED and state-regulated (TDI, Texas)
  * She CANNOT get paid through HMO plans (no out-of-network benefits)
  * She CANNOT bill Medicare Advantage plans

Analyze the insurance card image(s) provided. Look carefully for:
- Plan type: PPO, HMO, EPO, POS
- Funding: "Self-Funded", "Self-Insured", "ASO" (Administrative Services Only), "not subject to state insurance laws" → these mean ERISA/self-funded
- Medicare indicators: "Medicare Advantage", "MA Plan", specific MA plan names (Humana Gold Plus, AARP Medicare Complete, WellCare, Devoted, Clover, etc.)
- Medicaid indicators: "Medicaid", "STAR", "CHIP", "Community Health Choice", "Molina", "Superior Health Plan", "TMPPM"
- Tricare indicators: "Tricare", "Defense Health Agency"
- Group number format (can hint at self-funded)

Respond ONLY with valid JSON in this exact format:
{
  "carrier_name": "Blue Cross Blue Shield of Texas",
  "plan_name": "BlueChoice PPO",
  "plan_type": "PPO",
  "is_traditional_medicare": false,
  "is_medicare_advantage": false,
  "is_medicaid": false,
  "is_tricare": false,
  "is_self_funded": false,
  "is_hmo": false,
  "has_oon_benefits": true,
  "idr_eligible": true,
  "confidence": "high",
  "insurance_category": "ppo_oon",
  "card_notes": "Any notable text from the card relevant to billing",
  "reasoning": "2-3 sentence explanation of determination"
}

insurance_category must be exactly one of:
- traditional_medicare
- tricare
- ppo_oon       (PPO with out-of-network benefits — eligible via IDR or gap exception)
- hmo           (HMO — no out-of-network benefits — cash pay required)
- fully_funded  (fully-funded plan without OON benefits — cash pay required)
- medicare_advantage
- medicaid
- va_champva
- unknown       (cannot determine from card — needs manual verification)
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
