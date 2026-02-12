"""Helper functions for bullet library editor."""

import json
import re
from pathlib import Path
from typing import Optional, Tuple, List
from ui.resume_helpers import text_to_bullets, bullets_to_text


def validate_bullet(bullet: str, line_num: int) -> Optional[str]:
    """
    Validate a single bullet point.

    Args:
        bullet: The bullet text to validate
        line_num: Line number for error messages (1-indexed)

    Returns:
        Error message if invalid, None if valid
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
    """
    if not role or not role.strip():
        return False, "Role name cannot be empty"

    if len(role.strip()) < 2:
        return False, "Role name must be at least 2 characters"

    if len(role.strip()) > 100:
        return False, "Role name must be at most 100 characters"

    return True, ""


def load_bullet_library(file_path: str) -> Tuple[str, str, str]:
    """
    Load bullet library from JSON file.

    Args:
        file_path: Absolute path to JSON file

    Returns:
        Tuple of (role, bullets_text, status_message)
    """
    try:
        path = Path(file_path)
        if not path.exists():
            return "", "", f"Error: File not found: {file_path}"

        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        # Extract role and bullets
        role = data.get("role", "")
        bullets = data.get("bullets", [])

        # Convert to text
        bullets_text = bullets_to_text(bullets)

        bullet_count = len(text_to_bullets(bullets_text))
        return role, bullets_text, f"✓ Loaded {bullet_count} bullets from {path.name}"

    except json.JSONDecodeError as e:
        return "", "", f"Error: Invalid JSON in file: {str(e)}"
    except Exception as e:
        return "", "", f"Error loading file: {str(e)}"


def save_bullet_library(file_path: str, role: str, bullets_text: str) -> Tuple[bool, str]:
    """
    Save bullet library to JSON file.

    Args:
        file_path: Absolute path to JSON file
        role: Role name
        bullets_text: Newline-separated bullet text

    Returns:
        Tuple of (success, status_message)
    """
    # Validate role
    role_valid, role_error = validate_role_name(role)
    if not role_valid:
        return False, f"Error: {role_error}"

    # Validate bullets
    bullets_valid, bullet_errors = validate_bullets_text(bullets_text)
    if not bullets_valid:
        error_list = "\n".join(bullet_errors[:5])  # Show first 5 errors
        if len(bullet_errors) > 5:
            error_list += f"\n... and {len(bullet_errors) - 5} more errors"
        return False, f"Validation failed:\n{error_list}"

    # Convert text to bullets array
    bullets = text_to_bullets(bullets_text)

    if len(bullets) == 0:
        return False, "Error: Cannot save empty bullet library"

    # Build JSON data
    data = {
        "role": role.strip(),
        "bullets": bullets
    }

    # Save to file
    try:
        path = Path(file_path)
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        return True, f"✓ Saved {len(bullets)} bullets to {path.name}"

    except Exception as e:
        return False, f"Error saving file: {str(e)}"


def create_new_bullet_library(role: str) -> Tuple[bool, str, str]:
    """
    Create a new bullet library file.

    Args:
        role: Role name for the new library

    Returns:
        Tuple of (success, file_path, status_message)
    """
    # Validate role name
    role_valid, role_error = validate_role_name(role)
    if not role_valid:
        return False, "", f"Error: {role_error}"

    # Generate filename: lowercase with underscores
    filename = role.strip().lower().replace(' ', '_')
    # Remove any non-alphanumeric characters except underscores
    filename = re.sub(r'[^a-z0-9_]', '', filename)
    filename = f"{filename}.json"

    # Build full path
    bullet_libs_dir = Path(__file__).parent.parent / "bullet_libs"
    bullet_libs_dir.mkdir(exist_ok=True)
    file_path = bullet_libs_dir / filename

    # Check if file already exists
    if file_path.exists():
        return False, "", f"Error: File already exists: {filename}"

    # Create new file with empty bullets
    data = {
        "role": role.strip(),
        "bullets": []
    }

    try:
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        return True, str(file_path), f"✓ Created new library: {filename}"

    except Exception as e:
        return False, "", f"Error creating file: {str(e)}"


def count_bullets(bullets_text: str) -> int:
    """
    Count non-empty bullets in text.

    Args:
        bullets_text: Newline-separated bullet text

    Returns:
        Number of non-empty bullets
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
    """
    is_valid, errors = validate_bullets_text(bullets_text)

    if is_valid:
        return "✓ All bullets valid"
    else:
        return f"⚠ {len(errors)} validation error(s)"
