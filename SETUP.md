# Houston Community Surgical — Colonoscopy Intake Setup Guide

## Quick Start (Local)

1. **Install dependencies**
   ```
   pip install -r requirements.txt
   ```

2. **Set up your credentials**
   ```
   copy .env.example .env
   ```
   Open `.env` and fill in:
   - Your Gmail (or office email) App Password for SMTP
   - Your Anthropic API key (for the medical safety check)
   - The YouTube video ID once available

3. **Run the app**
   ```
   streamlit run app.py
   ```
   The app opens at http://localhost:8501

---

## Email Setup (Gmail)

If using a Gmail account to send emails:

1. Go to your Google Account → Security → 2-Step Verification (must be ON)
2. Then go to Security → App passwords
3. Create a new app password (name it "HCS Intake")
4. Copy the 16-character password into `.env` as `SMTP_PASSWORD`
5. Set `SMTP_USER` to the full Gmail address

> If you use Google Workspace (info@houstoncommunitysurgical.com), the same steps apply.
> Your IT/domain provider may have a different SMTP host — check with them.

---

## Prep Instructions PDF

Drop your MiraLAX prep PDF here:
```
assets/miralax_prep.pdf
```
The download button on the success page will activate automatically.

---

## YouTube Video

Once you have the unlisted YouTube video link:
1. Copy the video ID from the URL (the part after `?v=`)
   - Example: `https://www.youtube.com/watch?v=abc123xyz` → ID is `abc123xyz`
2. Add it to `.env`:
   ```
   YOUTUBE_VIDEO_ID=abc123xyz
   ```

---

## Sharing Publicly (Streamlit Cloud — Free)

To get a shareable public URL:

1. Create a free account at https://streamlit.io/cloud
2. Push this folder to a GitHub repository (private is fine)
3. Connect the repo in Streamlit Cloud and deploy `app.py`
4. Add your secrets in Streamlit Cloud → App Settings → Secrets:
   ```
   SMTP_HOST = "smtp.gmail.com"
   SMTP_PORT = "587"
   SMTP_USER = "info@houstoncommunitysurgical.com"
   SMTP_PASSWORD = "your_app_password"
   FROM_EMAIL = "info@houstoncommunitysurgical.com"
   OFFICE_EMAIL = "info@houstoncommunitysurgical.com"
   ANTHROPIC_API_KEY = "sk-ant-..."
   YOUTUBE_VIDEO_ID = "abc123xyz"
   ```
5. Share the Streamlit URL with patients or PCPs

---

## Submissions Database

All completed forms are stored in `data/submissions.db` (SQLite).
You can open this with DB Browser for SQLite (free download) to view all submissions.

---

## Office Reference

- Phone: (832) 979-5670
- eFax: 832-346-1911
- Email: info@houstoncommunitysurgical.com
- Staff: Tamika and Kaye
