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


def rows_to_section_summary(rows: list) -> str:
    """Return '34 bullets (10 analyst, 12 programmer, 12 spins)' from [text, section] rows."""
    counts: dict = {}
    for row in (rows or []):
        if isinstance(row, (list, tuple)) and len(row) >= 2:
            section = str(row[1]).strip().lower()
            if section:
                counts[section] = counts.get(section, 0) + 1

    total = sum(counts.values())
    if total == 0:
        return "0 bullets"

    ordered = [f"{counts[s]} {s}" for s in sorted(VALID_SECTIONS) if s in counts]
    ordered += [f"{counts[s]} {s}" for s in sorted(counts) if s not in VALID_SECTIONS]
    return f"{total} bullets ({', '.join(ordered)})"


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


def load_bullet_library(file_path: str) -> Tuple[str, list, str]:
    """
    Load bullet library from JSON file.

    Args:
        file_path: Absolute path to JSON file

    Returns:
        Tuple of (role, rows, status_message) where rows = [[text, section], ...]
    """
    try:
        path = Path(file_path)
        if not path.exists():
            return "", [], f"Error: File not found: {file_path}"

        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        role = data.get("role", "")
        bullets = data.get("bullets", [])
        rows = []
        for b in bullets:
            if isinstance(b, dict):
                rows.append([b.get("text", ""), b.get("section", "")])
            else:
                rows.append([str(b), ""])   # legacy plain string — section blank

        logger.info(f"Loaded {len(rows)} bullets from {path.name}")
        return role, rows, f"Loaded {len(rows)} bullets from {path.name}"

    except json.JSONDecodeError as e:
        return "", [], f"Error: Invalid JSON in file: {str(e)}"
    except Exception as e:
        return "", [], f"Error loading file: {str(e)}"


def save_bullet_library(file_path: str, role: str, rows: list) -> Tuple[bool, str]:
    """
    Save bullet library to JSON file.

    Args:
        file_path: Absolute path to JSON file
        role: Role name
        rows: List of [text, section] rows from Dataframe

    Returns:
        Tuple of (success, status_message)
    """
    role_valid, role_error = validate_role_name(role)
    if not role_valid:
        return False, f"Error: {role_error}"

    # Filter blank rows (user left empty rows at bottom of table)
    non_empty = [r for r in (rows or []) if len(r) >= 2 and str(r[0]).strip()]
    if not non_empty:
        return False, "Error: Cannot save empty bullet library"

    bullets = []
    validation_errors = []
    for i, row in enumerate(non_empty):
        text = str(row[0]).strip()
        section = str(row[1]).strip().lower() if len(row) > 1 else ""
        item = {"text": text, "section": section}
        errs = validate_bullet_item(item, i)
        if errs:
            validation_errors.extend(errs)
        else:
            bullets.append(item)

    if validation_errors:
        shown = validation_errors[:10]
        if len(validation_errors) > 10:
            shown.append(f"... and {len(validation_errors) - 10} more errors")
        valid_str = ", ".join(sorted(VALID_SECTIONS))
        return False, (
            f"Validation failed ({len(validation_errors)} error(s)):\n"
            + "\n".join(shown)
            + f"\n\nValid sections: {valid_str}"
        )

    if not bullets:
        return False, "Error: No valid bullets to save after validation"

    data = {"role": role.strip(), "bullets": bullets}
    try:
        path = Path(file_path)
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        summary = rows_to_section_summary([[b["text"], b["section"]] for b in bullets])
        logger.info(f"Saved {len(bullets)} bullets to {path.name}")
        return True, f"Saved {len(bullets)} bullets to {path.name} — {summary}"
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
