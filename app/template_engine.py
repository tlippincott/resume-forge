"""
Template loading and rendering functions.

This module contains business logic for loading HTML templates and
substituting placeholders.
"""

import html
import json
from pathlib import Path
from app.exceptions import FileOperationError
from app.logging_config import get_logger

logger = get_logger(__name__)

_TECHNICAL_SKILLS_CONFIG = Path(__file__).parent.parent / "config" / "technical_skills.json"


def build_technical_skills_html(role: str = "General") -> str:
    """
    Build the TECHNICAL SKILLS HTML block for the resume template.

    Loads section content and role-specific ordering from technical_skills.json.
    Falls back to "General" ordering if the role is not found.

    Args:
        role: Role type (e.g. "Programmer", "Analyst", "Help Desk")

    Returns:
        HTML string with all tech-skills-group divs in role-appropriate order
    """
    try:
        with open(_TECHNICAL_SKILLS_CONFIG, 'r', encoding='utf-8') as f:
            config = json.load(f)
    except (IOError, json.JSONDecodeError) as e:
        logger.warning(f"Could not load technical_skills.json: {e}")
        return ""

    sections = config.get("sections", {})
    role_ordering = config.get("role_ordering", {})
    order = role_ordering.get(role, role_ordering.get("General", []))

    parts = []
    for key in order:
        section = sections.get(key)
        if not section:
            continue
        heading = html.escape(section.get("heading", key))
        bullets = section.get("bullets", [])
        li_items = "\n        ".join(
            f"<li>{html.escape(b)}</li>" for b in bullets
        )
        parts.append(
            f'<div class="tech-skills-group">\n'
            f'  <p class="skills"><span class="strong">{heading}:</span></p>\n'
            f'  <ul>\n'
            f'    {li_items}\n'
            f'  </ul>\n'
            f'</div>'
        )

    return "\n".join(parts)


def load_resume_html(
    summary: str,
    spins_html: str,
    programmer_html: str,
    analyst_html: str,
    role: str = "General"
) -> str:
    """
    Load resume template and substitute placeholders.

    Args:
        summary: Professional summary text
        spins_html: HTML for SPINS section
        programmer_html: HTML for programmer section
        analyst_html: HTML for analyst section
        role: Role type for technical skills ordering (default "General")

    Returns:
        Complete HTML document with substitutions

    Raises:
        FileOperationError: If template files are missing
    """
    template_path = Path(__file__).parent.parent / "templates" / "resume.html"
    css_path = Path(__file__).parent.parent / "templates" / "resume_style.css"

    if not template_path.exists():
        logger.error(f"Resume template not found: {template_path}")
        raise FileOperationError(f"Template not found: {template_path}")

    # Read template
    try:
        with open(template_path, 'r', encoding='utf-8') as f:
            html_content = f.read()
    except IOError as e:
        logger.error(f"Error reading template: {e}")
        raise FileOperationError(f"Error reading template: {e}")

    # Read CSS and inline it
    if css_path.exists():
        try:
            with open(css_path, 'r', encoding='utf-8') as f:
                css_content = f.read()

            # Replace CSS link with inline style
            html_content = html_content.replace(
                '<link rel="stylesheet" href="resume_style.css">',
                f'<style>{css_content}</style>'
            )
        except IOError as e:
            logger.warning(f"Error reading CSS file: {e}")
            # Continue without CSS

    # Replace placeholders
    html_content = html_content.replace("{summary}", html.escape(summary or ""))
    html_content = html_content.replace("{spins}", spins_html or "")
    html_content = html_content.replace("{programmer}", programmer_html or "")
    html_content = html_content.replace("{analyst}", analyst_html or "")
    html_content = html_content.replace("{technical_skills}", build_technical_skills_html(role))

    logger.debug("Resume HTML template loaded and substituted successfully")
    return html_content


def load_cover_letter_html(cover_letter_body: str) -> str:
    """
    Load cover letter template and substitute placeholder.

    Args:
        cover_letter_body: HTML paragraphs for cover letter body

    Returns:
        Complete HTML document with substitutions

    Raises:
        FileOperationError: If template files are missing
    """
    template_path = Path(__file__).parent.parent / "templates" / "cover_letter.html"
    css_path = Path(__file__).parent.parent / "templates" / "cover_style.css"

    if not template_path.exists():
        logger.error(f"Cover letter template not found: {template_path}")
        raise FileOperationError(f"Template not found: {template_path}")

    # Read template
    try:
        with open(template_path, 'r', encoding='utf-8') as f:
            html_content = f.read()
    except IOError as e:
        logger.error(f"Error reading template: {e}")
        raise FileOperationError(f"Error reading template: {e}")

    # Read CSS and inline it
    if css_path.exists():
        try:
            with open(css_path, 'r', encoding='utf-8') as f:
                css_content = f.read()

            # Replace CSS link with inline style
            html_content = html_content.replace(
                '<link rel="stylesheet" href="cover_style.css">',
                f'<style>{css_content}</style>'
            )
        except IOError as e:
            logger.warning(f"Error reading CSS file: {e}")
            # Continue without CSS

    # Replace placeholder
    html_content = html_content.replace("{cover_letter_body}", cover_letter_body or "")

    logger.debug("Cover letter HTML template loaded and substituted successfully")
    return html_content
