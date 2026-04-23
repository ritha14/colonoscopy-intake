"""Insurance type options and messages."""

INSURANCE_TYPES = {
    "traditional_medicare": {
        "label": "Medicare (Original / Traditional Medicare)",
        "message": "Dr. Belizaire works with Traditional Medicare. The office will confirm your coverage before scheduling.",
        "stop": False,
        "warning": False,
    },
    "commercial": {
        "label": "Commercial Insurance (PPO, HMO, or other)",
        "message": "Dr. Belizaire works with most commercial insurance plans. The office will be in touch before scheduling to confirm that your insurance will cover the procedure.",
        "stop": False,
        "warning": False,
    },
    "medicare_advantage": {
        "label": "Medicare Advantage (Humana, Aetna, AARP, WellCare, etc.)",
        "message": (
            "Please note: Dr. Belizaire is not in-network with Medicare Advantage plans. "
            "The office will be in touch before scheduling to discuss your options. "
            "If you have questions, call or text (832) 979-5670 and say: "
            "'I am interested in direct-to-colonoscopy and want to confirm my insurance will cover it.'"
        ),
        "stop": False,
        "warning": True,
    },
    "medicaid": {
        "label": "Medicaid (STAR, CHIP, Molina, Community Health Choice, etc.)",
        "message": (
            "Unfortunately, Dr. Belizaire is unable to see Medicaid patients. "
            "We are sorry we cannot assist you at this time. "
            "Please contact your primary care doctor for a referral to a Medicaid-participating provider."
        ),
        "stop": True,
        "warning": False,
    },
    "military": {
        "label": "Military / Tricare / VA / CHAMPVA",
        "message": "The office will be in touch before scheduling to confirm your coverage.",
        "stop": False,
        "warning": False,
    },
    "self_pay": {
        "label": "Self-Pay / No Insurance",
        "message": (
            "The surgeon fee is $600 cash, due before your procedure. "
            "Facility and anesthesia fees will be quoted separately prior to scheduling."
        ),
        "stop": False,
        "warning": False,
    },
}
