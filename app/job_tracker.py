"""
Job Application Tracker — SQLite data-access layer.

Database is stored at <project_root>/applications/job_applications.db.
No Gradio imports.
"""

import sqlite3
from datetime import date, datetime
from pathlib import Path

_DB_DIR = Path(__file__).parent.parent / "applications"
_DB_PATH = _DB_DIR / "job_applications.db"


def init_db() -> None:
    """Create the database and table if they do not exist."""
    _DB_DIR.mkdir(exist_ok=True)
    with sqlite3.connect(_DB_PATH) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS applications (
                id                    INTEGER PRIMARY KEY AUTOINCREMENT,
                applied_date          TEXT NOT NULL,
                company_name          TEXT NOT NULL,
                job_title             TEXT NOT NULL,
                job_description       TEXT,
                resume_pdf_path       TEXT,
                cover_letter_pdf_path TEXT,
                rejection_date        TEXT,
                interview_date        TEXT,
                notes                 TEXT,
                created_at            TEXT DEFAULT (datetime('now'))
            )
        """)
        conn.commit()


def save_application(
    applied_date: str,
    company_name: str,
    job_title: str,
    job_description: str | None = None,
    resume_pdf_path: str | None = None,
    cover_letter_pdf_path: str | None = None,
    notes: str | None = None,
) -> int:
    """Insert a new application row and return its id."""
    with sqlite3.connect(_DB_PATH) as conn:
        cursor = conn.execute(
            """
            INSERT INTO applications
                (applied_date, company_name, job_title, job_description,
                 resume_pdf_path, cover_letter_pdf_path, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (applied_date, company_name, job_title, job_description,
             resume_pdf_path, cover_letter_pdf_path, notes),
        )
        conn.commit()
        return cursor.lastrowid


def update_rejection(app_id: int, rejection_date: str) -> None:
    """Set rejection_date for the given application."""
    with sqlite3.connect(_DB_PATH) as conn:
        conn.execute(
            "UPDATE applications SET rejection_date = ? WHERE id = ?",
            (rejection_date, app_id),
        )
        conn.commit()


def update_interview(app_id: int, interview_date: str) -> None:
    """Set interview_date for the given application."""
    with sqlite3.connect(_DB_PATH) as conn:
        conn.execute(
            "UPDATE applications SET interview_date = ? WHERE id = ?",
            (interview_date, app_id),
        )
        conn.commit()


def update_pdf_paths(
    app_id: int,
    resume_pdf_path: str | None,
    cover_letter_pdf_path: str | None,
) -> None:
    """Update archived PDF paths for an application."""
    with sqlite3.connect(_DB_PATH) as conn:
        conn.execute(
            "UPDATE applications SET resume_pdf_path = ?, cover_letter_pdf_path = ? WHERE id = ?",
            (resume_pdf_path, cover_letter_pdf_path, app_id),
        )
        conn.commit()


def _compute_status(row: dict) -> str:
    """Compute human-readable status from row fields."""
    if row.get("interview_date"):
        return "Interview Scheduled"
    if row.get("rejection_date"):
        return "Rejected"
    try:
        applied = datetime.strptime(row["applied_date"], "%m-%d-%Y").date()
        days = (date.today() - applied).days
    except (ValueError, TypeError):
        return "Pending"
    if days >= 90:
        return "No Response (90+ days)"
    if days >= 60:
        return "No Response (60+ days)"
    if days >= 30:
        return "No Response (30+ days)"
    return "Pending"


def _row_to_dict(row: sqlite3.Row) -> dict:
    d = dict(row)
    d["status"] = _compute_status(d)
    try:
        applied = datetime.strptime(d["applied_date"], "%m-%d-%Y").date()
        d["days_pending"] = (date.today() - applied).days
    except (ValueError, TypeError):
        d["days_pending"] = 0
    return d


def list_applications() -> list[dict]:
    """Return all applications with computed status and days_pending, newest first."""
    with sqlite3.connect(_DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.execute(
            "SELECT * FROM applications ORDER BY id DESC"
        )
        return [_row_to_dict(row) for row in cursor.fetchall()]


def get_application(app_id: int) -> dict | None:
    """Return a single application by id, or None if not found."""
    with sqlite3.connect(_DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.execute(
            "SELECT * FROM applications WHERE id = ?", (app_id,)
        )
        row = cursor.fetchone()
        return _row_to_dict(row) if row else None
