"""
Insurance handling — simplified.

The office verifies insurance before scheduling for everyone.
Only hard stop: Medicaid (not accepted).
Warning only: Medicare Advantage (not in-network, office discusses options).
Everyone else: office will confirm coverage before scheduling.
"""

INSURANCE_TYPES: dict[str, dict] = {
    "traditional_medicare": {
        "label": "Medicare (Original / Traditional Medicare)",
        "result": "OFFICE_VERIFY",
        "message": (
            "Dr. Belizaire works with Traditional Medicare. "
            "The office will be in touch before scheduling to confirm your coverage."
        ),
        "status": "pending_office_verification",
        "pay_label": "Traditional Medicare",
    },
    "commercial": {
        "label": "Commercial Insurance (PPO, HMO, or other employer/marketplace plan)",
        "result": "OFFICE_VERIFY",
        "message": (
            "Dr. Belizaire works with most commercial insurance plans. "
            "The office will be in touch before scheduling to confirm that your insurance will cover the procedure."
        ),
        "status": "pending_office_verification",
        "pay_label": "Commercial Insurance",
    },
    "medicare_advantage": {
        "label": "Medicare Advantage (a Medicare plan through a private insurer — Humana, Aetna, AARP, WellCare, etc.)",
        "result": "MA_WARNING",
        "message": (
            "Please note: Dr. Belizaire is not in-network with Medicare Advantage plans. "
            "The office will be in touch before scheduling to discuss your options."
        ),
        "status": "pending_office_verification",
        "pay_label": "Medicare Advantage — Office Will Follow Up",
    },
    "medicaid": {
        "label": "Medicaid (including STAR, CHIP, and Medicaid managed care plans)",
        "result": "NOT_ELIGIBLE",
        "message": (
            "Unfortunately, Dr. Belizaire is unable to see Medicaid patients. "
            "We are sorry we cannot assist you at this time. "
            "Please contact your primary care doctor for a referral to a Medicaid-participating provider."
        ),
        "status": "ineligible_insurance",
        "pay_label": "Not Eligible",
    },
    "military": {
        "label": "Military / Tricare / VA / CHAMPVA",
        "result": "OFFICE_VERIFY",
        "message": (
            "The office will be in touch before scheduling to confirm your coverage."
        ),
        "status": "pending_office_verification",
        "pay_label": "Military / Tricare",
    },
    "self_pay": {
        "label": "Self-Pay (no insurance)",
        "result": "CASH_PAY_FULL",
        "message": (
            "The surgeon fee is $600 cash, due before your procedure. "
            "Facility and anesthesia fees will be quoted separately prior to scheduling."
        ),
        "status": "cash_pay_full",
        "pay_label": "Self-Pay",
    },
}


def get_insurance_options() -> list[tuple[str, str]]:
    """Return list of (key, label) pairs for UI display."""
    return [(k, v["label"]) for k, v in INSURANCE_TYPES.items()]


def analyze_insurance(insurance_type_key: str) -> dict:
    """Return the result dict for the given insurance type key."""
    if insurance_type_key in INSURANCE_TYPES:
        return INSURANCE_TYPES[insurance_type_key]
    return {
        "result": "OFFICE_VERIFY",
        "message": "The office will be in touch to confirm your coverage before scheduling.",
        "status": "pending_office_verification",
        "pay_label": "Pending Verification",
    }
