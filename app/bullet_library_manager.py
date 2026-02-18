"""
Bullet library file management functions.

This module contains business logic for loading, saving, and creating
bullet library JSON files. Previously in ui/bullet_editor_helpers.py.
"""

import json
import re
from pathlib import Path
from typing import Any, List, Tuple
from app.text_processors import text_to_bullets, bullets_to_text
from app.validators import validate_role_name, validate_bullets_text
from app.exceptions import FileOperationError, ValidationError
from app.logging_config import get_logger

logger = get_logger(__name__)

VALID_SECTIONS = {"spins", "programmer", "analyst"}


def validate_bullet_item(item: Any, index: int) -> List[str]:
    """
    Validate a single bullet item from a bullet library.

    Args:
        item: The bullet item to validate
        index: Zero-based index in the bullets list (for error messages)

    Returns:
        List of error strings (empty if valid)
    """
    errors = []

    if isinstance(item, str):
        errors.append(f"Bullet {index}: legacy string format not allowed; use {{text, section}} dict")
        return errors

    if not isinstance(item, dict):
        errors.append(f"Bullet {index}: expected dict, got {type(item).__name__}")
        return errors

    text = item.get("text", "")
    if not text or not isinstance(text, str) or not text.strip():
        errors.append(f"Bullet {index}: missing or empty 'text' field")

    section = item.get("section")
    if section is None:
        errors.append(f"Bullet {index}: missing 'section' field")
    elif section not in VALID_SECTIONS:
        errors.append(
            f"Bullet {index}: invalid section '{section}'; must be one of {sorted(VALID_SECTIONS)}"
        )

    return errors


def validate_bullet_library(bullet_data: dict) -> Tuple[bool, List[str]]:
    """
    Validate a bullet library dict loaded from JSON.

    Args:
        bullet_data: Dict loaded from bullet library JSON file

    Returns:
        Tuple of (is_valid, error_messages)
    """
    all_errors: List[str] = []

    if not isinstance(bullet_data, dict) or "bullets" not in bullet_data:
        return False, ["Bullet library must be a dict with a 'bullets' key"]

    bullets = bullet_data["bullets"]
    if not isinstance(bullets, list):
        return False, ["'bullets' must be a list"]

    if not bullets:
        return False, ["'bullets' list is empty"]

    for i, item in enumerate(bullets):
        item_errors = validate_bullet_item(item, i)
        all_errors.extend(item_errors)
        if len(all_errors) >= 10:
            all_errors.append(f"... (stopping after 10 errors)")
            break

    return len(all_errors) == 0, all_errors


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
            logger.error(f"Bullet library file not found: {file_path}")
            return "", "", f"Error: File not found: {file_path}"

        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        # Extract role and bullets
        role = data.get("role", "")
        bullets = data.get("bullets", [])

        # Support new {text, section} format — extract text for display
        bullet_texts = [b["text"] if isinstance(b, dict) else b for b in bullets]

        # Convert to text
        bullets_text = bullets_to_text(bullet_texts)

        bullet_count = len(text_to_bullets(bullets_text))
        logger.info(f"Loaded {bullet_count} bullets from {path.name}")
        return role, bullets_text, f"Loaded {bullet_count} bullets from {path.name}"

    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in {file_path}: {e}")
        return "", "", f"Error: Invalid JSON in file: {str(e)}"
    except Exception as e:
        logger.error(f"Error loading bullet library {file_path}: {e}")
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
        logger.warning(f"Invalid role name: {role_error}")
        return False, f"Error: {role_error}"

    # Validate bullets
    bullets_valid, bullet_errors = validate_bullets_text(bullets_text)
    if not bullets_valid:
        error_list = "\n".join(bullet_errors[:5])  # Show first 5 errors
        if len(bullet_errors) > 5:
            error_list += f"\n... and {len(bullet_errors) - 5} more errors"
        logger.warning(f"Bullet validation failed: {len(bullet_errors)} errors")
        return False, f"Validation failed:\n{error_list}"

    # Convert text to bullets array
    bullets = text_to_bullets(bullets_text)

    if len(bullets) == 0:
        logger.warning("Attempted to save empty bullet library")
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

        logger.info(f"Saved {len(bullets)} bullets to {path.name}")
        return True, f"✓ Saved {len(bullets)} bullets to {path.name}"

    except Exception as e:
        logger.error(f"Error saving bullet library to {file_path}: {e}")
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
        logger.warning(f"Invalid role name for new library: {role_error}")
        return False, "", f"Error: {role_error}"

    # Generate filename: lowercase with underscores
    filename = role.strip().lower().replace(' ', '_')
    # Remove any non-alphanumeric characters except underscores
    filename = re.sub(r'[^a-z0-9_]', '', filename)
    filename = f"{filename}.json"

    # Build full path
    bullet_libs_dir = Path(__file__).parent.parent / "bullet_libs"
    try:
        bullet_libs_dir.mkdir(exist_ok=True)
    except OSError as e:
        logger.error(f"Error creating bullet_libs directory: {e}")
        return False, "", f"Error creating directory: {str(e)}"

    file_path = bullet_libs_dir / filename

    # Check if file already exists
    if file_path.exists():
        logger.warning(f"Attempted to create duplicate library: {filename}")
        return False, "", f"Error: File already exists: {filename}"

    # Create new file with empty bullets
    data = {
        "role": role.strip(),
        "bullets": []
    }

    try:
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        logger.info(f"Created new bullet library: {filename}")
        return True, str(file_path), f"✓ Created new library: {filename}"

    except Exception as e:
        logger.error(f"Error creating bullet library {filename}: {e}")
        return False, "", f"Error creating file: {str(e)}"
