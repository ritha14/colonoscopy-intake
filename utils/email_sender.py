"""
Email sender — sends referral PDF and any uploaded files to the office,
and sends a styled HTML confirmation email to the patient.
"""
import smtplib
import sys
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
from email.mime.image import MIMEImage
from pathlib import Path

PREP_PDF_PATH = Path(__file__).parent.parent / "assets" / "miralax_prep.pdf"

sys.path.insert(0, str(Path(__file__).parent.parent))
from config import SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASSWORD, FROM_EMAIL, OFFICE_EMAIL, OFFICE_PHONE, YOUTUBE_VIDEO_ID


def _connect():
    password = SMTP_PASSWORD.replace(" ", "")
    server = smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=20)
    server.starttls()
    server.login(SMTP_USER, password)
    return server


def send_office_email(data: dict, pdf_bytes: bytes, uploaded_files: dict) -> bool:
    if not SMTP_USER or not SMTP_PASSWORD:
        print("EMAIL: SMTP not configured — skipping office email.")
        return False

    try:
        first = data.get("first_name", "")
        last  = data.get("last_name", "")
        sub_id = data.get("submission_id", "N/A")

        msg = MIMEMultipart("alternative")
        msg["From"]    = f"HCS Intake <{FROM_EMAIL}>"
        msg["To"]      = OFFICE_EMAIL
        msg["Subject"] = f"New Colonoscopy Intake — {first} {last}"

        html = f"""
<html><head>
<style>
  body {{ font-family: 'Helvetica Neue', Arial, sans-serif; font-size: 16px;
         color: #111; background: #f5f7fa; margin: 0; padding: 0; }}
  .wrap {{ max-width: 620px; margin: 24px auto; background: #fff;
           border-radius: 8px; overflow: hidden;
           border: 1px solid #dde3ea; }}
  .header {{ background: #1a3a5c; padding: 20px 28px; }}
  .header h1 {{ color: #fff; font-size: 20px; margin: 0; }}
  .header p  {{ color: #a8c4e0; font-size: 14px; margin: 4px 0 0; }}
  .body {{ padding: 24px 28px; }}
  .section {{ margin-bottom: 20px; }}
  .section h2 {{ font-size: 13px; font-weight: 700; color: #fff;
                 background: #1a3a5c; padding: 6px 10px;
                 border-radius: 4px; margin: 0 0 10px; letter-spacing:.5px; }}
  .row {{ display: flex; padding: 4px 0; border-bottom: 1px solid #f0f0f0; }}
  .lbl {{ color: #555; font-size: 14px; min-width: 150px; }}
  .val {{ color: #111; font-size: 14px; font-weight: 600; }}
  .footer {{ background: #f5f7fa; padding: 14px 28px;
             font-size: 12px; color: #888; text-align: center; }}
</style>
</head><body>
<div class="wrap">
  <div class="header">
    <h1>New Colonoscopy Intake</h1>
    <p>Houston Community Surgical — Dr. Ritha Belizaire MD FACS FASCRS</p>
  </div>
  <div class="body">
    <div class="section">
      <h2>PATIENT</h2>
      <div class="row"><span class="lbl">Name</span><span class="val">{first} {last}</span></div>
      <div class="row"><span class="lbl">DOB</span><span class="val">{data.get("dob","")}</span></div>
      <div class="row"><span class="lbl">Phone</span><span class="val">{data.get("phone","")}</span></div>
      <div class="row"><span class="lbl">Email</span><span class="val">{data.get("email","")}</span></div>
    </div>
    <div class="section">
      <h2>INTAKE RESULTS</h2>
      <div class="row"><span class="lbl">Insurance</span><span class="val">{data.get("insurance_result","PENDING — verify")}</span></div>
      <div class="row"><span class="lbl">ASA Class</span><span class="val">ASA {data.get("asa_class","?")}</span></div>
      <div class="row"><span class="lbl">Decision</span><span class="val">{data.get("patient_decision","")}</span></div>
      <div class="row"><span class="lbl">Location</span><span class="val">{data.get("location_preference","")}</span></div>
    </div>
    <div class="section">
      <h2>REFERRING / PCP</h2>
      <div class="row"><span class="lbl">Doctor</span><span class="val">{data.get("pcp_name","")}</span></div>
      <div class="row"><span class="lbl">Address</span><span class="val">{data.get("pcp_address","")}</span></div>
      <div class="row"><span class="lbl">Phone / Fax</span><span class="val">{data.get("pcp_phone","")} / {data.get("pcp_fax","")}</span></div>
    </div>
    <p style="font-size:14px; color:#555;">
      Full referral form attached as PDF. Insurance card and photo ID attached below.
    </p>
  </div>
  <div class="footer">Submission ID: {sub_id} &nbsp;|&nbsp; Houston Community Surgical Intake System</div>
</div>
</body></html>"""

        msg.attach(MIMEText(html, "html"))

        # Attach referral PDF
        pdf_part = MIMEApplication(pdf_bytes, _subtype="pdf")
        pdf_part.add_header("Content-Disposition", "attachment",
                            filename=f"Referral_{last}_{first}_{sub_id}.pdf")
        msg.attach(pdf_part)

        # Attach uploaded ID files
        file_map = {
            "ins_front_bytes": ("ins_front_name", f"Insurance_Card_Front_{last}_{first}"),
            "ins_back_bytes":  ("ins_back_name",  f"Insurance_Card_Back_{last}_{first}"),
            "dl_bytes":        ("dl_name",         f"DriversLicense_{last}_{first}"),
        }
        for bytes_key, (name_key, fallback_name) in file_map.items():
            file_data = uploaded_files.get(bytes_key)
            if file_data:
                orig_name = uploaded_files.get(name_key, "")
                ext = Path(orig_name).suffix if orig_name else ".jpg"
                attachment = MIMEApplication(file_data)
                attachment.add_header("Content-Disposition", "attachment",
                                      filename=f"{fallback_name}{ext}")
                msg.attach(attachment)

        with _connect() as server:
            server.send_message(msg)
        return True

    except Exception as e:
        print(f"Office email error: {type(e).__name__}: {e}")
        return False


