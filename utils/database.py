"""
PostgreSQL database for storing all intake submissions (Cloud SQL on Cloud Run).
"""
import psycopg2
import psycopg2.extras
import json
import uuid
from datetime import datetime
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from config import DB_USER, DB_PASSWORD, DB_NAME, INSTANCE_CONNECTION_NAME, DB_HOST, DB_PORT


def _connection():
    if INSTANCE_CONNECTION_NAME:
        conn = psycopg2.connect(
            host=f"/cloudsql/{INSTANCE_CONNECTION_NAME}",
            user=DB_USER,
            password=DB_PASSWORD,
            dbname=DB_NAME,
        )
    else:
        conn = psycopg2.connect(
            host=DB_HOST,
            port=int(DB_PORT),
            user=DB_USER,
            password=DB_PASSWORD,
            dbname=DB_NAME,
        )
    return conn


def init_db():
    conn = _connection()
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS submissions (
            id                  SERIAL PRIMARY KEY,
            submission_id       TEXT UNIQUE NOT NULL,
            submitted_at        TEXT,
            status              TEXT,

            first_name          TEXT,
            last_name           TEXT,
            dob                 TEXT,
            age                 INTEGER,
            phone               TEXT,
            email               TEXT,

            chief_complaint     TEXT,
            hpi                 TEXT,
            pmh                 TEXT,
            psh                 TEXT,
            sochx               TEXT,
            fhx                 TEXT,
            medications         TEXT,
            allergies           TEXT,
            prior_screening     TEXT,

            pcp_name            TEXT,
            pcp_address         TEXT,
            pcp_phone           TEXT,
            pcp_fax             TEXT,

            has_insurance       INTEGER,
            insurance_type      TEXT,
            insurance_carrier   TEXT,
            policy_holder       TEXT,
            policy_holder_name  TEXT,
            policy_holder_dob   TEXT,
            insurance_result    TEXT,
            insurance_message   TEXT,
            pay_label           TEXT,
            payment_type        TEXT,

            asa_class           INTEGER,
            asa_reasoning       TEXT,
            asa_key_factors     TEXT,
            is_candidate        INTEGER,

            patient_decision    TEXT,
            video_watched       INTEGER,
            location_preference TEXT,

            full_json           TEXT
        )
    """)
    conn.commit()
    cur.close()
    conn.close()


def save_submission(data: dict) -> str:
    if not data.get("submission_id"):
        data["submission_id"] = str(uuid.uuid4())[:8].upper()

    sub_id = data["submission_id"]
    init_db()

    key_factors = data.get("asa_key_factors", [])
    if isinstance(key_factors, list):
        key_factors = ", ".join(key_factors)

    conn = _connection()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO submissions (
            submission_id, submitted_at, status,
            first_name, last_name, dob, age, phone, email,
            chief_complaint, hpi, pmh, psh, sochx, fhx,
            medications, allergies, prior_screening,
            pcp_name, pcp_address, pcp_phone, pcp_fax,
            has_insurance, insurance_type, insurance_carrier,
            policy_holder, policy_holder_name, policy_holder_dob,
            insurance_result, insurance_message, pay_label, payment_type,
            asa_class, asa_reasoning, asa_key_factors, is_candidate,
            patient_decision, video_watched, location_preference,
            full_json
        ) VALUES (
            %s, %s, %s,
            %s, %s, %s, %s, %s, %s,
            %s, %s, %s, %s, %s, %s,
            %s, %s, %s,
            %s, %s, %s, %s,
            %s, %s, %s,
            %s, %s, %s,
            %s, %s, %s, %s,
            %s, %s, %s, %s,
            %s, %s, %s,
            %s
        )
        ON CONFLICT (submission_id) DO UPDATE SET
            status              = EXCLUDED.status,
            patient_decision    = EXCLUDED.patient_decision,
            video_watched       = EXCLUDED.video_watched,
            location_preference = EXCLUDED.location_preference,
            full_json           = EXCLUDED.full_json
    """, (
        sub_id,
        data.get("submitted_at", datetime.now().isoformat()),
        data.get("status", ""),
        data.get("first_name"), data.get("last_name"), data.get("dob"),
        data.get("age"), data.get("phone"), data.get("email"),
        data.get("chief_complaint"), data.get("hpi"),
        data.get("pmh"), data.get("psh"), data.get("sochx"), data.get("fhx"),
        data.get("medications"), data.get("allergies"), data.get("prior_screening"),
        data.get("pcp_name"), data.get("pcp_address"), data.get("pcp_phone"), data.get("pcp_fax"),
        1 if data.get("has_insurance") else 0,
        data.get("insurance_type"), data.get("insurance_carrier"),
        data.get("policy_holder"), data.get("policy_holder_name"), data.get("policy_holder_dob"),
        data.get("insurance_result"), data.get("insurance_message"),
        data.get("pay_label"), data.get("payment_type"),
        data.get("asa_class"), data.get("asa_reasoning"), key_factors,
        1 if data.get("is_candidate") else 0,
        data.get("patient_decision"),
        1 if data.get("video_watched") else 0,
        data.get("location_preference"),
        json.dumps(data, default=str),
    ))
    conn.commit()
    cur.close()
    conn.close()

    return sub_id


def list_submissions(limit: int = 100) -> list:
    init_db()
    conn = _connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute(
        "SELECT * FROM submissions ORDER BY submitted_at DESC LIMIT %s", (limit,)
    )
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return [dict(r) for r in rows]
