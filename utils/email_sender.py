"""
Email sender using Gmail SMTP via SSL (port 465).
Credentials passed in from app.py where st.secrets is guaranteed available.
"""
import io
import smtplib
import sys
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
from pathlib import Path
from PIL import Image

PREP_PDF_PATH    = Path(__file__).parent.parent / "assets" / "miralax_prep.pdf"
YOUTUBE_VIDEO_ID = "Wml4B9fmDyE"
OFFICE_PHONE     = "(832) 979-5670"

sys.path.insert(0, str(Path(__file__).parent.parent))


def _compress_image(data: bytes, max_px: int = 1400, quality: int = 75) -> bytes:
    try:
        img = Image.open(io.BytesIO(data))
        img = img.convert("RGB")
        img.thumbnail((max_px, max_px), Image.LANCZOS)
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=quality, optimize=True)
        return buf.getvalue()
    except Exception:
        return data


def _connect(creds: dict):
    server = smtplib.SMTP_SSL(creds["host"], 465, timeout=30)
    server.login(creds["user"], creds["password"])
    return server


def send_office_email(data: dict, pdf_bytes: bytes, uploaded_files: dict, creds: dict) -> bool:
    first  = data.get("first_name", "")
    last   = data.get("last_name", "")
    sub_id = data.get("submission_id", "N/A")

    html = f"""
<html><head>
<style>
  body {{ font-family: 'Helvetica Neue', Arial, sans-serif; font-size: 16px;
         color: #111; background: #f5f7fa; margin: 0; padding: 0; }}
  .wrap {{ max-width: 620px; margin: 24px auto; background: #fff;
           border-radius: 8px; overflow: hidden; border: 1px solid #dde3ea; }}
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
      Full referral PDF + insurance card + photo ID attached.
    </p>
  </div>
  <div class="footer">Submission ID: {sub_id} &nbsp;|&nbsp; Houston Community Surgical Intake System</div>
</div>
</body></html>"""

    msg = MIMEMultipart("mixed")
    msg["From"]    = f"HCS Intake <{creds['from_email']}>"
    msg["To"]      = creds["office_email"]
    msg["Subject"] = f"New Colonoscopy Intake — {first} {last}"
    msg.attach(MIMEText(html, "html"))

    pdf_part = MIMEApplication(pdf_bytes, _subtype="pdf")
    pdf_part.add_header("Content-Disposition", "attachment",
                        filename=f"Referral_{last}_{first}_{sub_id}.pdf")
    msg.attach(pdf_part)

    file_map = {
        "ins_front_bytes": ("ins_front_name", f"Insurance_Card_Front_{last}_{first}"),
        "ins_back_bytes":  ("ins_back_name",  f"Insurance_Card_Back_{last}_{first}"),
        "dl_bytes":        ("dl_name",         f"DriversLicense_{last}_{first}"),
    }
    for bytes_key, (name_key, fallback_name) in file_map.items():
        file_data = uploaded_files.get(bytes_key)
        if file_data:
            file_data = _compress_image(file_data)
            attachment = MIMEApplication(file_data)
            attachment.add_header("Content-Disposition", "attachment",
                                  filename=f"{fallback_name}.jpg")
            msg.attach(attachment)

    with _connect(creds) as server:
        server.send_message(msg)
    return True


