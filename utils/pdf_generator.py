"""
Generate the colonoscopy referral PDF using ReportLab.
"""
import io
from datetime import datetime

from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, HRFlowable, Table, TableStyle,
)
from reportlab.lib.enums import TA_CENTER, TA_LEFT


NAVY = colors.HexColor("#1a3a5c")
BLUE_LIGHT = colors.HexColor("#e8f0f8")
BLUE_MID = colors.HexColor("#2c5f8a")
GREY = colors.HexColor("#666666")
GREEN = colors.HexColor("#28a745")
ORANGE = colors.HexColor("#e67e00")
RED = colors.HexColor("#c0392b")


def _styles():
    base = getSampleStyleSheet()

    title = ParagraphStyle(
        "HCSTitle", parent=base["Normal"],
        fontSize=17, textColor=NAVY, alignment=TA_CENTER,
        fontName="Helvetica-Bold", spaceAfter=2,
    )
    subtitle = ParagraphStyle(
        "HCSSubtitle", parent=base["Normal"],
        fontSize=11, textColor=BLUE_MID, alignment=TA_CENTER,
        spaceAfter=2,
    )
    doc_title = ParagraphStyle(
        "HCSDocTitle", parent=base["Normal"],
        fontSize=10, textColor=GREY, alignment=TA_CENTER,
        spaceAfter=10,
    )
    section = ParagraphStyle(
        "HCSSection", parent=base["Normal"],
        fontSize=9, textColor=colors.white, fontName="Helvetica-Bold",
        backColor=NAVY, leftIndent=-4, rightIndent=-4,
        borderPad=5, spaceBefore=10, spaceAfter=4,
    )
    field_label = ParagraphStyle(
        "HCSFieldLabel", parent=base["Normal"],
        fontSize=8, fontName="Helvetica-Bold", textColor=NAVY, spaceAfter=1,
    )
    field_value = ParagraphStyle(
        "HCSFieldValue", parent=base["Normal"],
        fontSize=9, textColor=colors.black, spaceAfter=5, leftIndent=8,
    )
    status_ok = ParagraphStyle(
        "HCSStatusOK", parent=base["Normal"],
        fontSize=10, fontName="Helvetica-Bold", textColor=GREEN,
    )
    status_warn = ParagraphStyle(
        "HCSStatusWarn", parent=base["Normal"],
        fontSize=10, fontName="Helvetica-Bold", textColor=ORANGE,
    )
    status_err = ParagraphStyle(
        "HCSStatusErr", parent=base["Normal"],
        fontSize=10, fontName="Helvetica-Bold", textColor=RED,
    )
    footer = ParagraphStyle(
        "HCSFooter", parent=base["Normal"],
        fontSize=7, textColor=GREY, alignment=TA_CENTER,
    )
    return {
        "title": title, "subtitle": subtitle, "doc_title": doc_title,
        "section": section, "field_label": field_label, "field_value": field_value,
        "status_ok": status_ok, "status_warn": status_warn, "status_err": status_err,
        "footer": footer,
    }


def _section(s, elements, title):
    elements.append(Paragraph(f"  {title}", s["section"]))


def _field(s, elements, label, value):
    if not value or str(value).strip() == "":
        value = "—"
    elements.append(Paragraph(label, s["field_label"]))
    elements.append(Paragraph(str(value), s["field_value"]))


