"""
HTML generation functions for bullet formatting.

This module contains business logic for converting bullets to HTML.
Previously in ui/resume_helpers.py.
"""

import html
from typing import List


def build_html_bullets(bullet_list: List[str]) -> str:
    """
    Convert bullet list to HTML list items.

    Args:
        bullet_list: List of bullet strings

    Returns:
        HTML string with <li> tags

    Example:
        >>> build_html_bullets(['First bullet', 'Second bullet'])
        '<li>First bullet</li>\\n<li>Second bullet</li>'
    """
    if not bullet_list:
        return ""

    # Filter empties, wrap in <li> tags, join with newlines
    bullets = [
        f"<li>{html.escape(bullet.strip())}</li>"
        for bullet in bullet_list
        if bullet.strip()
    ]
    return "\n".join(bullets)
