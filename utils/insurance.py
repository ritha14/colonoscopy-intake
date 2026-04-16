"""
Insurance eligibility classification based on Dr. Belizaire's network status.

In-network: Traditional Medicare, Tricare only.
Cannot see: Medicaid.

Key rule for commercial plans:
  - PPO with out-of-network benefits → ELIGIBLE (office handles IDR/gap exception)
  - HMO (no OON benefits) → CASH PAY $600 surgeon or refer in-network
  - Fully-funded plan → CASH PAY $600 surgeon or refer in-network
  - Medicare Advantage → CASH PAY $600 surgeon or refer in-network
"""

INSURANCE_TYPES: dict[str, dict] = {
    "traditional_medicare": {
        "label": "Traditional Medicare (Original Medicare Part A/B — NOT Medicare Advantage)",
        "result": "ELIGIBLE",
        "message": "Your insurance can be used for the full procedure.",
        "status": "eligible",
        "pay_label": "In-Network / Fully Covered",
    },
    "tricare": {
        "label": "Tricare (military health coverage)",
        "result": "ELIGIBLE",
        "message": "Your insurance can be used for the full procedure.",
        "status": "eligible",
        "pay_label": "In-Network / Fully Covered",
    },
    "ppo_oon": {
        "label": "PPO plan with out-of-network benefits (Blue Cross PPO, Aetna PPO, Cigna PPO, United PPO, Humana PPO, etc.)",
        "result": "ELIGIBLE",
        "message": (
            "Because you have a PPO plan with out-of-network benefits, "
            "your insurance can be used for the full procedure. "
            "Our office will handle the out-of-network billing on your behalf "
            "through the No Surprises Act / Federal IDR or gap exception process."
        ),
        "status": "eligible",
        "pay_label": "PPO — Eligible via No Surprises Act / IDR",
    },
    "hmo": {
        "label": "HMO plan (Blue Cross HMO, Aetna HMO, Cigna HMO, United HMO, Humana HMO, etc.) — no out-of-network coverage",
        "result": "CASH_PAY_SURGEON",
        "message": (
            "HMO plans do not cover out-of-network providers. "
            "You have two options: pay the surgeon fee of $600 cash (facility and anesthesia bill through your insurance), "
            "or we can help refer you to an in-network surgeon."
        ),
        "status": "cash_pay_surgeon",
        "pay_label": "HMO — Cash $600 Surgeon or In-Network Referral",
    },
    "fully_funded": {
        "label": "Fully-funded commercial plan (employer plan that does NOT allow out-of-network care)",
        "result": "CASH_PAY_SURGEON",
        "message": (
            "Fully-funded plans that do not allow out-of-network care cannot be billed for this procedure. "
            "You have two options: pay the surgeon fee of $600 cash (facility and anesthesia bill through your insurance), "
            "or we can help refer you to an in-network surgeon."
        ),
        "status": "cash_pay_surgeon",
        "pay_label": "Fully-Funded Plan — Cash $600 Surgeon or In-Network Referral",
    },
    "medicare_advantage": {
        "label": "Medicare Advantage (Medicare HMO or PPO — card says 'Medicare Advantage' or plan name like Humana Gold, AARP, WellCare, etc.)",
        "result": "CASH_PAY_SURGEON",
        "message": (
            "Medicare Advantage plans are not accepted by Dr. Belizaire. "
            "You have two options: pay the surgeon fee of $600 cash (facility and anesthesia bill through your insurance), "
            "or we can help refer you to an in-network surgeon."
        ),
        "status": "cash_pay_surgeon",
        "pay_label": "Medicare Advantage — Cash $600 Surgeon or In-Network Referral",
    },
    "medicaid": {
        "label": "Medicaid or Medicaid Managed Care (STAR, CHIP, Molina, Community Health Choice, Superior, etc.)",
        "result": "NOT_ELIGIBLE",
        "message": (
            "Dr. Belizaire is unable to see Medicaid patients. "
            "We are sorry we cannot assist you at this time. "
            "Please contact your primary care doctor for a referral to a Medicaid-participating provider."
        ),
        "status": "ineligible_insurance",
        "pay_label": "Not Eligible",
    },
    "va_champva": {
        "label": "VA / CHAMPVA / Other government plan",
        "result": "OFFICE_CHECK",
        "message": (
            "Your plan may require manual verification. "
            "Our team will confirm your coverage when scheduling."
        ),
        "status": "pending_office_verification",
        "pay_label": "Pending Verification",
    },
    "self_pay": {
        "label": "No insurance — Self-Pay",
        "result": "CASH_PAY_FULL",
        "message": (
            "The surgeon fee is $600 cash, due before your procedure. "
            "Facility and anesthesia fees will be quoted separately prior to scheduling."
        ),
        "status": "cash_pay_full",
        "pay_label": "Full Cash Pay",
    },
}


def get_insurance_options() -> list[tuple[str, str]]:
    """Return list of (key, label) pairs for UI display."""
    return [(k, v["label"]) for k, v in INSURANCE_TYPES.items()]


def analyze_insurance(insurance_type_key: str) -> dict:
    """Return the eligibility result dict for the given insurance type key."""
    if insurance_type_key in INSURANCE_TYPES:
        return INSURANCE_TYPES[insurance_type_key]
    return {
        "result": "OFFICE_CHECK",
        "message": "We need to verify your insurance. Our team will contact you.",
        "status": "pending_office_verification",
        "pay_label": "Pending Verification",
    }