def send_patient_email(data: dict, pdf_bytes: bytes, creds: dict) -> bool:
    patient_email = data.get("email", "")
    if not patient_email:
        return False

    first    = data.get("first_name", "Patient")
    last     = data.get("last_name", "")
    sub_id   = data.get("submission_id", "N/A")
    location = data.get("location_preference", "")

    video_section = f"""
    <div class="section">
      <h2>PREP VIDEO</h2>
      <p>Please watch this short video so you know what to expect:</p>
      <p><a href="https://www.youtube.com/watch?v={YOUTUBE_VIDEO_ID}"
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
           border-radius: 8px; overflow: hidden; border: 1px solid #dde3ea; }}
  .header {{ background: #1a3a5c; padding: 24px 28px; text-align: center; }}
  .header h1 {{ color: #fff; font-size: 22px; margin: 0 0 4px; }}
  .header p  {{ color: #a8c4e0; font-size: 15px; margin: 0; }}
  .body {{ padding: 28px; }}
  .greeting {{ font-size: 19px; font-weight: 600; color: #1a3a5c; margin-bottom: 12px; }}
  .intro {{ font-size: 16px; color: #333; line-height: 1.7; margin-bottom: 24px; }}
  .section {{ margin-bottom: 24px; }}
  .section h2 {{ font-size: 13px; font-weight: 700; color: #fff;
                 background: #1a3a5c; padding: 7px 12px;
                 border-radius: 4px; margin: 0 0 12px; letter-spacing:.5px; }}
  .section p  {{ font-size: 16px; color: #333; line-height: 1.7; margin: 6px 0; }}
  .section ul {{ font-size: 16px; color: #333; line-height: 1.9; padding-left: 20px; margin: 0; }}
  .highlight {{ background: #e8f4fd; border-left: 4px solid #2c5f8a;
                padding: 14px 18px; border-radius: 4px;
                font-size: 16px; color: #1a3a5c; margin: 16px 0; }}
  .footer {{ background: #f5f7fa; padding: 18px 28px; font-size: 13px;
             color: #888; text-align: center; border-top: 1px solid #dde3ea; line-height: 1.8; }}
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
      Thank you for completing your colonoscopy intake. We have received everything and
      Tamika or Kaye will be in touch within <strong>1–2 business days</strong> to schedule your procedure.
    </div>
    <div class="section">
      <h2>YOUR PREFERRED LOCATION</h2>
      <p>{location}</p>
    </div>
    <div class="section">
      <h2>INSURANCE</h2>
      <p>{data.get("insurance_message", "Our office will verify your coverage before scheduling.")}</p>
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
        <li>Questions? Call or text <strong>{OFFICE_PHONE}</strong> or reply to this email.</li>
      </ul>
    </div>
    <div class="highlight">
      Call or text <strong>{OFFICE_PHONE}</strong> &nbsp;|&nbsp;
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
    msg["From"]    = f"Houston Community Surgical <{creds['from_email']}>"
    msg["To"]      = patient_email
    msg["Subject"] = "Your Colonoscopy Intake — Houston Community Surgical"
    msg.attach(MIMEText(html, "html"))

    pdf_part = MIMEApplication(pdf_bytes, _subtype="pdf")
    pdf_part.add_header("Content-Disposition", "attachment",
                        filename=f"Colonoscopy_Referral_{last}_{first}.pdf")
    msg.attach(pdf_part)

    if PREP_PDF_PATH.exists():
        prep_part = MIMEApplication(PREP_PDF_PATH.read_bytes(), _subtype="pdf")
        prep_part.add_header("Content-Disposition", "attachment",
                             filename="MiraLAX_Prep_Instructions.pdf")
        msg.attach(prep_part)

    with _connect(creds) as server:
        server.send_message(msg)
    return True


def send_referral_email(friend_email: str, sender_name: str, creds: dict) -> bool:
    html = f"""
<html><head>
<style>
  body {{ font-family: 'Helvetica Neue', Arial, sans-serif; font-size: 16px;
         color: #111; background: #f5f7fa; margin: 0; padding: 0; }}
  .wrap {{ max-width: 580px; margin: 24px auto; background: #fff;
           border-radius: 8px; overflow: hidden; border: 1px solid #dde3ea; }}
  .header {{ background: #1a3a5c; padding: 24px 28px; text-align: center; }}
  .header h1 {{ color: #fff; font-size: 20px; margin: 0 0 4px; }}
  .header p  {{ color: #a8c4e0; font-size: 14px; margin: 0; }}
  .body {{ padding: 28px; font-size: 16px; color: #333; line-height: 1.7; }}
  .cta {{ display: block; text-align: center; background: #1a3a5c; color: #fff !important;
          padding: 14px 28px; border-radius: 8px; text-decoration: none;
          font-weight: 700; font-size: 17px; margin: 24px 0; }}
  .footer {{ background: #f5f7fa; padding: 14px 28px;
             font-size: 12px; color: #888; text-align: center; }}
</style>
</head><body>
<div class="wrap">
  <div class="header">
    <h1>Houston Community Surgical</h1>
    <p>Dr. Ritha Belizaire MD FACS FASCRS</p>
  </div>
  <div class="body">
    <p>Hey,</p>
    <p><strong>{sender_name}</strong> just completed their colonoscopy intake online and thought you might be due for one too.</p>
    <p>It took less than 5 minutes — no phone calls, no waiting on hold. You fill out a short form, upload your insurance card, and the office takes it from there.</p>
    <a href="https://bit.ly/colonoscopy-intake" class="cta">&#9654; Get Started — takes about 5 minutes</a>
    <p style="font-size:14px; color:#555;">
      Questions? Call or text <strong>(832) 979-5670</strong> or email
      <strong>info@houstoncommunitysurgical.com</strong>
    </p>
  </div>
  <div class="footer">Houston Community Surgical &nbsp;|&nbsp; Dr. Ritha Belizaire MD FACS FASCRS</div>
</div>
</body></html>"""

    msg = MIMEMultipart("mixed")
    msg["From"]    = f"Houston Community Surgical <{creds['from_email']}>"
    msg["To"]      = friend_email
    msg["Subject"] = f"{sender_name} thinks it's time for your colonoscopy \U0001f604"
    msg.attach(MIMEText(html, "html"))
    with _connect(creds) as server:
        server.send_message(msg)
    return True


def send_emails(data: dict, pdf_bytes: bytes, uploaded_files: dict = None, creds: dict = None) -> tuple:
    if uploaded_files is None:
        uploaded_files = {}
    if not creds or not creds.get("user") or not creds.get("password"):
        raise ValueError("SMTP credentials missing from secrets.")
    office_err = None
    try:
        office_ok = send_office_email(data, pdf_bytes, uploaded_files, creds)
    except Exception as e:
        office_ok  = False
        office_err = str(e)

    patient_err = None
    try:
        patient_ok = send_patient_email(data, pdf_bytes, creds)
    except Exception as e:
        patient_ok  = False
        patient_err = str(e)

    error = " | ".join(filter(None, [office_err, patient_err]))
    return office_ok, patient_ok, error
