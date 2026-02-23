"""Helper functions for resume editing, preview, and PDF generation.

DEPRECATED: Most business logic has been moved to app layer.
This file now re-exports functions for backward compatibility.
"""

from app.text_processors import text_to_bullets, bullets_to_text
from app.data_extractors import (
    get_bullet_by_text,
    replace_bullet_in_list,
    extract_bullet_texts
)
from app.html_generators import build_html_bullets
from app.template_engine import load_resume_html, load_cover_letter_html
from app.pdf_generator import generate_pdf_file, generate_cover_letter_pdf_file
from app.gap_manager import list_gap_files, load_gap_explanation, derive_gap_file_from_bullet_file


# All functions are now imported from app layer modules above
# This file serves as a re-export shim for backward compatibility


def cover_letter_html_to_text(html_body: str) -> str:
    """Convert <p>...</p><p>...</p> body to plain paragraphs separated by blank lines."""
    import html as html_mod
    raw = html_body.replace("<p>", "").split("</p>")
    paragraphs = [html_mod.unescape(p.strip()) for p in raw if p.strip()]
    return "\n\n".join(paragraphs)


def cover_letter_text_to_html(text: str) -> str:
    """Convert plain paragraphs (blank-line separated) back to <p>...</p> body."""
    import html as html_mod
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    if not paragraphs:
        paragraphs = [p.strip() for p in text.split("\n") if p.strip()]
    escaped = [html_mod.escape(p) for p in paragraphs]
    return "<p>" + "</p><p>".join(escaped) + "</p>" if escaped else ""
