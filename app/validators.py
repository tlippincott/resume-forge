"""
Validation functions for user input.

This module contains business logic for validating bullets and role names.
Previously in ui/bullet_editor_helpers.py.
"""

from typing import Optional, Tuple, List
from app.text_processors import text_to_bullets


def validate_bullet(bullet: str, line_num: int) -> Optional[str]:
    """
    Validate a single bullet point.

    Args:
        bullet: The bullet text to validate
        line_num: Line number for error messages (1-indexed)

    Returns:
        Error message if invalid, None if valid

    Validation rules:
        - Maximum 250 characters
        - Should not end with a period
        - Empty bullets are filtered out (not errors)

    Example:
        >>> validate_bullet("Great bullet point", 1)
        None
        >>> validate_bullet("Bullet with period.", 1)
        'Line 1: Bullet should not end with a period'
    """
    if not bullet or not bullet.strip():
        return None  # Empty bullets are filtered out, not errors

    # Check length
    if len(bullet) > 250:
        return f"Line {line_num}: Bullet exceeds 250 characters ({len(bullet)} chars)"

    # Check for period at end
    if bullet.rstrip().endswith('.'):
        return f"Line {line_num}: Bullet should not end with a period"

    return None


def validate_bullets_text(bullets_text: str) -> Tuple[bool, List[str]]:
    """
    Validate all bullets in newline-separated text.

    Args:
        bullets_text: Newline-separated bullet text

    Returns:
        Tuple of (is_valid, list_of_error_messages)

    Example:
        >>> validate_bullets_text("Good bullet\\nAnother good one")
        (True, [])
        >>> validate_bullets_text("Bad bullet.")
        (False, ['Line 1: Bullet should not end with a period'])
    """
    if not bullets_text or not bullets_text.strip():
        return True, []  # Empty is valid

    lines = bullets_text.split('\n')
    errors = []

    for i, line in enumerate(lines, start=1):
        error = validate_bullet(line, i)
        if error:
            errors.append(error)

    return len(errors) == 0, errors


def validate_role_name(role: str) -> Tuple[bool, str]:
    """
    Validate role name.

    Args:
        role: Role name to validate

    Returns:
        Tuple of (is_valid, error_message)

    Validation rules:
        - Must not be empty
        - Minimum 2 characters
        - Maximum 100 characters

    Example:
        >>> validate_role_name("Help Desk")
        (True, '')
        >>> validate_role_name("A")
        (False, 'Role name must be at least 2 characters')
    """
    if not role or not role.strip():
        return False, "Role name cannot be empty"

    if len(role.strip()) < 2:
        return False, "Role name must be at least 2 characters"

    if len(role.strip()) > 100:
        return False, "Role name must be at most 100 characters"

    return True, ""


def count_bullets(bullets_text: str) -> int:
    """
    Count non-empty bullets in text.

    Args:
        bullets_text: Newline-separated bullet text

    Returns:
        Number of non-empty bullets

    Example:
        >>> count_bullets("bullet 1\\nbullet 2\\n\\nbullet 3")
        3
    """
    bullets = text_to_bullets(bullets_text)
    return len(bullets)


def get_validation_summary(bullets_text: str) -> str:
    """
    Get validation summary for display.

    Args:
        bullets_text: Newline-separated bullet text

    Returns:
        Summary string like "✓ All bullets valid" or "⚠ 3 validation error(s)"

    Example:
        >>> get_validation_summary("Good bullet\\nAnother good one")
        '✓ All bullets valid'
        >>> get_validation_summary("Bad bullet.")
        '⚠ 1 validation error(s)'
    """
    is_valid, errors = validate_bullets_text(bullets_text)

    if is_valid:
        return "✓ All bullets valid"
    else:
        return f"⚠ {len(errors)} validation error(s)"
