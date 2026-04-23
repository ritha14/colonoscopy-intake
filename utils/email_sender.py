"""
Email sender — sends referral PDF and any uploaded files to the office,
and sends a confirmation email to the patient.
"""
import smtplib
import sys
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
from email.mime.image import MIMEImage
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from config import SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASSWORD, FROM_EMAIL, OFFICE_EMAIL, OFFICE_PHONE


def _connect():
    server = smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=20)
    server.starttls()
    server.login(SMTP_USER, SMTP_PASSWORD)
    return server


def send_office_email(data: dict, pdf_bytes: bytes, uploaded_files: dict) -> bool:
    """
    Send referral PDF + uploaded ID documents to the office.
    uploaded_files: dict with keys like 'ins_front_bytes', 'ins_back_bytes', 'dl_bytes'
    """
    if not SMTP_USER or not SMTP_PASSWORD:
        print("EMAIL: SMTP not configured — skipping office email.")
        return False

    try:
        first = data.get("first_name", "")
        last = data.get("last_name", "")
        sub_date = data.get("submission_date", "")
        sub_id = data.get("submission_id", "N/A")

        msg = MIMEMultipart()
        msg["From"] = f"Dr. Ritha Belizaire <{FROM_EMAIL}>"
        msg["To"] = OFFICE_EMAIL
        msg["Subject"] = f"New Direct Colonoscopy Request — {first} {last}"

        body = f"""New colonoscopy intake submission received.

Patient: {first} {last}
DOB: {data.get("dob", "")}
Phone: {data.get("phone", "")}
Email: {data.get("email", "")}

─── RESULTS ───────────────────────────────────────────
Insurance Type: {data.get("insurance_type_label", "")}
Insurance Carrier: {data.get("insurance_carrier", "")}
Eligibility: {data.get("insurance_result", "")}
ASA Class: ASA {data.get("asa_class", "?")}
Payment: {data.get("pay_label", "")}
Decision: {data.get("patient_decision", "")}
Location: {data.get("location_preference", "")}
Status: {data.get("status", "")}

─── PCP ────────────────────────────────────────────────
{data.get("pcp_name", "")}
{data.get("pcp_address", "")}
Phone: {data.get("pcp_phone", "")} | Fax: {data.get("pcp_fax", "")}

Full referral form is attached as PDF.
ID documents (insurance card, driver's license) are attached below if provided.

Submission ID: {sub_id}
— Houston Community Surgical Intake System"""

        msg.attach(MIMEText(body, "plain"))

        # Attach referral PDF
        pdf_part = MIMEApplication(pdf_bytes, _subtype="pdf")
        pdf_part.add_header(
            "Content-Disposition", "attachment",
            filename=f"Referral_{last}_{first}_{sub_id}.pdf",
        )
        msg.attach(pdf_part)

        # Attach uploaded files
        file_map = {
            "ins_front_bytes": ("ins_front_name", f"Insurance_Card_Front_{last}_{first}"),
            "ins_back_bytes": ("ins_back_name", f"Insurance_Card_Back_{last}_{first}"),
            "dl_bytes": ("dl_name", f"DriversLicense_{last}_{first}"),
        }
        for bytes_key, (name_key, fallback_name) in file_map.items():
            file_data = uploaded_files.get(bytes_key)
            if file_data:
                orig_name = uploaded_files.get(name_key, "")
                ext = Path(orig_name).suffix if orig_name else ".jpg"
                attachment = MIMEApplication(file_data)
                attachment.add_header(
                    "Content-Disposition", "attachment",
                    filename=f"{fallback_name}{ext}",
                )
                msg.attach(attachment)

        with _connect() as server:
            server.send_message(msg)

        return True

    except Exception as e:
        print(f"Office email error: {type(e).__name__}: {e}")
        return False


def send_patient_email(data: dict, pdf_bytes: bytes) -> bool:
    """Send confirmation + referral PDF to patient."""
    if not SMTP_USER or not SMTP_PASSWORD:
        print("EMAIL: SMTP not configured — skipping patient email.")
        return False

    patient_email = data.get("email", "")
    if not patient_email:
        return False

    try:
        first = data.get("first_name", "Patient")
        last = data.get("last_name", "")
        sub_id = data.get("submission_id", "N/A")

        msg = MIMEMultipart()
        msg["From"] = f"Houston Community Surgical <{FROM_EMAIL}>"
        msg["To"] = patient_email
        msg["Subject"] = "Your Colonoscopy Intake Has Been Received — Houston Community Surgical"

        body = f"""Dear {first},

Thank you for completing your colonoscopy intake form with Houston Community Surgical.

Your submission has been received and is being reviewed by our team.

Tamika or Kaye will be in touch with you within 1–2 business days to schedule your procedure.

──────────────────────────────────────────────
INSURANCE & PAYMENT
──────────────────────────────────────────────
{data.get("insurance_message", "")}

──────────────────────────────────────────────
YOUR PREFERRED LOCATION
──────────────────────────────────────────────
{data.get("location_preference", "")}

──────────────────────────────────────────────
NEXT STEPS
──────────────────────────────────────────────
• Your referral summary is attached to this email — please save it for your records.
• Bowel prep instructions (MiraLAX) will be provided when your procedure is scheduled.
• If you have any questions, call us at {OFFICE_PHONE} or reply to this email.

──────────────────────────────────────────────
Submission ID: {sub_id}

Thank you for choosing Houston Community Surgical.

Warm regards,
Tamika & Kaye
Houston Community Surgical — Dr. Ritha Belizaire MD FACS FASCRS
Phone: {OFFICE_PHONE}
Email: info@houstoncommunitysurgical.com"""

        msg.attach(MIMEText(body, "plain"))

        # Attach referral PDF
        pdf_part = MIMEApplication(pdf_bytes, _subtype="pdf")
        pdf_part.add_header(
            "Content-Disposition", "attachment",
            filename=f"Colonoscopy_Referral_{last}_{first}.pdf",
        )
        msg.attach(pdf_part)

        with _connect() as server:
            server.send_message(msg)

        return True

    except Exception as e:
        print(f"Patient email error: {type(e).__name__}: {e}")
        return False


def send_emails(data: dict, pdf_bytes: bytes, uploaded_files: dict = None) -> tuple:
    """
    Send both office and patient emails.
    Returns (office_sent: bool, patient_sent: bool).
    """
    if uploaded_files is None:
        uploaded_files = {}
    office_ok = send_office_email(data, pdf_bytes, uploaded_files)
    patient_ok = send_patient_email(data, pdf_bytes)
    return office_ok, patient_ok
