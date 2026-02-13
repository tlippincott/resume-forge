"""
Text processing functions for bullet manipulation.

This module contains business logic for converting between text representations
and bullet lists. Previously in ui/resume_helpers.py.
"""

from typing import List


def text_to_bullets(text: str) -> List[str]:
    """
    Convert newline-separated text to bullet list.

    Filters out empty lines and strips whitespace.

    Args:
        text: Newline-separated bullet text (e.g., "bullet 1\\nbullet 2\\n\\nbullet 3")

    Returns:
        List of bullet strings (e.g., ['bullet 1', 'bullet 2', 'bullet 3'])

    Example:
        >>> text_to_bullets("bullet 1\\nbullet 2\\n\\nbullet 3")
        ['bullet 1', 'bullet 2', 'bullet 3']
    """
    if not text or not text.strip():
        return []

    # Split on newlines, strip, filter empties
    return [line.strip() for line in text.split('\n') if line.strip()]


def bullets_to_text(bullet_list: List[str]) -> str:
    """
    Convert bullet list to newline-separated text.

    Filters out empty bullets and strips whitespace.

    Args:
        bullet_list: List of bullet strings (e.g., ['bullet 1', 'bullet 2'])

    Returns:
        Newline-separated text (e.g., "bullet 1\\nbullet 2")

    Example:
        >>> bullets_to_text(['bullet 1', 'bullet 2'])
        'bullet 1\\nbullet 2'
    """
    if not bullet_list:
        return ""

    return "\n".join(bullet.strip() for bullet in bullet_list if bullet.strip())
