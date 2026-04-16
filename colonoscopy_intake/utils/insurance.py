"""
Insurance eligibility classification based on Dr. Belizaire's network status.

In-network: Traditional Medicare, Tricare only.
Cannot see: Medicaid.
All commercial plans: out-of-network.
"""

INSURANCE_TYPES: dict[str, dict] = {
    "traditional_medicare": {
        "label": "Traditional Medicare (Original Medicare, Part A/B — NOT Medicare Advantage)",
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
    "erisa_self_funded": {
        "label": "Self-funded employer plan (large employer, federal ERISA — often says 'self-funded' on back of card)",
        "result": "ELIGIBLE",
        "message": (
            "Your insurance can be used for the full procedure. "
            "As a self-funded/ERISA plan, out-of-network reimbursement may be pursued "
            "through the federal Independent Dispute Resolution process."
        ),
        "status": "eligible",
        "pay_label": "Federal IDR Eligible",
    },
    "gap_exception": {
        "label": "Fully-insured commercial plan (TX state-regulated, TDI — gap exception eligible)",
        "result": "ELIGIBLE",
        "message": (
            "Your insurance can be used for the full procedure. "
            "Our office will file for a gap exception on your behalf."
        ),
        "status": "eligible",
        "pay_label": "Gap Exception Eligible",
    },
    "medicare_advantage": {
        "label": "Medicare Advantage (Medicare HMO, Medicare PPO, or any MA plan — has 'Medicare Advantage' or 'MA' on card)",
        "result": "CASH_PAY_SURGEON",
        "message": (
            "Facility, anesthesia, and lab fees will be billed through your insurance. "
            "The surgeon fee is $600 cash, due before your procedure."
        ),
        "status": "cash_pay_surgeon",
        "pay_label": "Cash — Surgeon Fee $600",
    },
    "commercial_ppo_hmo": {
        "label": "Commercial insurance — PPO or HMO (Blue Cross, Aetna, Cigna, United, Humana, Oscar, etc.)",
        "result": "CASH_PAY_SURGEON",
        "message": (
            "Facility, anesthesia, and lab fees will be billed through your insurance. "
            "The surgeon fee is $600 cash, due before your procedure."
        ),
        "status": "cash_pay_surgeon",
        "pay_label": "Cash — Surgeon Fee $600",
    },
    "medicaid": {
        "label": "Medicaid or Medicaid Managed Care (STAR, CHIP, Molina, Community Health Choice, etc.)",
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
