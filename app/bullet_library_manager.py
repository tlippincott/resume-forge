"""
Bullet library file management functions.

This module contains business logic for loading, saving, and creating
bullet library JSON files. Previously in ui/bullet_editor_helpers.py.
"""

import json
import re
from pathlib import Path
from typing import Tuple
from app.text_processors import text_to_bullets, bullets_to_text
from app.validators import validate_role_name, validate_bullets_text
from app.exceptions import FileOperationError, ValidationError
from app.logging_config import get_logger

logger = get_logger(__name__)


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

        # Convert to text
        bullets_text = bullets_to_text(bullets)

        bullet_count = len(text_to_bullets(bullets_text))
        logger.info(f"Loaded {bullet_count} bullets from {path.name}")
        return role, bullets_text, f"✓ Loaded {bullet_count} bullets from {path.name}"

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
