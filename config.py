"""
Configuration — reads from .env (local) or Streamlit secrets (cloud deployment).
"""
import os
from dotenv import load_dotenv

load_dotenv()


def _get(key: str, default: str = "") -> str:
    """Read from env, fall back to st.secrets if running on Streamlit Cloud."""
    val = os.getenv(key, "")
    if val:
        return val
    try:
        import streamlit as st
        return str(st.secrets[key])
    except Exception:
        return default


# Email
SMTP_HOST = _get("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(_get("SMTP_PORT", "587"))
SMTP_USER = _get("SMTP_USER", "")
SMTP_PASSWORD = _get("SMTP_PASSWORD", "")
FROM_EMAIL = _get("FROM_EMAIL", "ritha.belizaire@houstoncommunitysurgical.com")
OFFICE_EMAIL = _get("OFFICE_EMAIL", "info@houstoncommunitysurgical.com")

# Anthropic
ANTHROPIC_API_KEY = _get("ANTHROPIC_API_KEY", "")

# YouTube
YOUTUBE_VIDEO_ID = _get("YOUTUBE_VIDEO_ID", "")

# Database
DB_PATH = _get("DB_PATH", "data/submissions.db")

# Office constants
OFFICE_PHONE = "(832) 979-5670"
OFFICE_FAX = "832-346-1911"
OFFICE_EMAIL_DISPLAY = "info@houstoncommunitysurgical.com"
DOCTOR_NAME = "Dr. Ritha Belizaire MD FACS FASCRS"
PRACTICE_NAME = "Houston Community Surgical"

SURGERY_CENTERS = [
    "Memorial Houston Surgery Center — 9230 Katy Fwy #601, Houston, TX 77055",
    "Kirby Glen Surgery Center — 2457 S Braeswood Blvd, Houston, TX 77030",
]

HOSPITAL_CENTERS = [
    "Memorial Hermann Greater Heights Hospital — 1635 N Loop W, Houston, TX 77008",
    "Houston Methodist Hospital (TMC) — 6565 Fannin St, Houston, TX 77030",
]

BMI_CONDITION = "My BMI is 45 or above"
