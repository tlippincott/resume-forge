"""Helper functions for resume editing, preview, and PDF generation."""

import re
from pathlib import Path
from datetime import datetime
from app.render import render_html_to_pdf


def build_html_bullets(bullet_list: list[str]) -> str:
    """Convert ['bullet 1', 'bullet 2'] to '<li>bullet 1</li>\n<li>bullet 2</li>'."""
    if not bullet_list:
        return ""

    # Filter empties, wrap in <li> tags, join with newlines
    bullets = [f"<li>{bullet.strip()}</li>" for bullet in bullet_list if bullet.strip()]
    return "\n".join(bullets)


def bullets_to_text(bullet_list: list[str]) -> str:
    """Convert ['bullet 1', 'bullet 2'] to 'bullet 1\nbullet 2' for textbox."""
    if not bullet_list:
        return ""

    return "\n".join(bullet.strip() for bullet in bullet_list if bullet.strip())


def text_to_bullets(text: str) -> list[str]:
    """Convert 'bullet 1\nbullet 2\n\nbullet 3' to ['bullet 1', 'bullet 2', 'bullet 3']."""
    if not text or not text.strip():
        return []

    # Split on newlines, strip, filter empties
    return [line.strip() for line in text.split('\n') if line.strip()]


def load_resume_html(summary: str, spins_html: str,
                     programmer_html: str, analyst_html: str) -> str:
    """Load template, substitute placeholders, return complete HTML."""
    template_path = Path(__file__).parent.parent / "templates" / "resume.html"
    css_path = Path(__file__).parent.parent / "templates" / "resume_style.css"

    if not template_path.exists():
        raise FileNotFoundError(f"Template not found: {template_path}")

    # Read template
    with open(template_path, 'r', encoding='utf-8') as f:
        html_content = f.read()

    # Read CSS and inline it
    if css_path.exists():
        with open(css_path, 'r', encoding='utf-8') as f:
            css_content = f.read()

        # Replace CSS link with inline style
        html_content = html_content.replace(
            '<link rel="stylesheet" href="resume_style.css">',
            f'<style>{css_content}</style>'
        )

    # Replace placeholders
    html_content = html_content.replace("{summary}", summary or "")
    html_content = html_content.replace("{spins}", spins_html or "")
    html_content = html_content.replace("{programmer}", programmer_html or "")
    html_content = html_content.replace("{analyst}", analyst_html or "")

    return html_content


def generate_pdf_file(html_content: str) -> str:
    """Generate PDF from HTML, return absolute file path."""
    # Create timestamp filename
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"resume_{timestamp}.pdf"

    # Ensure output directory exists
    output_dir = Path(__file__).parent.parent / "output"
    output_dir.mkdir(exist_ok=True)

    # Create full path
    filepath = output_dir / filename

    # Generate PDF
    render_html_to_pdf(html_content, str(filepath))

    # Return absolute path
    return str(filepath.absolute())