def send_patient_email(data: dict, pdf_bytes: bytes) -> bool:
    if not SMTP_USER or not SMTP_PASSWORD:
        print("EMAIL: SMTP not configured — skipping patient email.")
        return False

    patient_email = data.get("email", "")
    if not patient_email:
        return False

    try:
        first  = data.get("first_name", "Patient")
        last   = data.get("last_name", "")
        sub_id = data.get("submission_id", "N/A")
        location = data.get("location_preference", "")

        video_section = ""
        if YOUTUBE_VIDEO_ID and YOUTUBE_VIDEO_ID.strip():
            video_section = f"""
    <div class="section">
      <h2>COLONOSCOPY INSTRUCTION VIDEO</h2>
      <p>Please watch this short video so you know exactly what to expect on the day of your procedure:</p>
      <p><a href="https://www.youtube.com/watch?v={YOUTUBE_VIDEO_ID.strip()}"
            style="background:#1a3a5c; color:#fff; padding:10px 20px;
                   border-radius:6px; text-decoration:none; font-weight:700;
                   display:inline-block;">▶ Watch the Video</a></p>
    </div>"""

        html = f"""
<html><head>
<style>
  body {{ font-family: 'Helvetica Neue', Arial, sans-serif; font-size: 17px;
         color: #111; background: #f5f7fa; margin: 0; padding: 0; }}
  .wrap {{ max-width: 620px; margin: 24px auto; background: #fff;
           border-radius: 8px; overflow: hidden;
           border: 1px solid #dde3ea; }}
  .header {{ background: #1a3a5c; padding: 24px 28px; text-align: center; }}
  .header h1 {{ color: #fff; font-size: 22px; margin: 0 0 4px; }}
  .header p  {{ color: #a8c4e0; font-size: 15px; margin: 0; }}
  .body {{ padding: 28px 28px; }}
  .greeting {{ font-size: 19px; font-weight: 600; color: #1a3a5c; margin-bottom: 12px; }}
  .intro {{ font-size: 16px; color: #333; line-height: 1.7; margin-bottom: 24px; }}
  .section {{ margin-bottom: 24px; }}
  .section h2 {{ font-size: 13px; font-weight: 700; color: #fff;
                 background: #1a3a5c; padding: 7px 12px;
                 border-radius: 4px; margin: 0 0 12px; letter-spacing:.5px; }}
  .section p  {{ font-size: 16px; color: #333; line-height: 1.7; margin: 6px 0; }}
  .section ul {{ font-size: 16px; color: #333; line-height: 1.9;
                 padding-left: 20px; margin: 0; }}
  .highlight {{ background: #e8f4fd; border-left: 4px solid #2c5f8a;
                padding: 14px 18px; border-radius: 4px;
                font-size: 16px; color: #1a3a5c; margin: 16px 0; }}
  .footer {{ background: #f5f7fa; padding: 18px 28px;
             font-size: 13px; color: #888; text-align: center;
             border-top: 1px solid #dde3ea; line-height: 1.8; }}
</style>
</head><body>
<div class="wrap">
  <div class="header">
    <h1>Houston Community Surgical</h1>
    <p>Dr. Ritha Belizaire MD FACS FASCRS</p>
  </div>
  <div class="body">
    <div class="greeting">Hi {first},</div>
    <div class="intro">
      Thank you for completing your colonoscopy intake. We have received everything
      and Tamika or Kaye will be in touch within <strong>1–2 business days</strong> to schedule your procedure.
    </div>

    <div class="section">
      <h2>YOUR PREFERRED LOCATION</h2>
      <p>{location}</p>
    </div>

    <div class="section">
      <h2>INSURANCE</h2>
      <p>{data.get("insurance_message","Our office will verify your coverage before scheduling.")}</p>
    </div>

    {video_section}

    <div class="section">
      <h2>BOWEL PREP INSTRUCTIONS</h2>
      <ul>
        <li>Your prep instructions are <strong>attached to this email.</strong></li>
        <li>All medications are <strong>over the counter</strong> — no prescription needed.</li>
        <li>Do <strong>not</strong> eat solid food after midnight the night before your procedure.</li>
      </ul>
    </div>

    <div class="section">
      <h2>NEXT STEPS</h2>
      <ul>
        <li>Your referral summary is attached — please save it for your records.</li>
        <li>If you have any questions, call or text us at <strong>{OFFICE_PHONE}</strong>
            or reply to this email.</li>
      </ul>
    </div>

    <div class="highlight">
      Questions? Call or text <strong>{OFFICE_PHONE}</strong> or email
      <strong>info@houstoncommunitysurgical.com</strong>
    </div>
  </div>
  <div class="footer">
    Houston Community Surgical &nbsp;|&nbsp; Dr. Ritha Belizaire MD FACS FASCRS<br>
    {OFFICE_PHONE} &nbsp;|&nbsp; info@houstoncommunitysurgical.com<br>
    Submission ID: {sub_id}
  </div>
</div>
</body></html>"""

        msg = MIMEMultipart("mixed")
        msg["From"]    = f"Houston Community Surgical <{FROM_EMAIL}>"
        msg["To"]      = patient_email
        msg["Subject"] = "Your Colonoscopy Intake — Houston Community Surgical"

        msg.attach(MIMEText(html, "html"))

        # Attach referral PDF
        pdf_part = MIMEApplication(pdf_bytes, _subtype="pdf")
        pdf_part.add_header("Content-Disposition", "attachment",
                            filename=f"Colonoscopy_Referral_{last}_{first}.pdf")
        msg.attach(pdf_part)

        # Attach bowel prep PDF if available
        if PREP_PDF_PATH.exists():
            prep_part = MIMEApplication(PREP_PDF_PATH.read_bytes(), _subtype="pdf")
            prep_part.add_header("Content-Disposition", "attachment",
                                 filename="MiraLAX_Prep_Instructions.pdf")
            msg.attach(prep_part)

        with _connect() as server:
            server.send_message(msg)
        return True

    except Exception as e:
        print(f"Patient email error: {type(e).__name__}: {e}")
        return False


def send_emails(data: dict, pdf_bytes: bytes, uploaded_files: dict = None) -> tuple:
    if uploaded_files is None:
        uploaded_files = {}
    office_ok  = send_office_email(data, pdf_bytes, uploaded_files)
    patient_ok = send_patient_email(data, pdf_bytes)
    return office_ok, patient_ok
