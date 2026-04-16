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
    "medicare": {
        "label": "Medicare",
        "result": "ELIGIBLE",
        "message": "Your Medicare can be used for the full procedure.",
        "status": "eligible",
        "pay_label": "Medicare — Fully Covered",
    },
    "ppo": {
        "label": "PPO",
        "result": "ELIGIBLE",
        "message": (
            "Because you have a PPO plan, your insurance can be used for this procedure. "
            "Our office will handle the out-of-network billing on your behalf."
        ),
        "status": "eligible",
        "pay_label": "PPO — Eligible",
    },
    "hmo": {
        "label": "HMO",
        "result": "CASH_PAY_SURGEON",
        "message": (
            "HMO plans typically do not cover out-of-network providers. "
            "You have two options: pay the surgeon fee of $600 cash "
            "(facility and anesthesia still bill through your insurance), "
            "or we can refer you to an in-network surgeon.\n\n"
            "If you believe this is incorrect or you'd like us to double-check your coverage, "
            "please call or text our office at (832) 979-5670 and say: "
            "\"I am interested in direct-to-colonoscopy and I want to make sure my insurance will cover it.\""
        ),
        "status": "cash_pay_surgeon",
        "pay_label": "HMO — Cash $600 or In-Network Referral",
    },
    "medicare_advantage": {
        "label": "Medicare Advantage",
        "result": "CASH_PAY_SURGEON",
        "message": (
            "Medicare Advantage plans are not accepted by Dr. Belizaire. "
            "You have two options: pay the surgeon fee of $600 cash "
            "(facility and anesthesia still bill through your insurance), "
            "or we can refer you to an in-network surgeon.\n\n"
            "If you believe this is incorrect or you'd like us to double-check your coverage, "
            "please call or text our office at (832) 979-5670 and say: "
            "\"I am interested in direct-to-colonoscopy and I want to make sure my insurance will cover it.\""
        ),
        "status": "cash_pay_surgeon",
        "pay_label": "Medicare Advantage — Cash $600 or In-Network Referral",
    },
    "medicaid": {
        "label": "Medicaid",
        "result": "NOT_ELIGIBLE",
        "message": (
            "Dr. Belizaire is unable to see Medicaid patients. "
            "We are sorry we cannot assist you at this time. "
            "Please contact your primary care doctor for a referral to a Medicaid-participating provider."
        ),
        "status": "ineligible_insurance",
        "pay_label": "Not Eligible",
    },
    "unknown": {
        "label": "Unknown / Not sure",
        "result": "OFFICE_CHECK",
        "message": (
            "No problem — our team will verify your insurance when they reach out to schedule. "
            "Please have your insurance card available when we call.\n\n"
            "You can also reach us first by calling or texting (832) 979-5670 and saying: "
            "\"I am interested in direct-to-colonoscopy and I want to make sure my insurance will cover it.\""
        ),
        "status": "pending_office_verification",
        "pay_label": "Pending Verification",
    },
    "self_pay": {
        "label": "Cash (no insurance)",
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
