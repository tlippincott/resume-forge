"""
PDF archival for job applications.

Copies generated PDFs into applications/{id}_{safe_company}_{safe_title}/
so they are preserved even if the output files are later overwritten.
"""

import re
import shutil
from pathlib import Path

_ARCHIVE_DIR = Path(__file__).parent.parent / "applications"


def _safe_name(text: str) -> str:
    """Convert text to a filesystem-safe slug (max 30 chars)."""
    slug = re.sub(r"[^\w\s-]", "", text.lower())
    slug = re.sub(r"[\s_-]+", "_", slug).strip("_")
    return slug[:30]


def archive_pdfs(
    app_id: int,
    company_name: str,
    job_title: str,
    resume_src: str | None,
    cover_letter_src: str | None,
) -> tuple[str | None, str | None]:
    """
    Copy PDFs into the archive directory for this application.

    Returns:
        (resume_archive_path, cover_letter_archive_path) — either may be None
        if the source was not provided or did not exist.
    """
    safe_company = _safe_name(company_name) if company_name else "unknown"
    safe_title = _safe_name(job_title) if job_title else "unknown"
    dest_dir = _ARCHIVE_DIR / f"{app_id}_{safe_company}_{safe_title}"
    dest_dir.mkdir(parents=True, exist_ok=True)

    label = f"{app_id}_{safe_company}_{safe_title}"
    resume_dest = _copy_if_exists(resume_src, dest_dir / f"{label}_resume.pdf")
    cover_dest = _copy_if_exists(cover_letter_src, dest_dir / f"{label}_cover_letter.pdf")

    return resume_dest, cover_dest


def _copy_if_exists(src: str | None, dest: Path) -> str | None:
    if not src:
        return None
    src_path = Path(src)
    if not src_path.exists():
        return None
    shutil.copy2(src_path, dest)
    return str(dest)
