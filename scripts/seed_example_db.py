"""
Seed script — creates applications/job_applications.db with fake example data.

Run from the project root:
    python scripts/seed_example_db.py

This is safe to re-run: it drops and recreates the table so the fake rows
are always the same. It does NOT touch an existing database that contains
real data unless you pass --force.
"""

import argparse
import sqlite3
import sys
from pathlib import Path

_DB_DIR = Path(__file__).parent.parent / "applications"
_DB_PATH = _DB_DIR / "job_applications.db"

EXAMPLE_ROWS = [
    {
        "applied_date": "01-15-2026",
        "company_name": "Acme Corp",
        "job_title": "Software Developer",
        "job_description": "Full-stack Python/React role building internal tooling.",
        "resume_pdf_path": None,
        "cover_letter_pdf_path": None,
        "rejection_date": None,
        "interview_date": "02-03-2026",
        "notes": "Referred by Jane Doe.",
        "created_at": "2026-01-15 09:00:00",
    },
    {
        "applied_date": "01-22-2026",
        "company_name": "Globex Solutions",
        "job_title": "Software Analyst",
        "job_description": "Data pipeline work with Python and SQL.",
        "resume_pdf_path": None,
        "cover_letter_pdf_path": None,
        "rejection_date": "02-10-2026",
        "interview_date": None,
        "notes": "Position was filled internally.",
        "created_at": "2026-01-22 14:30:00",
    },
    {
        "applied_date": "02-01-2026",
        "company_name": "Initech Technologies",
        "job_title": "Sales Engineer",
        "job_description": "Pre-sales technical demos for enterprise SaaS product.",
        "resume_pdf_path": None,
        "cover_letter_pdf_path": None,
        "rejection_date": None,
        "interview_date": None,
        "notes": "",
        "created_at": "2026-02-01 10:15:00",
    },
    {
        "applied_date": "02-14-2026",
        "company_name": "Umbrella Analytics",
        "job_title": "Software Developer",
        "job_description": "Backend services in Python, Kubernetes deployment.",
        "resume_pdf_path": None,
        "cover_letter_pdf_path": None,
        "rejection_date": None,
        "interview_date": None,
        "notes": "Remote-friendly team.",
        "created_at": "2026-02-14 08:45:00",
    },
]


def seed(force: bool = False) -> None:
    if _DB_PATH.exists() and not force:
        print(
            f"Database already exists at {_DB_PATH}.\n"
            "Pass --force to overwrite it with example data."
        )
        sys.exit(0)

    _DB_DIR.mkdir(exist_ok=True)

    with sqlite3.connect(_DB_PATH) as conn:
        conn.execute("DROP TABLE IF EXISTS applications")
        conn.execute("""
            CREATE TABLE applications (
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

        for row in EXAMPLE_ROWS:
            conn.execute(
                """
                INSERT INTO applications
                    (applied_date, company_name, job_title, job_description,
                     resume_pdf_path, cover_letter_pdf_path,
                     rejection_date, interview_date, notes, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    row["applied_date"],
                    row["company_name"],
                    row["job_title"],
                    row["job_description"],
                    row["resume_pdf_path"],
                    row["cover_letter_pdf_path"],
                    row["rejection_date"],
                    row["interview_date"],
                    row["notes"],
                    row["created_at"],
                ),
            )

        conn.commit()

    print(f"Seeded {len(EXAMPLE_ROWS)} example rows into {_DB_PATH}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Seed the job applications database with example data.")
    parser.add_argument(
        "--force",
        action="store_true",
        help="Overwrite an existing database.",
    )
    args = parser.parse_args()
    seed(force=args.force)
