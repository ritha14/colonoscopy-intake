"""
Direct-to-Colonoscopy Intake & Scheduling System
Houston Community Surgical — Dr. Ritha Belizaire MD FACS FASCRS
"""
import re
import uuid
import sys
from datetime import datetime, date
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).parent))

from config import OFFICE_PHONE, SURGERY_CENTERS, YOUTUBE_VIDEO_ID, PRACTICE_NAME, DOCTOR_NAME
from utils.insurance import analyze_insurance, get_insurance_options, INSURANCE_TYPES
from utils.asa import classify_asa
from utils.pdf_generator import generate_referral_pdf
from utils.email_sender import send_emails
from utils.database import save_submission
from utils.card_analyzer import analyze_card

# ── Page config ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Houston Community Surgical — Colonoscopy Intake",
    page_icon="🏥",
    layout="centered",
    initial_sidebar_state="collapsed",
)

# ── CSS ───────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
  /* Progress bar color */
  .stProgress > div > div > div { background-color: #1a3a5c !important; }

  /* Colored message boxes */
  .hcs-info  { background:#e8f4fd; border-left:4px solid #2c5f8a; padding:12px 16px; border-radius:4px; margin:8px 0; }
  .hcs-warn  { background:#fff3cd; border-left:4px solid #e67e00; padding:12px 16px; border-radius:4px; margin:8px 0; }
  .hcs-ok    { background:#d4edda; border-left:4px solid #28a745; padding:12px 16px; border-radius:4px; margin:8px 0; }
  .hcs-err   { background:#f8d7da; border-left:4px solid #c0392b; padding:12px 16px; border-radius:4px; margin:8px 0; }

  /* Section headers */
  h3 { color: #1a3a5c !important; }

  /* Hide Streamlit branding */
  footer { visibility: hidden; }

  div[data-testid="stDecoration"] { display: none; }
</style>
""", unsafe_allow_html=True)

# ── Helpers ───────────────────────────────────────────────────────────────────

STEP_NAMES = {
    1: "Welcome & Demographics",
    2: "Chief Complaint & Symptoms",
    3: "Medical History",
    4: "Medications, Allergies & Screening",
    5: "Primary Care Doctor",
    6: "Insurance & ID",
    7: "Insurance Review",
    8: "Medical Safety Check",
    9: "Your Options",
    10: "Instruction Video",
    11: "Surgery Center",
    12: "Submitting…",
    13: "Request Sent",
}
TOTAL_STEPS = 11  # visible steps for progress bar


def _init():
    defaults = {
        "step": 1,
        "data": {},
        "ins_result": None,
        "asa_result": None,
        "card_analysis": None,
        "pdf_bytes": None,
        "uploaded_files": {},
        "show_age_warn": False,
        "submitted": False,
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v


def _go(step: int):
    st.session_state.step = step


def _rerun():
    st.rerun()


def _validate_phone(phone: str) -> bool:
    return len(re.sub(r"\D", "", phone)) == 10


def _validate_email(email: str) -> bool:
    return bool(re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", email))


def _parse_dob(raw: str):
    """Return (True, date_obj) or (False, error_message)."""
    raw = raw.strip()
    # Support M/D/YYYY as well as MM/DD/YYYY
    parts = raw.split("/")
    if len(parts) == 3:
        try:
            m, d, y = int(parts[0]), int(parts[1]), int(parts[2])
            dob = date(y, m, d)
            if dob >= date.today():
                return False, "Date of birth must be in the past."
            if dob.year < 1900:
                return False, "Please enter a valid year."
            return True, dob
        except (ValueError, TypeError):
            pass
    return False, "Please enter date of birth as MM/DD/YYYY (example: 01/15/1965)."


def _age(dob: date) -> int:
    today = date.today()
    return today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))


def _header():
    st.markdown(f"## {PRACTICE_NAME}")
    st.markdown(f"**{DOCTOR_NAME}** — Direct-to-Colonoscopy Intake")
    step = st.session_state.step
    if 1 <= step <= TOTAL_STEPS:
        st.progress((step - 1) / (TOTAL_STEPS - 1))
        st.caption(f"Step {step} of {TOTAL_STEPS} — {STEP_NAMES.get(step, '')}")
    st.divider()


def _box(kind: str, html: str):
    css = {"info": "hcs-info", "warn": "hcs-warn", "ok": "hcs-ok", "err": "hcs-err"}.get(kind, "hcs-info")
    st.markdown(f'<div class="{css}">{html}</div>', unsafe_allow_html=True)


def _nav_back(target: int, key: str):
    if st.button("← Back", key=key):
        _go(target)
        _rerun()


# ── Step 1: Welcome & Demographics ───────────────────────────────────────────
def step_1():
    st.markdown("### Welcome")
    _box("info", """
    <strong>Welcome to Houston Community Surgical — Dr. Ritha Belizaire's Direct-to-Colonoscopy Intake.</strong><br><br>
    This form will collect your medical history, verify your insurance, and determine if you are a candidate
    for direct scheduling.<br><br>
    <strong>All fields are required. Please answer honestly and completely.</strong>
    """)

    st.markdown("#### Your Information")
    d = st.session_state.data
    c1, c2 = st.columns(2)
    with c1:
        first = st.text_input("First Name *", value=d.get("first_name", ""))
    with c2:
        last = st.text_input("Last Name *", value=d.get("last_name", ""))
    dob_raw = st.text_input("Date of Birth (MM/DD/YYYY) *", value=d.get("dob", ""), placeholder="01/15/1965")
    c3, c4 = st.columns(2)
    with c3:
        phone = st.text_input("Phone Number *", value=d.get("phone", ""), placeholder="(555) 555-5555")
    with c4:
        email = st.text_input("Email Address *", value=d.get("email", ""), placeholder="you@example.com")

    # Age warning confirmation
    if st.session_state.show_age_warn:
        _box("warn", """
        <strong>⚠️ Please Note:</strong><br>
        If you are under the age of 45, your insurance is less likely to cover this procedure at 100%.
        You may have out-of-pocket costs. Please contact your insurance company if you have questions.
        """)
        if st.button("I understand — continue", key="age_ok"):
            st.session_state.show_age_warn = False
            _go(2)
            _rerun()
        return  # Wait for confirmation before showing Next button

    if st.button("Next →", type="primary", key="s1_next"):
        errors = []
        if not first.strip():
            errors.append("First name is required.")
        if not last.strip():
            errors.append("Last name is required.")

        dob_valid, dob_result = _parse_dob(dob_raw)
        if not dob_valid:
            errors.append(dob_result)

        if not phone.strip():
            errors.append("Phone number is required.")
        elif not _validate_phone(phone):
            errors.append("Please enter a valid 10-digit phone number.")

        if not email.strip():
            errors.append("Email address is required.")
        elif not _validate_email(email):
            errors.append("Please enter a valid email address.")

        if errors:
            for e in errors:
                st.error(e)
            return

        age = _age(dob_result)
        st.session_state.data.update({
            "first_name": first.strip(),
            "last_name": last.strip(),
            "dob": dob_raw.strip(),
            "phone": phone.strip(),
            "email": email.strip(),
            "age": age,
            "age_display": f"{age} years old",
        })

        if age < 45:
            st.session_state.show_age_warn = True
            _rerun()
        else:
            _go(2)
            _rerun()


# ── Step 2: Chief Complaint & HPI ────────────────────────────────────────────
def step_2():
    st.markdown("### Step 2: Why Are You Here Today?")
    st.caption("All questions are written in plain language.")

    d = st.session_state.data

    st.markdown("#### Chief Complaint")
    st.caption("The main reason you're here today. You may write 'None' if you have no specific complaint.")
    cc = st.text_area("Chief complaint *", value=d.get("chief_complaint", ""), height=80,
                       placeholder="Example: Routine screening colonoscopy. Or: None")

    st.markdown("#### Stomach or Intestinal Symptoms")
    st.caption("""
    We want to know about any new stomach or intestinal symptoms — nausea, vomiting, trouble keeping
    food down, unexpected weight loss, blood in your stool, changes in how often or how easily you go
    to the bathroom, or stomach pain.
    """)

    hpi_choice_prev = d.get("hpi_choice", "screening")
    hpi_idx = 1 if hpi_choice_prev == "symptoms" else 0

    hpi_choice = st.radio(
        "Symptom status *",
        options=["I just need a screening colonoscopy", "I have symptoms to describe"],
        index=hpi_idx,
        key="hpi_radio",
    )

    hpi_text = ""
    if hpi_choice == "I have symptoms to describe":
        hpi_text = st.text_area(
            "Describe your symptoms *",
            value=d.get("hpi_text", ""),
            height=120,
            placeholder="When did symptoms start? How often? Describe what you're experiencing.",
        )

    c1, c2 = st.columns([1, 5])
    with c1:
        _nav_back(1, "s2_back")
    with c2:
        if st.button("Next →", type="primary", key="s2_next"):
            errors = []
            if not cc.strip():
                errors.append("Chief complaint is required. Enter 'None' if you have no specific complaint.")
            if hpi_choice == "I have symptoms to describe" and not hpi_text.strip():
                errors.append("Please describe your symptoms, or select 'I just need a screening colonoscopy'.")
            if errors:
                for e in errors:
                    st.error(e)
                return
            final_hpi = hpi_text.strip() if hpi_choice == "I have symptoms to describe" else "Screening colonoscopy — no active symptoms"
            st.session_state.data.update({
                "chief_complaint": cc.strip(),
                "hpi_choice": "symptoms" if hpi_choice == "I have symptoms to describe" else "screening",
                "hpi_text": hpi_text.strip(),
                "hpi": final_hpi,
            })
            _go(3)
            _rerun()


# ── Step 3: Medical History ───────────────────────────────────────────────────
def step_3():
    st.markdown("### Step 3: Medical History")
    st.caption("Please answer each section. You may write **None** if it does not apply to you.")

    d = st.session_state.data

    st.markdown("#### Past Medical History (PMH)")
    st.caption("Anything you are currently being treated for, or were treated for more than 3 months at any point in your life. Any time you've been hospitalized.")
    pmh = st.text_area("Past Medical History *", value=d.get("pmh", ""), height=100,
                        placeholder="Example: High blood pressure, diabetes, hospitalized for pneumonia in 2018. Or: None")

    st.markdown("#### Past Surgical History (PSH)")
    st.caption("Any surgeries you've had in your lifetime.")
    psh = st.text_area("Past Surgical History *", value=d.get("psh", ""), height=80,
                        placeholder="Example: Appendectomy 1998, C-section 2005. Or: None")

    st.markdown("#### Social History")
    st.caption("Tobacco use, alcohol use, illicit drug use, employment or student status.")
    sochx = st.text_area("Social History *", value=d.get("sochx", ""), height=80,
                          placeholder="Example: Non-smoker, occasional alcohol, no drug use, works as nurse. Or: None")

    st.markdown("#### Family History (FHx)")
    st.caption("Any diseases or conditions that run in your family, especially colon cancer, other cancers, or digestive diseases.")
    fhx = st.text_area("Family History *", value=d.get("fhx", ""), height=80,
                        placeholder="Example: Father had colon cancer at age 60. Mother has diabetes. Or: None")

    c1, c2 = st.columns([1, 5])
    with c1:
        _nav_back(2, "s3_back")
    with c2:
        if st.button("Next →", type="primary", key="s3_next"):
            errors = []
            for label, val in [("Past Medical History", pmh), ("Past Surgical History", psh),
                                ("Social History", sochx), ("Family History", fhx)]:
                if not val.strip():
                    errors.append(f"{label} is required. Enter 'None' if it does not apply.")
            if errors:
                for e in errors:
                    st.error(e)
                return
            st.session_state.data.update({
                "pmh": pmh.strip(), "psh": psh.strip(),
                "sochx": sochx.strip(), "fhx": fhx.strip(),
            })
            _go(4)
            _rerun()


# ── Step 4: Medications, Allergies, Prior Screening ──────────────────────────
def step_4():
    st.markdown("### Step 4: Medications, Allergies & Prior Screening")
    st.caption("Please answer each section. You may write **None** if it does not apply.")

    d = st.session_state.data

    st.markdown("#### Current Medications")
    st.caption("All medications you currently take, including over-the-counter drugs and supplements.")
    meds = st.text_area("Medications *", value=d.get("medications", ""), height=100,
                         placeholder="Example: Lisinopril 10mg daily, aspirin 81mg, Vitamin D. Or: None")

    st.markdown("#### Allergies")
    st.caption("Any allergies to medications, foods, or latex, and what reaction you have.")
    allergies = st.text_area("Allergies *", value=d.get("allergies", ""), height=80,
                              placeholder="Example: Penicillin — hives. Sulfa — rash. Or: None")

    st.markdown("#### Previous Colorectal Cancer Screening")
    st.caption("Any prior colonoscopies, stool tests (like Cologuard or FIT), or other colon cancer screenings and what the results were.")
    screening = st.text_area("Prior Screening *", value=d.get("prior_screening", ""), height=80,
                              placeholder="Example: Colonoscopy 2018 — normal. Cologuard 2022 — negative. Or: None")

    c1, c2 = st.columns([1, 5])
    with c1:
        _nav_back(3, "s4_back")
    with c2:
        if st.button("Next →", type="primary", key="s4_next"):
            errors = []
            for label, val in [("Medications", meds), ("Allergies", allergies), ("Prior Screening", screening)]:
                if not val.strip():
                    errors.append(f"{label} is required. Enter 'None' if it does not apply.")
            if errors:
                for e in errors:
                    st.error(e)
                return
            st.session_state.data.update({
                "medications": meds.strip(),
                "allergies": allergies.strip(),
                "prior_screening": screening.strip(),
            })
            _go(5)
            _rerun()


# ── Step 5: PCP / Referring Doctor ───────────────────────────────────────────
def step_5():
    st.markdown("### Step 5: Primary Care or Referring Doctor")
    st.caption("Please provide the doctor who is referring you or your primary care physician.")

    d = st.session_state.data

    pcp_name = st.text_input("Doctor's Name *", value=d.get("pcp_name", ""), placeholder="Dr. Jane Smith")
    pcp_addr = st.text_area("Office Address *", value=d.get("pcp_address", ""), height=80,
                             placeholder="123 Main St, Houston, TX 77001")
    c1, c2 = st.columns(2)
    with c1:
        pcp_phone = st.text_input("Office Phone *", value=d.get("pcp_phone", ""), placeholder="(555) 555-5555")
    with c2:
        pcp_fax = st.text_input("Fax Number *", value=d.get("pcp_fax", ""),
                                 placeholder="(555) 555-5556 or Unknown")

    cn1, cn2 = st.columns([1, 5])
    with cn1:
        _nav_back(4, "s5_back")
    with cn2:
        if st.button("Next →", type="primary", key="s5_next"):
            errors = []
            if not pcp_name.strip():
                errors.append("Doctor's name is required.")
            if not pcp_addr.strip():
                errors.append("Office address is required.")
            if not pcp_phone.strip():
                errors.append("Office phone is required.")
            elif not _validate_phone(pcp_phone):
                errors.append("Please enter a valid 10-digit phone number for the doctor's office.")
            if not pcp_fax.strip():
                errors.append("Fax number is required. Enter 'Unknown' if you don't have it.")
            if errors:
                for e in errors:
                    st.error(e)
                return
            st.session_state.data.update({
                "pcp_name": pcp_name.strip(),
                "pcp_address": pcp_addr.strip(),
                "pcp_phone": pcp_phone.strip(),
                "pcp_fax": pcp_fax.strip(),
            })
            _go(6)
            _rerun()


# ── Step 6: Insurance & ID Upload ─────────────────────────────────────────────
def step_6():
    st.markdown("### Step 6: Insurance & ID")

    d = st.session_state.data
    uf = st.session_state.uploaded_files

    # Insurance or self-pay
    has_ins_prev = d.get("has_insurance", True)
    pay_choice = st.radio(
        "Do you have health insurance? *",
        ["Yes, I have insurance", "No, I am self-pay (no insurance)"],
        index=0 if has_ins_prev else 1,
    )
    has_insurance = pay_choice.startswith("Yes")

    policy_holder = "self"
    policy_holder_name = ""
    policy_holder_dob = ""

    if has_insurance:
        st.markdown("#### Insurance Card")
        st.caption("Upload the front and back of your insurance card.")

        ins_front = st.file_uploader("Insurance Card — FRONT *", type=["jpg", "jpeg", "png", "pdf"], key="uf_ins_front")
        if ins_front:
            uf["ins_front_bytes"] = ins_front.getvalue()
            uf["ins_front_name"] = ins_front.name
        if "ins_front_bytes" in uf:
            st.success(f"✅ Front uploaded: {uf.get('ins_front_name', 'file')}")

        ins_back = st.file_uploader("Insurance Card — BACK *", type=["jpg", "jpeg", "png", "pdf"], key="uf_ins_back")
        if ins_back:
            uf["ins_back_bytes"] = ins_back.getvalue()
            uf["ins_back_name"] = ins_back.name
        if "ins_back_bytes" in uf:
            st.success(f"✅ Back uploaded: {uf.get('ins_back_name', 'file')}")

        st.markdown("#### Policy Holder")
        ph_prev = d.get("policy_holder", "self")
        ph_choice = st.radio(
            "Are you the policy holder on this insurance? *",
            ["Yes, I am the policy holder", "No, someone else holds the policy"],
            index=0 if ph_prev == "self" else 1,
        )
        if ph_choice.startswith("No"):
            policy_holder = "other"
            ph1, ph2 = st.columns(2)
            with ph1:
                policy_holder_name = st.text_input("Policy holder's full name *", value=d.get("policy_holder_name", ""))
            with ph2:
                policy_holder_dob = st.text_input("Policy holder's date of birth (MM/DD/YYYY) *", value=d.get("policy_holder_dob", ""))
        else:
            policy_holder = "self"

    st.markdown("#### Driver's License / Government-Issued ID")
    st.caption("Please upload a photo or scan of your driver's license or government-issued ID.")
    dl = st.file_uploader("Driver's License / ID *", type=["jpg", "jpeg", "png", "pdf"], key="uf_dl")
    if dl:
        uf["dl_bytes"] = dl.getvalue()
        uf["dl_name"] = dl.name
    if "dl_bytes" in uf:
        st.success(f"✅ ID uploaded: {uf.get('dl_name', 'file')}")

    cn1, cn2 = st.columns([1, 5])
    with cn1:
        _nav_back(5, "s6_back")
    with cn2:
        if st.button("Next →", type="primary", key="s6_next"):
            errors = []
            if has_insurance:
                if policy_holder == "other":
                    if not policy_holder_name.strip():
                        errors.append("Policy holder name is required.")
                    if not policy_holder_dob.strip():
                        errors.append("Policy holder date of birth is required.")
                    elif not _parse_dob(policy_holder_dob)[0]:
                        errors.append("Please enter a valid policy holder date of birth as MM/DD/YYYY.")
                if "ins_front_bytes" not in uf:
                    errors.append("Please upload the FRONT of your insurance card.")
                if "ins_back_bytes" not in uf:
                    errors.append("Please upload the BACK of your insurance card.")
            if "dl_bytes" not in uf:
                errors.append("Please upload your driver's license or government-issued ID.")
            if errors:
                for e in errors:
                    st.error(e)
                return

            st.session_state.data.update({
                "has_insurance": has_insurance,
                "policy_holder": policy_holder,
                "policy_holder_name": policy_holder_name.strip(),
                "policy_holder_dob": policy_holder_dob.strip(),
                "id_docs_note": "Uploaded and emailed to office",
            })
            st.session_state.ins_result = None
            _go(7)
            _rerun()


# ── Step 7: Insurance Type & Notice ───────────────────────────────────────────
def step_7():
    st.markdown("### Step 7: Insurance Information")

    d = st.session_state.data
    has_insurance = d.get("has_insurance", True)

    # Self-pay — no need to select insurance type
    if not has_insurance:
        result = analyze_insurance("self_pay")
        _box("info", f"{result['message']}")
        cn1, cn2 = st.columns([1, 5])
        with cn1:
            if st.button("← Back", key="s7_back_sp"):
                _go(6)
                _rerun()
        with cn2:
            if st.button("Next →", type="primary", key="s7_next_sp"):
                st.session_state.data.update({
                    "insurance_type": "self_pay",
                    "insurance_type_label": "Self-Pay",
                    "insurance_carrier": "N/A",
                    "insurance_result": result["result"],
                    "insurance_message": result["message"],
                    "pay_label": result["pay_label"],
                    "payment_type": result["status"],
                })
                _go(8)
                _rerun()
        return

    # Select insurance type
    opts = [(k, v["label"]) for k, v in INSURANCE_TYPES.items() if k != "self_pay"]
    opt_keys = [k for k, _ in opts]
    opt_labels = [lbl for _, lbl in opts]

    prev_type = d.get("insurance_type", "")
    def_idx = opt_keys.index(prev_type) if prev_type in opt_keys else 0

    sel_idx = st.selectbox(
        "What type of insurance do you have? *",
        range(len(opt_labels)),
        format_func=lambda i: opt_labels[i],
        index=def_idx,
        key="s7_ins_type",
    )
    selected_key = opt_keys[sel_idx]
    result = analyze_insurance(selected_key)
    result_code = result["result"]

    # Show appropriate notice
    st.markdown("---")
    if result_code == "NOT_ELIGIBLE":
        _box("err", f"<strong>❌ Unable to Schedule</strong><br><br>{result['message']}")
    elif result_code == "MA_WARNING":
        _box("warn", f"<strong>⚠️ Please Note</strong><br><br>{result['message']}")
    elif result_code == "CASH_PAY_FULL":
        _box("info", f"{result['message']}")
    else:
        _box("ok", f"<strong>✅ Got it!</strong><br><br>{result['message']}")

    cn1, cn2 = st.columns([1, 5])
    with cn1:
        if st.button("← Back", key="s7_back"):
            _go(6)
            _rerun()
    with cn2:
        btn_label = "Submit & Exit" if result_code == "NOT_ELIGIBLE" else "Next →"
        if st.button(btn_label, type="primary", key="s7_next"):
            ins_label = INSURANCE_TYPES.get(selected_key, {}).get("label", "")
            st.session_state.data.update({
                "insurance_type": selected_key,
                "insurance_type_label": ins_label,
                "insurance_result": result_code,
                "insurance_message": result["message"],
                "pay_label": result["pay_label"],
                "payment_type": result["status"],
            })
            if result_code == "NOT_ELIGIBLE":
                d["status"] = "ineligible_insurance"
                d["submission_date"] = datetime.now().strftime("%m/%d/%Y %I:%M %p")
                d["submission_id"] = str(uuid.uuid4())[:8].upper()
                save_submission(d)
                _go(14)
                _rerun()
            else:
                _go(8)
                _rerun()


# ── Step 8: ASA Classification ────────────────────────────────────────────────
def step_8():
    st.markdown("### Step 8: Medical Safety Check")
    st.caption("We are reviewing your medical history to confirm that a colonoscopy is safe for you at an outpatient surgery center.")

    d = st.session_state.data

    if st.session_state.asa_result is None:
        with st.spinner("Reviewing your medical history… this may take 10–15 seconds."):
            asa = classify_asa(
                pmh=d.get("pmh", ""),
                psh=d.get("psh", ""),
                sochx=d.get("sochx", ""),
                medications=d.get("medications", ""),
                allergies=d.get("allergies", ""),
            )
            st.session_state.asa_result = asa
            st.session_state.data.update({
                "asa_class": asa["asa_class"],
                "asa_reasoning": asa["reasoning"],
                "asa_key_factors": asa.get("key_factors", []),
                "is_candidate": asa["asa_class"] <= 2,
            })

    asa = st.session_state.asa_result
    is_candidate = asa["asa_class"] <= 2

    if is_candidate:
        _box("ok", f"""
        <strong>✅ You Are Cleared for Direct Scheduling</strong><br><br>
        Based on your medical history, you are an appropriate candidate for an outpatient colonoscopy
        without a prior office visit (ASA Class {asa['asa_class']}).<br><br>
        <em>{asa['reasoning']}</em>
        """)

        cn1, cn2 = st.columns([1, 5])
        with cn1:
            if st.button("← Back", key="s8_back"):
                st.session_state.asa_result = None
                _go(7)
                _rerun()
        with cn2:
            if st.button("Next →", type="primary", key="s8_next"):
                _go(9)
                _rerun()

    else:
        _box("warn", f"""
        <strong>⚠️ Pre-Procedure Office Visit Required</strong><br><br>
        Based on your medical history (ASA Class {asa['asa_class']}), we need to meet with you
        in the office before scheduling your procedure. This is for your safety.<br><br>
        <em>{asa['reasoning']}</em><br><br>
        <strong>Please call us to schedule a pre-procedure visit: {OFFICE_PHONE}</strong>
        """)

        col_a, col_b = st.columns(2)
        with col_a:
            if st.button("← Review My Medical History", key="s8_back_asa"):
                st.session_state.asa_result = None
                _go(3)
                _rerun()
        with col_b:
            if st.button("Submit My Info & Call the Office", type="primary", key="s8_submit_call"):
                d["status"] = "requires_office_visit"
                d["patient_decision"] = "Will call office for pre-procedure visit"
                d["submission_date"] = datetime.now().strftime("%m/%d/%Y %I:%M %p")
                d["submission_id"] = str(uuid.uuid4())[:8].upper()
                try:
                    pdf = generate_referral_pdf(d)
                    st.session_state.pdf_bytes = pdf
                    save_submission(d)
                    send_emails(d, pdf, st.session_state.uploaded_files)
                except Exception:
                    pass
                _go(13)
                _rerun()


# ── Step 9: Decision Pathways ─────────────────────────────────────────────────
def step_9():
    st.markdown("### Step 9: How Would You Like to Proceed?")

    d = st.session_state.data
    result_code = d.get("insurance_result", "")

    # Self-pay only — ask if they want to proceed with $600 cash
    if result_code == "CASH_PAY_FULL":
        _box("info", d.get("insurance_message", ""))
        st.markdown("#### How would you like to proceed?")
        decision = st.radio("Choose one:", [
            "Proceed — I understand the fees and want to schedule",
            "I am not ready to proceed at this time",
        ], key="s9_dec_cash")

        cn1, cn2 = st.columns([1, 5])
        with cn1:
            _nav_back(8, "s9_back_cash")
        with cn2:
            if st.button("Next →", type="primary", key="s9_next_cash"):
                if "not ready" in decision:
                    d["patient_decision"] = "Chose not to proceed"
                    d["status"] = "chose_not_to_proceed"
                    d["submission_date"] = datetime.now().strftime("%m/%d/%Y %I:%M %p")
                    d["submission_id"] = str(uuid.uuid4())[:8].upper()
                    save_submission(d)
                    _box("info", f"No problem. If you change your mind, call us at {OFFICE_PHONE} or complete this form again.")
                else:
                    d["patient_decision"] = "Proceeding with self-pay"
                    _go(10)
                    _rerun()

    else:
        # All other insurance types — office will verify, just proceed
        d["patient_decision"] = "Proceeding — office will verify insurance before scheduling"
        _go(10)
        _rerun()


# ── Step 10: Instruction Video ────────────────────────────────────────────────
def step_10():
    st.markdown("### Step 10: Colonoscopy Instruction Video")

    _box("info", """
    Please watch the following video before completing your intake. It covers what to expect
    during your procedure, how to get ready, and answers common questions.
    """)

    vid_id = YOUTUBE_VIDEO_ID
    if vid_id and vid_id.strip():
        st.video(f"https://www.youtube.com/watch?v={vid_id.strip()}")
    else:
        _box("warn", """
        📹 <strong>Video coming soon.</strong><br>
        The instruction video link is not yet available. Our office will share it with you when scheduling.
        In the meantime, feel free to call <strong>(832) 979-5670</strong> if you have questions about preparation.
        """)

    prev_watched = st.session_state.data.get("video_watched", False)
    vid_status = st.radio(
        "Video status: *",
        ["Yes, I watched the video", "I'll watch it later"],
        index=0 if prev_watched else 1,
        key="s10_vid",
    )

    cn1, cn2 = st.columns([1, 5])
    with cn1:
        _nav_back(9, "s10_back")
    with cn2:
        if st.button("Next →", type="primary", key="s10_next"):
            st.session_state.data["video_watched"] = vid_status.startswith("Yes")
            _go(11)
            _rerun()


# ── Step 11: Location Preference ──────────────────────────────────────────────
def step_11():
    st.markdown("### Step 11: Preferred Surgery Center")
    st.caption("Dr. Belizaire performs colonoscopies at two locations. Please choose your preference.")

    d = st.session_state.data
    prev_loc = d.get("location_preference", "")

    try:
        loc_idx = SURGERY_CENTERS.index(prev_loc)
    except ValueError:
        loc_idx = 0

    location = st.radio("Choose your preferred location: *", SURGERY_CENTERS, index=loc_idx)

    if "9230 Katy Fwy" in location:
        _box("info", "📍 <strong>Memorial Houston Surgery Center</strong><br>9230 Katy Fwy #601, Houston, TX 77055<br><em>Near I-10 / Memorial City</em>")
    else:
        _box("info", "📍 <strong>Kirby Glen Surgery Center</strong><br>2457 S Braeswood Blvd, Houston, TX 77030<br><em>Near the Texas Medical Center / Rice University</em>")

    cn1, cn2 = st.columns([1, 5])
    with cn1:
        _nav_back(10, "s11_back")
    with cn2:
        if st.button("Submit My Request →", type="primary", key="s11_next"):
            st.session_state.data["location_preference"] = location
            _go(12)
            _rerun()


# ── Step 12: Submit ───────────────────────────────────────────────────────────
def step_12():
    if st.session_state.submitted:
        _go(13)
        _rerun()
        return

    st.markdown("### Submitting Your Request…")

    d = st.session_state.data
    d["submission_date"] = datetime.now().strftime("%m/%d/%Y %I:%M %p")
    d["submitted_at"] = datetime.now().isoformat()
    d["submission_id"] = str(uuid.uuid4())[:8].upper()
    d["status"] = "completed"

    prog = st.progress(0, text="Generating your referral document…")

    try:
        pdf_bytes = generate_referral_pdf(d)
        st.session_state.pdf_bytes = pdf_bytes
        prog.progress(40, text="Saving your record…")
    except Exception as e:
        st.error(f"Could not generate referral PDF: {e}")
        st.info("Please call the office directly to complete your scheduling.")
        return

    try:
        save_submission(d)
        prog.progress(65, text="Sending confirmation emails…")
    except Exception as e:
        st.warning(f"Database note: {e}")

    try:
        office_ok, patient_ok = send_emails(d, pdf_bytes, st.session_state.uploaded_files)
        prog.progress(100, text="Done!")
        if not office_ok:
            st.warning("Office notification could not be sent automatically. Please call (832) 979-5670 to confirm receipt.")
        if not patient_ok:
            st.warning("Confirmation email could not be sent to your email. Please download your referral PDF below.")
    except Exception as e:
        st.warning(f"Email note: {e}")

    st.session_state.submitted = True
    _go(13)
    _rerun()


# ── Step 13: Success ──────────────────────────────────────────────────────────
def step_13():
    st.markdown("### ✅ Your Request Has Been Received")

    d = st.session_state.data

    _box("ok", f"""
    <strong>Your colonoscopy intake has been sent to Dr. Belizaire's office.</strong><br><br>
    <strong>Tamika or Kaye will be in touch with you within 1–2 business days to schedule your procedure.</strong><br><br>
    Submission ID: <strong>{d.get('submission_id', 'N/A')}</strong><br>
    Submitted: {d.get('submission_date', '')}
    """)

    st.divider()

    # Download referral PDF
    if st.session_state.pdf_bytes:
        st.markdown("#### Download Your Referral Summary")
        st.download_button(
            label="📄 Download Referral PDF",
            data=st.session_state.pdf_bytes,
            file_name=f"Colonoscopy_Referral_{d.get('last_name', '')}_{d.get('first_name', '')}.pdf",
            mime="application/pdf",
        )
    st.divider()

    # Prep instructions
    st.markdown("#### Bowel Preparation Instructions")
    _box("info", """
    Please download and read your MiraLAX bowel preparation instructions carefully.
    These explain what to eat and drink the day before your procedure,
    and how to take your prep medication.<br><br>
    <strong>Do not eat solid food after midnight the day before your procedure.</strong>
    """)

    prep_path = Path(__file__).parent / "assets" / "miralax_prep.pdf"
    if prep_path.exists():
        with open(prep_path, "rb") as f:
            st.download_button(
                label="📋 Download MiraLAX Prep Instructions",
                data=f.read(),
                file_name="MiraLAX_Colonoscopy_Prep_Instructions.pdf",
                mime="application/pdf",
            )
    else:
        st.info("Prep instruction PDF will be provided by the office when your procedure is scheduled.")

    st.divider()
    st.markdown(f"""
    **Questions?** Call **{OFFICE_PHONE}** or email **info@houstoncommunitysurgical.com**

    Thank you for choosing Houston Community Surgical and Dr. Belizaire!
    """)

    if st.button("Start a New Submission", key="restart_13"):
        for k in list(st.session_state.keys()):
            del st.session_state[k]
        _rerun()


# ── Step 14: End (ineligible / declined) ─────────────────────────────────────
def step_14():
    st.markdown("### Thank You")
    _box("info", f"""
    Thank you for completing our intake form.<br><br>
    If you have questions, please call us at <strong>{OFFICE_PHONE}</strong> or
    email <strong>info@houstoncommunitysurgical.com</strong>.
    """)
    if st.button("Start Over", key="restart_14"):
        for k in list(st.session_state.keys()):
            del st.session_state[k]
        _rerun()


# ── Main ──────────────────────────────────────────────────────────────────────
def main():
    _init()
    _header()

    step = st.session_state.step
    {
        1: step_1, 2: step_2, 3: step_3, 4: step_4,
        5: step_5, 6: step_6, 7: step_7, 8: step_8,
        9: step_9, 10: step_10, 11: step_11,
        12: step_12, 13: step_13, 14: step_14,
    }.get(step, step_1)()


if __name__ == "__main__":
    main()
