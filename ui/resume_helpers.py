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


def load_resume_html(summary: str, spins_html: str, programmer_html: str, analyst_html: str) -> str:
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


def load_cover_letter_html(cover_letter_body: str) -> str:
    """Load cover letter template, substitute placeholder, return complete HTML."""
    template_path = Path(__file__).parent.parent / "templates" / "cover_letter.html"
    css_path = Path(__file__).parent.parent / "templates" / "cover_style.css"

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
            '<link rel="stylesheet" href="cover_style.css">',
            f'<style>{css_content}</style>'
        )

    # Replace placeholder
    html_content = html_content.replace("{cover_letter_body}", cover_letter_body or "")

    return html_content


def generate_cover_letter_pdf_file(html_content: str) -> str:
    """Generate cover letter PDF from HTML, return absolute file path."""
    # Create timestamp filename
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"cover_letter_{timestamp}.pdf"

    # Ensure output directory exists
    output_dir = Path(__file__).parent.parent / "output"
    output_dir.mkdir(exist_ok=True)

    # Create full path
    filepath = output_dir / filename

    # Generate PDF
    render_html_to_pdf(html_content, str(filepath))

    # Return absolute path
    return str(filepath.absolute())


def list_gap_files() -> list[tuple[str, str]]:
    """
    List available gap explanation files from gap_libs/ directory.

    Returns:
        List of tuples: [(display_name, file_path), ...]
        Example: [("Help Desk", "gap_libs/help_desk_gap.json"), ...]
    """
    gap_path = Path(__file__).parent.parent / "gap_libs"
    if not gap_path.exists():
        return []

    files = []
    for f in gap_path.iterdir():
        if f.is_file() and f.suffix == '.json' and f.name.endswith('_gap.json'):
            # Convert "help_desk_gap" → "Help Desk"
            display_name = f.stem.replace('_gap', '').replace('_', ' ').title()
            files.append((display_name, str(f)))

    return sorted(files, key=lambda x: x[0])


def load_gap_explanation(gap_file_path: str) -> str:
    """
    Load gap explanation paragraph from JSON file.

    Args:
        gap_file_path: Absolute path to gap JSON file

    Returns:
        Gap explanation paragraph text, or empty string if file doesn't exist/is invalid
    """
    import json

    if not gap_file_path or not Path(gap_file_path).exists():
        return ""

    try:
        with open(gap_file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return data.get("gap_explanation", "")
    except (json.JSONDecodeError, KeyError, FileNotFoundError):
        return ""


def derive_gap_file_from_bullet_file(bullet_file_path: str) -> str:
    """
    Derive gap file path from bullet file path.

    Args:
        bullet_file_path: Path to bullet JSON file (e.g., "bullet_libs/help_desk.json")

    Returns:
        Path to matching gap file (e.g., "gap_libs/help_desk_gap.json")
        Returns empty string if derivation fails
    """
    if not bullet_file_path:
        return ""

    bullet_path = Path(bullet_file_path)
    base_name = bullet_path.stem  # e.g., "help_desk"

    # Construct gap file path
    gap_file = Path(__file__).parent.parent / "gap_libs" / f"{base_name}_gap.json"

    return str(gap_file) if gap_file.exists() else ""


# ===== INTELLIGENCE-AWARE HELPER FUNCTIONS =====

def get_bullet_by_text(bullet_text: str, analyzed_bullets: list) -> dict:
    """
    Retrieve full bullet intelligence by text.

    Args:
        bullet_text: Bullet text string
        analyzed_bullets: List of analyzed bullet dicts

    Returns:
        Full bullet dict with intelligence, or empty dict if not found
    """
    for bullet in analyzed_bullets:
        if bullet.get("text") == bullet_text:
            return bullet
    return {}


def replace_bullet_in_list(bullets: list, target_index: int, replacement_bullet: dict) -> list:
    """
    Replace bullet at target_index with replacement_bullet.

    Args:
        bullets: List[Dict] - Current bullet list with intelligence
        target_index: int - Index to replace (0-based)
        replacement_bullet: Dict - New bullet with full intelligence

    Returns:
        List[Dict] - Updated bullet list
    """
    if 0 <= target_index < len(bullets):
        bullets[target_index] = replacement_bullet
    return bullets


def extract_bullet_texts(bullets_with_intelligence: list) -> list:
    """Extract just the text from intelligence-enriched bullets."""
    return [b.get("text", "") if isinstance(b, dict) else b for b in bullets_with_intelligence]
