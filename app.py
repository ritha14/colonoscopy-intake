"""
Direct-to-Colonoscopy Intake
Houston Community Surgical — Dr. Ritha Belizaire MD FACS FASCRS
"""
import re, uuid, sys
from datetime import datetime, date
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).parent))

from config import OFFICE_PHONE, SURGERY_CENTERS, HOSPITAL_CENTERS, YOUTUBE_VIDEO_ID, BMI_CONDITION
from utils.asa import ASA3_CONDITIONS
from utils.pdf_generator import generate_referral_pdf
from utils.email_sender import send_emails
from utils.database import save_submission

# ── Page setup ────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Houston Community Surgical — Colonoscopy Intake",
    page_icon="🏥",
    layout="centered",
    initial_sidebar_state="collapsed",
)

st.markdown('<link href="https://fonts.googleapis.com/css2?family=Poppins:wght@400;500;600;700&display=swap" rel="stylesheet">', unsafe_allow_html=True)

st.markdown("""
<style>
/* ── Force light mode — prevents phone dark mode from inverting colors ── */
:root { color-scheme: light only; }
html, body, .stApp, [data-testid="stAppViewContainer"] {
    background-color: #ffffff !important;
    color: #111111 !important;
}

/* ── Global font ── */
html, body, .stApp, [data-testid="stAppViewContainer"],
p, li, span, div, label, input, textarea, button {
    font-family: 'Poppins', 'Helvetica Neue', Arial, sans-serif !important;
}

/* ── Desktop font sizes ── */
.stMarkdown p, .stMarkdown li {
    font-size: 19px !important;
    line-height: 1.75 !important;
    color: #111111 !important;
}
.stTextInput input, .stTextArea textarea {
    font-size: 19px !important;
    color: #111 !important;
    background: #ffffff !important;
    border: 1.5px solid #b0b8c1 !important;
    border-radius: 6px !important;
}
.stRadio label span p, .stCheckbox label span p {
    font-size: 19px !important;
    color: #111 !important;
}
div[data-testid="stButton"] > button[kind="primary"] {
    font-size: 19px !important;
    padding: 0.6rem 2rem !important;
    font-weight: 700 !important;
    background: #1a3a5c !important;
    color: #ffffff !important;
    border: none !important;
    border-radius: 8px !important;
    min-height: 52px !important;
    width: 100% !important;
}
div[data-testid="stButton"] > button[kind="primary"]:hover {
    background: #2c5f8a !important;
    color: #ffffff !important;
}
div[data-testid="stButton"] > button[kind="secondary"] {
    font-size: 17px !important;
    border-radius: 8px !important;
    color: #1a3a5c !important;
    background: #ffffff !important;
}
h3 { font-size: 24px !important; color: #1a3a5c !important; font-weight: 700 !important; }
.stProgress > div > div > div { background-color: #1a3a5c !important; }

/* ── Colored boxes — explicit colors so dark mode can't invert ── */
.box-ok   { background:#d4edda !important; border-left:5px solid #28a745; padding:16px 20px; border-radius:6px; margin:12px 0; font-size:19px; line-height:1.75; color:#1a3a5c !important; }
.box-warn { background:#fff3cd !important; border-left:5px solid #e67e00; padding:16px 20px; border-radius:6px; margin:12px 0; font-size:19px; line-height:1.75; color:#5a3e00 !important; }
.box-err  { background:#f8d7da !important; border-left:5px solid #c0392b; padding:16px 20px; border-radius:6px; margin:12px 0; font-size:19px; line-height:1.75; color:#5a0a0a !important; }
.box-info { background:#e8f4fd !important; border-left:5px solid #2c5f8a; padding:16px 20px; border-radius:6px; margin:12px 0; font-size:19px; line-height:1.75; color:#1a3a5c !important; }
.box-ok *, .box-warn *, .box-err *, .box-info * { color: inherit !important; }

small, .stCaption { font-size: 15px !important; color: #555555 !important; }

/* ── Mobile adjustments ── */
@media (max-width: 640px) {
    .stMarkdown p, .stMarkdown li { font-size: 16px !important; }
    .stTextInput input, .stTextArea textarea { font-size: 16px !important; }
    .stRadio label span p, .stCheckbox label span p { font-size: 16px !important; }
    div[data-testid="stButton"] > button[kind="primary"] { font-size: 17px !important; }
    h3 { font-size: 20px !important; }
    .box-ok, .box-warn, .box-err, .box-info { font-size: 16px !important; padding: 12px 14px; }
}

footer { visibility: hidden; }
</style>
""", unsafe_allow_html=True)