def generate_referral_pdf(data: dict) -> bytes:
    """Build and return referral PDF as bytes."""
    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=letter,
        rightMargin=0.75 * inch, leftMargin=0.75 * inch,
        topMargin=0.75 * inch, bottomMargin=0.75 * inch,
    )
    s = _styles()
    el = []

    # ── Header ──────────────────────────────────────────────────────────────
    el.append(Paragraph("HOUSTON COMMUNITY SURGICAL", s["title"]))
    el.append(Paragraph("Dr. Ritha Belizaire MD FACS FASCRS", s["subtitle"]))
    el.append(Paragraph("Direct-to-Colonoscopy Referral — Confidential Medical Document", s["doc_title"]))
    el.append(HRFlowable(width="100%", thickness=2, color=NAVY))
    el.append(Spacer(1, 6))

    sub_date = data.get("submission_date", datetime.now().strftime("%m/%d/%Y %I:%M %p"))
    sub_id = data.get("submission_id", "N/A")
    el.append(Paragraph(
        f"<b>Submission Date:</b> {sub_date} &nbsp;&nbsp; <b>ID:</b> {sub_id} &nbsp;&nbsp; <b>Status:</b> {data.get('status', '').upper()}",
        s["field_value"],
    ))
    el.append(Spacer(1, 4))

    # ── 1. Patient Demographics ──────────────────────────────────────────────
    _section(s, el, "1. PATIENT DEMOGRAPHICS")
    name = f"{data.get('first_name', '')} {data.get('last_name', '')}".strip()
    _field(s, el, "Full Name", name)
    _field(s, el, "Date of Birth", data.get("dob"))
    _field(s, el, "Age", data.get("age_display"))
    _field(s, el, "Phone", data.get("phone"))
    _field(s, el, "Email", data.get("email"))

    # ── 2. Chief Complaint & HPI ─────────────────────────────────────────────
    _section(s, el, "2. CHIEF COMPLAINT & HISTORY OF PRESENT ILLNESS")
    _field(s, el, "Chief Complaint", data.get("chief_complaint"))
    _field(s, el, "HPI / Symptoms", data.get("hpi"))

    # ── 3. Past Medical History ──────────────────────────────────────────────
    _section(s, el, "3. PAST MEDICAL HISTORY (PMH)")
    _field(s, el, "PMH", data.get("pmh"))

    # ── 4. Past Surgical History ─────────────────────────────────────────────
    _section(s, el, "4. PAST SURGICAL HISTORY (PSH)")
    _field(s, el, "PSH", data.get("psh"))

    # ── 5. Social History ────────────────────────────────────────────────────
    _section(s, el, "5. SOCIAL HISTORY")
    _field(s, el, "Social History", data.get("sochx"))

    # ── 6. Family History ────────────────────────────────────────────────────
    _section(s, el, "6. FAMILY HISTORY")
    _field(s, el, "Family History", data.get("fhx"))

    # ── 7. Medications ───────────────────────────────────────────────────────
    _section(s, el, "7. CURRENT MEDICATIONS")
    _field(s, el, "Medications", data.get("medications"))

    # ── 8. Allergies ─────────────────────────────────────────────────────────
    _section(s, el, "8. ALLERGIES")
    _field(s, el, "Allergies", data.get("allergies"))

    # ── 9. Prior Screening ───────────────────────────────────────────────────
    _section(s, el, "9. PREVIOUS COLORECTAL CANCER SCREENING")
    _field(s, el, "Prior Screening & Results", data.get("prior_screening"))

    # ── 10. PCP / Referring Physician ────────────────────────────────────────
    _section(s, el, "10. PRIMARY CARE / REFERRING PHYSICIAN")
    _field(s, el, "Doctor's Name", data.get("pcp_name"))
    _field(s, el, "Office Address", data.get("pcp_address"))
    _field(s, el, "Phone", data.get("pcp_phone"))
    _field(s, el, "Fax", data.get("pcp_fax"))

    # ── 11. Insurance ────────────────────────────────────────────────────────
    _section(s, el, "11. INSURANCE INFORMATION")
    _field(s, el, "Insurance Type", data.get("insurance_type_label"))
    _field(s, el, "Carrier / Plan Name", data.get("insurance_carrier"))
    ph = "Patient (self)" if data.get("policy_holder") == "self" else data.get("policy_holder_name", "")
    _field(s, el, "Policy Holder", ph)
    if data.get("policy_holder") == "other":
        _field(s, el, "Policy Holder DOB", data.get("policy_holder_dob"))
    _field(s, el, "ID Documents", data.get("id_docs_note", "Uploaded and emailed to office"))

    # ── 12. Insurance Eligibility Determination ──────────────────────────────
    _section(s, el, "12. INSURANCE ELIGIBILITY DETERMINATION")
    ins_result = data.get("insurance_result", "")
    if ins_result == "ELIGIBLE":
        el.append(Paragraph("ELIGIBLE — In-Network / Covered", s["status_ok"]))
    elif ins_result in ("CASH_PAY_SURGEON", "CASH_PAY_FULL"):
        el.append(Paragraph(f"CASH PAY — {data.get('pay_label', ins_result)}", s["status_warn"]))
    elif ins_result == "NOT_ELIGIBLE":
        el.append(Paragraph("NOT ELIGIBLE — Medicaid", s["status_err"]))
    else:
        el.append(Paragraph(f"PENDING VERIFICATION — {ins_result}", s["field_value"]))
    el.append(Spacer(1, 3))
    _field(s, el, "Patient-Facing Message", data.get("insurance_message"))

    # ── 13. ASA Classification ───────────────────────────────────────────────
    _section(s, el, "13. ASA PHYSICAL STATUS CLASSIFICATION")
    asa_class = data.get("asa_class", "?")
    is_candidate = data.get("is_candidate", False)
    asa_label = f"ASA {asa_class} — {'CANDIDATE for direct scheduling' if is_candidate else 'REQUIRES pre-procedure office visit'}"
    if is_candidate:
        el.append(Paragraph(asa_label, s["status_ok"]))
    else:
        el.append(Paragraph(asa_label, s["status_warn"]))
    el.append(Spacer(1, 3))
    _field(s, el, "Clinical Reasoning", data.get("asa_reasoning"))
    factors = data.get("asa_key_factors", [])
    if factors:
        _field(s, el, "Key Factors", ", ".join(factors))

    # ── 14. Payment Type ─────────────────────────────────────────────────────
    _section(s, el, "14. PAYMENT TYPE")
    _field(s, el, "Payment Classification", data.get("pay_label", data.get("insurance_result")))

    # ── 15. Patient Decision ─────────────────────────────────────────────────
    _section(s, el, "15. PATIENT DECISION")
    _field(s, el, "Decision", data.get("patient_decision"))

    # ── 16. Instruction Video ────────────────────────────────────────────────
    _section(s, el, "16. COLONOSCOPY INSTRUCTION VIDEO")
    _field(s, el, "Video Status", "Watched" if data.get("video_watched") else "Will watch later")

    # ── 17. Location Preference ──────────────────────────────────────────────
    _section(s, el, "17. PREFERRED SURGERY CENTER")
    _field(s, el, "Location", data.get("location_preference"))

    # ── 18. Submission Summary ───────────────────────────────────────────────
    _section(s, el, "18. SUBMISSION SUMMARY")
    _field(s, el, "Submission Status", data.get("status", "").upper())
    _field(s, el, "Submission Date", sub_date)
    _field(s, el, "Submission ID", sub_id)

    # ── Footer ───────────────────────────────────────────────────────────────
    el.append(Spacer(1, 14))
    el.append(HRFlowable(width="100%", thickness=1, color=GREY))
    el.append(Spacer(1, 4))
    el.append(Paragraph("Houston Community Surgical — Dr. Ritha Belizaire MD FACS FASCRS", s["footer"]))
    el.append(Paragraph(
        "Phone: (832) 979-5670 | eFax: 832-346-1911 | info@houstoncommunitysurgical.com",
        s["footer"],
    ))
    el.append(Paragraph(
        "CONFIDENTIAL MEDICAL DOCUMENT — FOR AUTHORIZED USE ONLY", s["footer"],
    ))

    doc.build(el)
    return buf.getvalue()
