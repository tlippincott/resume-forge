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