# ── Helpers ───────────────────────────────────────────────────────────────────
def box(kind, html):
    st.markdown(f'<div class="box-{kind}">{html}</div>', unsafe_allow_html=True)

def go(n):
    st.session_state.step = n

def err(msg):
    st.error(msg)

def phone_ok(p):
    return len(re.sub(r"\D", "", p)) == 10

def email_ok(e):
    return bool(re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", e))

def parse_dob(s):
    s = s.strip()
    parts = s.split("/")
    if len(parts) == 3:
        try:
            dob = date(int(parts[2]), int(parts[0]), int(parts[1]))
            if dob >= date.today(): return None, "Date of birth must be in the past."
            if dob.year < 1900: return None, "Please enter a valid year."
            return dob, None
        except: pass
    return None, "Please use MM/DD/YYYY format — example: 01/15/1965"

def age_from(dob):
    t = date.today()
    return t.year - dob.year - ((t.month, t.day) < (dob.month, dob.day))

def back_btn(target, key):
    if st.button("← Back", key=key):
        go(target); st.rerun()

def init():
    if "step" not in st.session_state:
        st.session_state.step = 1
    if "d" not in st.session_state:
        st.session_state.d = {}
    if "uf" not in st.session_state:
        st.session_state.uf = {}
    if "pdf" not in st.session_state:
        st.session_state.pdf = None
    if "age_warn" not in st.session_state:
        st.session_state.age_warn = False
    if "done" not in st.session_state:
        st.session_state.done = False

STEPS = 10
STEP_NAMES = {
    1:"Welcome & Demographics", 2:"Chief Complaint & Symptoms",
    3:"Medical History", 4:"Medications, Allergies & Screening",
    5:"Primary Care Doctor", 6:"Insurance",
    7:"Medical Safety Check", 8:"Instruction Video",
    9:"Surgery Center", 10:"Submitting",
    11:"Complete", 12:"Pre-Procedure Visit Required",
}

def header():
    logo = Path(__file__).parent / "assets" / "logo.png"
    if logo.exists():
        col = st.columns([1, 6, 1])[1]
        with col:
            st.image(str(logo), use_container_width=True)
    else:
        st.markdown("## Houston Community Surgical")
    n = st.session_state.step
    if 1 <= n <= STEPS:
        st.progress((n-1)/(STEPS-1))
        st.caption(f"Step {n} of {STEPS} — {STEP_NAMES.get(n,'')}")
    st.divider()

# ── Step 1: Demographics ──────────────────────────────────────────────────────
def s1():
    st.markdown("### Welcome")
    box("info", """
    <strong>Welcome to Dr. Ritha Belizaire's Direct-to-Colonoscopy Intake.</strong><br><br>
    This form collects your medical history, verifies your insurance, and determines if you are
    a candidate for direct scheduling. <strong>All fields are required.</strong>
    """)

    d = st.session_state.d
    c1, c2 = st.columns(2)
    with c1: first = st.text_input("First Name *", value=d.get("first_name",""))
    with c2: last  = st.text_input("Last Name *",  value=d.get("last_name",""))
    dob_raw = st.text_input("Date of Birth (MM/DD/YYYY) *", value=d.get("dob",""), placeholder="01/15/1965")
    c3, c4 = st.columns(2)
    with c3: phone = st.text_input("Phone Number *", value=d.get("phone",""), placeholder="(555) 555-5555")
    with c4: email = st.text_input("Email Address *", value=d.get("email",""), placeholder="you@example.com")

    if st.session_state.age_warn:
        box("warn", """
        <strong>⚠️ Please Note:</strong> If you are under 45, your insurance is less likely to cover
        this procedure at 100%. You may have out-of-pocket costs.
        """)
        if st.button("I understand — continue", key="age_ok"):
            st.session_state.age_warn = False
            go(2); st.rerun()
        return

    not_robot = st.checkbox("I confirm I am a real person completing this form for myself or a patient. *", key="not_robot")

    if st.button("Next →", type="primary", key="s1"):
        errs = []
        if not first.strip(): errs.append("First name is required.")
        if not last.strip():  errs.append("Last name is required.")
        dob, dob_err = parse_dob(dob_raw)
        if dob_err: errs.append(dob_err)
        if not phone.strip(): errs.append("Phone number is required.")
        elif not phone_ok(phone): errs.append("Please enter a valid 10-digit phone number.")
        if not email.strip(): errs.append("Email address is required.")
        elif not email_ok(email): errs.append("Please enter a valid email address.")
        if not not_robot: errs.append("Please confirm you are a real person before continuing.")
        for e in errs: st.error(e)
        if errs: return
        a = age_from(dob)
        st.session_state.d.update({
            "first_name": first.strip(), "last_name": last.strip(),
            "dob": dob_raw.strip(), "phone": phone.strip(), "email": email.strip(),
            "age": a, "age_display": f"{a} years old",
        })
        if a < 45:
            st.session_state.age_warn = True; st.rerun()
        else:
            go(2); st.rerun()

# ── Step 2: Chief Complaint & HPI ────────────────────────────────────────────
def s2():
    st.markdown("### Step 2: Why Are You Here Today?")
    d = st.session_state.d

    st.markdown("#### Chief Complaint")
    st.caption("The main reason for your visit. You may write 'None' if you have no specific complaint.")
    cc = st.text_area("Chief complaint *", value=d.get("chief_complaint",""), height=80,
                      placeholder="Example: Routine screening. Or: None")

    st.markdown("#### Symptoms")
    st.caption("Any new nausea, vomiting, unexplained weight loss, blood in stool, changes in bowel habits, or stomach pain.")
    hpi_idx = 1 if d.get("hpi_choice") == "symptoms" else 0
    choice = st.radio("Do you have symptoms to describe? *",
                      ["I just need a screening colonoscopy", "I have symptoms to describe"],
                      index=hpi_idx, key="hpi_r")
    hpi_text = ""
    if choice == "I have symptoms to describe":
        hpi_text = st.text_area("Describe your symptoms *", value=d.get("hpi_text",""), height=120,
                                placeholder="When did they start? How often? How severe?")

    c1, c2 = st.columns([1,5])
    with c1: back_btn(1, "s2b")
    with c2:
        if st.button("Next →", type="primary", key="s2"):
            errs = []
            if not cc.strip(): errs.append("Chief complaint is required. Write 'None' if none.")
            if choice == "I have symptoms to describe" and not hpi_text.strip():
                errs.append("Please describe your symptoms.")
            for e in errs: st.error(e)
            if errs: return
            hpi = hpi_text.strip() if choice == "I have symptoms to describe" else "Screening — no active symptoms"
            st.session_state.d.update({
                "chief_complaint": cc.strip(),
                "hpi_choice": "symptoms" if choice == "I have symptoms to describe" else "screening",
                "hpi_text": hpi_text.strip(), "hpi": hpi,
            })
            go(3); st.rerun()

# ── Step 3: Medical History ───────────────────────────────────────────────────
def s3():
    st.markdown("### Step 3: Medical History")
    st.caption("Write **None** if something does not apply to you.")
    d = st.session_state.d

    st.markdown("#### Past Medical History")
    st.caption("Anything you are currently being treated for, or were treated for more than 3 months. Any hospitalizations.")
    pmh = st.text_area("Past Medical History *", value=d.get("pmh",""), height=100,
                       placeholder="Example: Hypertension, hypothyroidism, hospitalized 2018 for pneumonia. Or: None")

    st.markdown("#### Past Surgical History")
    st.caption("Any surgeries you have had in your lifetime.")
    psh = st.text_area("Past Surgical History *", value=d.get("psh",""), height=80,
                       placeholder="Example: Knee surgery 2015, appendectomy 1998. Or: None")

    st.markdown("#### Social History")
    st.caption("Tobacco use, alcohol use, drug use, employment status.")
    sochx = st.text_area("Social History *", value=d.get("sochx",""), height=80,
                         placeholder="Example: Non-smoker, social alcohol use, no drug use, works as teacher. Or: None")

    st.markdown("#### Family History")
    st.caption("Diseases that run in your family, especially colon cancer, other cancers, or digestive diseases.")
    fhx = st.text_area("Family History *", value=d.get("fhx",""), height=80,
                       placeholder="Example: Father had colon cancer at 60. Or: None")

    c1, c2 = st.columns([1,5])
    with c1: back_btn(2, "s3b")
    with c2:
        if st.button("Next →", type="primary", key="s3"):
            errs = []
            for label, val in [("Past Medical History", pmh), ("Past Surgical History", psh),
                                ("Social History", sochx), ("Family History", fhx)]:
                if not val.strip(): errs.append(f"{label} is required. Write 'None' if it does not apply.")
            for e in errs: st.error(e)
            if errs: return
            st.session_state.d.update({"pmh": pmh.strip(), "psh": psh.strip(),
                                       "sochx": sochx.strip(), "fhx": fhx.strip()})
            go(4); st.rerun()

# ── Step 4: Medications, Allergies, Prior Screening ──────────────────────────
def s4():
    st.markdown("### Step 4: Medications, Allergies & Prior Screening")
    st.caption("Write **None** if something does not apply.")
    d = st.session_state.d

    st.markdown("#### Current Medications")
    st.caption("All medications including over-the-counter drugs and supplements.")
    meds = st.text_area("Medications *", value=d.get("medications",""), height=100,
                        placeholder="Example: Lisinopril 10mg, aspirin 81mg, Vitamin D, NP Thyroid. Or: None")

    st.markdown("#### Important Medication Questions")
    st.caption("Please answer all three questions. These affect how we prepare you for your procedure.")

    glp1_idx = 1 if d.get("glp1") == "yes" else 0
    glp1 = st.radio(
        "Do you take any GLP-1 medications? (semaglutide [Wegovy/Ozempic], tirzepatide [Zepbound/Mounjaro], liraglutide [Victoza/Saxenda], or any other GLP-1) *",
        ["No", "Yes"], index=glp1_idx, key="glp1_r"
    )
    if glp1 == "Yes":
        box("warn", "⚠️ <strong>GLP-1 Notice:</strong> You will need to stop your GLP-1 medication <strong>1 week before your procedure.</strong> If it has not been stopped in time, the surgery center may cancel your procedure.")

    bt_idx = 1 if d.get("blood_thinners") == "yes" else 0
    blood_thinners = st.radio(
        "Do you take any blood thinners other than a baby aspirin? (e.g., Coumadin/warfarin, Lovenox, Xarelto, Eliquis, etc.) *",
        ["No", "Yes"], index=bt_idx, key="bt_r"
    )
    if blood_thinners == "Yes":
        box("warn", "⚠️ <strong>Blood Thinner Notice:</strong> Patients on blood thinners need to speak with Dr. Belizaire before scheduling. You will not be able to go direct — our office will discuss your options with you.")

    ins_idx = 1 if d.get("injectable_insulin") == "yes" else 0
    injectable_insulin = st.radio(
        "Do you take injectable insulin (not insulin pills)? *",
        ["No", "Yes"], index=ins_idx, key="ins_r"
    )
    if injectable_insulin == "Yes":
        box("info", "📋 <strong>Insulin users:</strong> Your prep instructions include specific guidance on what to do with your insulin before the procedure. Please read those instructions carefully when you receive them.")

    st.markdown("#### Allergies")
    st.caption("Allergies to medications, foods, or latex, and your reaction.")
    allg = st.text_area("Allergies *", value=d.get("allergies",""), height=80,
                        placeholder="Example: Penicillin — hives. Or: None")

    st.markdown("#### Previous Colorectal Screening")
    st.caption("Prior colonoscopies, Cologuard, FIT tests, and results.")
    scrn = st.text_area("Prior Screening *", value=d.get("prior_screening",""), height=80,
                        placeholder="Example: Colonoscopy 2018 — normal. Or: None")

    c1, c2 = st.columns([1,5])
    with c1: back_btn(3, "s4b")
    with c2:
        if st.button("Next →", type="primary", key="s4"):
            errs = []
            for label, val in [("Medications", meds), ("Allergies", allg), ("Prior Screening", scrn)]:
                if not val.strip(): errs.append(f"{label} is required. Write 'None' if it does not apply.")
            for e in errs: st.error(e)
            if errs: return
            st.session_state.d.update({
                "medications": meds.strip(),
                "allergies": allg.strip(),
                "prior_screening": scrn.strip(),
                "glp1": glp1.lower(),
                "blood_thinners": blood_thinners.lower(),
                "injectable_insulin": injectable_insulin.lower(),
            })
            go(5); st.rerun()

# ── Step 5: PCP ───────────────────────────────────────────────────────────────
def s5():
    st.markdown("### Step 5: Primary Care or Referring Doctor")
    d = st.session_state.d

    pcp_name = st.text_input("Doctor's Name *", value=d.get("pcp_name",""), placeholder="Dr. Jane Smith")
    pcp_addr = st.text_area("Office Address *", value=d.get("pcp_address",""), height=80,
                            placeholder="123 Main St, Houston, TX 77001")
    c1, c2 = st.columns(2)
    with c1: pcp_ph  = st.text_input("Office Phone *", value=d.get("pcp_phone",""), placeholder="(555) 555-5555")
    with c2: pcp_fax = st.text_input("Fax Number *",   value=d.get("pcp_fax",""),   placeholder="(555) 555-5556 or Unknown")

    cn1, cn2 = st.columns([1,5])
    with cn1: back_btn(4, "s5b")
    with cn2:
        if st.button("Next →", type="primary", key="s5"):
            errs = []
            if not pcp_name.strip(): errs.append("Doctor's name is required.")
            if not pcp_addr.strip(): errs.append("Office address is required.")
            if not pcp_ph.strip(): errs.append("Office phone is required.")
            elif not phone_ok(pcp_ph): errs.append("Please enter a valid 10-digit phone number.")
            if not pcp_fax.strip(): errs.append("Fax is required. Write 'Unknown' if you don't have it.")
            for e in errs: st.error(e)
            if errs: return
            st.session_state.d.update({"pcp_name": pcp_name.strip(), "pcp_address": pcp_addr.strip(),
                                       "pcp_phone": pcp_ph.strip(), "pcp_fax": pcp_fax.strip()})
            go(6); st.rerun()

# ── Step 6: Insurance & ID ────────────────────────────────────────────────────
def s6():
    st.markdown("### Step 6: Insurance & ID")
    d = st.session_state.d
    uf = st.session_state.uf

    box("info", """
    <strong>Insurance Verification</strong><br><br>
    Please upload your insurance card and a photo ID below.
    We will check with your insurance company to confirm that your procedure will be covered
    <strong>before we schedule anything.</strong><br><br>
    If there is anything out of pocket, we will let you know up front —
    and if your insurance will not cover it, we can refer you to an in-network provider so you always have options.
    """)

    st.markdown("#### Insurance Card")
    st.caption("Take a photo or scan of the front and back of your insurance card.")

    f = st.file_uploader("Insurance Card — FRONT *", type=["jpg","jpeg","png","pdf"], key="ins_f")
    if f:
        uf["ins_front_bytes"] = f.getvalue(); uf["ins_front_name"] = f.name
    if "ins_front_bytes" in uf:
        st.success(f"✅ Front uploaded: {uf.get('ins_front_name','file')}")

    b = st.file_uploader("Insurance Card — BACK *", type=["jpg","jpeg","png","pdf"], key="ins_b")
    if b:
        uf["ins_back_bytes"] = b.getvalue(); uf["ins_back_name"] = b.name
    if "ins_back_bytes" in uf:
        st.success(f"✅ Back uploaded: {uf.get('ins_back_name','file')}")

    st.markdown("#### Photo ID")
    st.caption("Upload a photo of your driver's license or government-issued ID.")
    dl = st.file_uploader("Driver's License / Photo ID *", type=["jpg","jpeg","png","pdf"], key="dl_f")
    if dl:
        uf["dl_bytes"] = dl.getvalue(); uf["dl_name"] = dl.name
    if "dl_bytes" in uf:
        st.success(f"✅ ID uploaded: {uf.get('dl_name','file')}")

    box("ok", "✅ <strong>No surprises.</strong> We confirm your coverage first, then we schedule your procedure.")

    cn1, cn2 = st.columns([1,5])
    with cn1: back_btn(5, "s6b")
    with cn2:
        if st.button("Next →", type="primary", key="s6n"):
            errs = []
            if "ins_front_bytes" not in uf: errs.append("Please upload the FRONT of your insurance card.")
            if "ins_back_bytes"  not in uf: errs.append("Please upload the BACK of your insurance card.")
            if "dl_bytes"        not in uf: errs.append("Please upload your driver's license or photo ID.")
            for e in errs: st.error(e)
            if errs: return
            d.update({
                "insurance_message": "Office will verify coverage before scheduling",
                "insurance_result": "PENDING",
                "id_docs_note": "Insurance card + photo ID uploaded and emailed to office",
            })
            go(7); st.rerun()


# ── Step 7: Medical Safety Check ─────────────────────────────────────────────
def s7():
    st.markdown("### Step 7: Medical Safety Check")

    box("info", """
    <strong>These questions are about serious medical conditions only.</strong><br><br>
    Common, well-managed conditions like <strong>hypothyroidism, controlled blood pressure,
    or controlled diabetes</strong> are <em>not</em> on this list and do not need to be checked.<br><br>
    Only check a box if it <strong>exactly</strong> matches your current situation.
    """)

    st.caption("Check any of the following that apply to you. Leave unchecked if they do not apply.")

    prior = st.session_state.d.get("asa_checked", [])
    checked = []
    for i, condition in enumerate(ASA3_CONDITIONS):
        if st.checkbox(condition, value=(condition in prior), key=f"asa_{i}"):
            checked.append(condition)

    st.markdown("---")
    none_checked = st.checkbox(
        "None of these apply to me",
        value=("none" in prior),
        key="asa_none",
    )

    c1, c2 = st.columns([1,5])
    with c1: back_btn(6, "s7b")
    with c2:
        if st.button("Next →", type="primary", key="s7n"):
            if not checked and not none_checked:
                st.error("Please check any that apply, or select 'None of these apply to me'.")
                return

            bmi_flagged = BMI_CONDITION in checked
            other_flagged = [c for c in checked if c != BMI_CONDITION]
            blood_thinner_flagged = st.session_state.d.get("blood_thinners") == "yes"
            needs_office = len(other_flagged) > 0 or blood_thinner_flagged
            bmi_only = bmi_flagged and not needs_office
            is_candidate = (none_checked and len(checked) == 0) or bmi_only

            all_checked = checked + (["none"] if none_checked else [])
            st.session_state.d.update({
                "asa_checked": all_checked,
                "asa_flagged": checked,
                "is_candidate": is_candidate,
                "bmi_only": bmi_only,
                "asa_class": 2 if is_candidate else 3,
                "asa_reasoning": (
                    "No high-risk conditions reported." if not checked
                    else f"Patient reported: {'; '.join(checked)}"
                ),
            })

            if needs_office:
                st.session_state.d["status"] = "requires_office_visit"
                st.session_state.d["patient_decision"] = "Will call office for pre-procedure visit"
                st.session_state.d["submission_date"] = datetime.now().strftime("%m/%d/%Y %I:%M %p")
                st.session_state.d["submission_id"] = str(uuid.uuid4())[:8].upper()
                try:
                    pdf = generate_referral_pdf(st.session_state.d)
                    st.session_state.pdf = pdf
                    save_submission(st.session_state.d)
                    send_emails(st.session_state.d, pdf, st.session_state.uf)
                except Exception: pass
                go(12); st.rerun()
            else:
                go(8); st.rerun()


# ── Step 8: Instruction Video ─────────────────────────────────────────────────
def s8():
    st.markdown("### Step 8: Colonoscopy Instruction Video")
    box("info", "Please watch the following video before completing your intake. It covers what to expect and how to prepare.")

    vid = YOUTUBE_VIDEO_ID
    if vid and vid.strip():
        st.video(f"https://www.youtube.com/watch?v={vid.strip()}")
    else:
        box("warn", "📹 <strong>Video coming soon.</strong> Our office will share the link when scheduling. Call or text (832) 979-5670 with any questions.")

    watched = st.radio("Video status: *",
                       ["Yes, I watched the video", "I'll watch it later"],
                       index=0 if st.session_state.d.get("video_watched") else 1,
                       key="s8_vid")

    c1, c2 = st.columns([1,5])
    with c1: back_btn(7, "s8b")
    with c2:
        if st.button("Next →", type="primary", key="s8n"):
            st.session_state.d["video_watched"] = watched.startswith("Yes")
            go(9); st.rerun()


# ── Step 9: Surgery Center / Hospital ────────────────────────────────────────
def s9():
    d = st.session_state.d
    bmi_only = d.get("bmi_only", False)

    if bmi_only:
        st.markdown("### Step 9: Preferred Hospital")
        st.caption("Dr. Belizaire performs colonoscopies at two hospital locations.")
        locations = HOSPITAL_CENTERS
        label = "Choose your preferred hospital: *"
        detail_map = {
            "Memorial Hermann": ("📍 <strong>Memorial Hermann Greater Heights Hospital</strong><br>"
                                 "1635 N Loop W, Houston, TX 77008<br><em>Near I-610 / Greater Heights</em>"),
            "Houston Methodist": ("📍 <strong>Houston Methodist Hospital</strong><br>"
                                  "6565 Fannin St, Houston, TX 77030<br><em>Texas Medical Center</em>"),
        }
    else:
        st.markdown("### Step 9: Preferred Surgery Center")
        st.caption("Dr. Belizaire performs colonoscopies at two locations.")
        locations = SURGERY_CENTERS
        label = "Choose your preferred location: *"
        detail_map = {
            "Katy Fwy": ("📍 <strong>Memorial Houston Surgery Center</strong><br>"
                         "9230 Katy Fwy #601, Houston, TX 77055<br><em>Near I-10 / Memorial City</em>"),
            "Braeswood": ("📍 <strong>Kirby Glen Surgery Center</strong><br>"
                          "2457 S Braeswood Blvd, Houston, TX 77030<br><em>Near the Texas Medical Center</em>"),
        }

    prev = d.get("location_preference", "")
    try: idx = locations.index(prev)
    except: idx = 0

    loc = st.radio(label, locations, index=idx)

    for keyword, detail_html in detail_map.items():
        if keyword in loc:
            box("info", detail_html)
            break

    c1, c2 = st.columns([1,5])
    with c1: back_btn(8, "s9b")
    with c2:
        if st.button("Submit My Request →", type="primary", key="s9n"):
            st.session_state.d["location_preference"] = loc
            go(10); st.rerun()


# ── Step 10: Submit ───────────────────────────────────────────────────────────
def s10():
    if st.session_state.done:
        go(11); st.rerun(); return

    st.markdown("### Submitting Your Request…")
    d = st.session_state.d
    d["submission_date"] = datetime.now().strftime("%m/%d/%Y %I:%M %p")
    d["submitted_at"]    = datetime.now().isoformat()
    d["submission_id"]   = str(uuid.uuid4())[:8].upper()
    d["status"]          = "completed"
    d["patient_decision"] = "Direct scheduling through intake form"

    prog = st.progress(0, text="Generating referral document…")
    try:
        pdf = generate_referral_pdf(d)
        st.session_state.pdf = pdf
        prog.progress(40, text="Saving your record…")
    except Exception as e:
        st.error(f"Could not generate PDF: {e}")
        st.info(f"Please call the office at {OFFICE_PHONE}.")
        return

    try:
        save_submission(d)
        prog.progress(65, text="Sending confirmation emails…")
    except Exception: pass

    try:
        ok_office, ok_patient = send_emails(d, pdf, st.session_state.uf)
        prog.progress(100, text="Done!")
        if not ok_office:
            st.warning("Office notification email could not be sent. Please call (832) 979-5670 to confirm receipt.")
        if not ok_patient:
            st.warning("Confirmation email could not be sent to the patient.")
    except Exception as e:
        st.error(f"Email error: {e}")
        st.stop()

    st.session_state.done = True
    go(11); st.rerun()


# ── Step 11: Success ──────────────────────────────────────────────────────────
def s11():
    st.markdown("### ✅ Your Request Has Been Received")
    d = st.session_state.d

    box("ok", f"""
    <strong>Your intake has been sent to Dr. Belizaire's office.</strong><br><br>
    <strong>Tamika or Kaye will be in touch within 1–2 business days to schedule your procedure.</strong><br><br>
    Submission ID: <strong>{d.get('submission_id','N/A')}</strong><br>
    Submitted: {d.get('submission_date','')}
    """)

    st.divider()
    if st.session_state.pdf:
        st.markdown("#### Download Your Referral Summary")
        st.download_button("📄 Download Referral PDF", data=st.session_state.pdf,
                           file_name=f"Referral_{d.get('last_name','')}_{d.get('first_name','')}.pdf",
                           mime="application/pdf")

    if d.get("glp1") == "yes":
        box("warn", """
        ⚠️ <strong>GLP-1 Reminder:</strong> You indicated that you take a GLP-1 medication (Wegovy, Ozempic, Zepbound, Mounjaro, Victoza, Saxenda, or similar).<br><br>
        <strong>You must stop your GLP-1 medication 1 week before your procedure.</strong>
        If it has not been stopped, the surgery center may cancel your procedure on the day of your appointment.
        Our office will confirm this with you when we contact you to schedule.
        """)

    if d.get("injectable_insulin") == "yes":
        box("info", """
        💉 <strong>Insulin Reminder:</strong> You indicated that you take injectable insulin.
        Your prep instructions include specific guidance on what to do with your insulin before the procedure.
        Please read those instructions carefully and follow them.
        """)

    st.markdown("#### Bowel Preparation Instructions")
    box("info", """
    Please download and read your MiraLAX prep instructions carefully.
    <strong>Do not eat solid food after midnight the night before your procedure.</strong>
    """)
    prep = Path(__file__).parent / "assets" / "miralax_prep.pdf"
    if prep.exists():
        st.download_button("📋 Download MiraLAX Prep Instructions", data=prep.read_bytes(),
                           file_name="MiraLAX_Prep_Instructions.pdf", mime="application/pdf")
    else:
        st.info("Prep instructions will be provided by the office when your procedure is scheduled.")

    st.divider()
    st.markdown(f"**Questions?** Call or text **{OFFICE_PHONE}** or email **info@houstoncommunitysurgical.com**")
    if st.button("Start a New Submission", key="restart"):
        for k in list(st.session_state.keys()): del st.session_state[k]
        st.rerun()


# ── Step 12: Pre-Procedure Office Visit Required ──────────────────────────────
def s12():
    st.markdown("### Your Information Has Been Received")
    d = st.session_state.d
    if d.get("blood_thinners") == "yes":
        reason = (
            "Because you are on a blood thinner, Dr. Belizaire needs to speak with you "
            "directly before your procedure can be scheduled. This is to make sure your "
            "blood thinner is managed safely around the time of the procedure."
        )
    else:
        reason = (
            "Based on your medical history, Dr. Belizaire needs to meet with you in the "
            "office before scheduling your procedure. This is standard practice to make sure "
            "your procedure is as safe as possible for you."
        )
    box("warn", f"""
    <strong>⚠️ You Cannot Be Scheduled Directly Online</strong><br><br>
    {reason}<br><br>
    Please call or text us at <strong>{OFFICE_PHONE}</strong> and our staff (Tamika or Kaye) will be happy to assist you.<br><br>
    Your intake information has already been sent to the office.
    """)
    if d.get("submission_id"):
        st.caption(f"Submission ID: {d.get('submission_id')} — {d.get('submission_date','')}")
    st.markdown(f"**Questions?** Call or text **{OFFICE_PHONE}** or email **info@houstoncommunitysurgical.com**")
    if st.button("Start Over", key="restart12"):
        for k in list(st.session_state.keys()): del st.session_state[k]
        st.rerun()


# ── Main ──────────────────────────────────────────────────────────────────────
def main():
    init()
    header()
    {1:s1, 2:s2, 3:s3, 4:s4, 5:s5, 6:s6, 7:s7, 8:s8,
     9:s9, 10:s10, 11:s11, 12:s12}.get(st.session_state.step, s1)()

if __name__ == "__main__":
    main()
