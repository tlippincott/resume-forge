"""
Employment gap explanation management functions.

This module contains business logic for managing gap explanation files.
Previously in ui/resume_helpers.py.
"""

import json
from pathlib import Path
from typing import List, Tuple
from app.exceptions import FileOperationError
from app.logging_config import get_logger

logger = get_logger(__name__)


def list_gap_files() -> List[Tuple[str, str]]:
    """
    List available gap explanation files from gap_libs/ directory.

    Returns:
        List of tuples: [(display_name, file_path), ...]
        Example: [("Help Desk", "gap_libs/help_desk_gap.json"), ...]
    """
    gap_path = Path(__file__).parent.parent / "gap_libs"
    if not gap_path.exists():
        logger.warning("Gap libs directory does not exist")
        return []

    files = []
    for f in gap_path.iterdir():
        if f.is_file() and f.suffix == '.json' and f.name.endswith('_gap.json'):
            # Convert "help_desk_gap" → "Help Desk"
            display_name = f.stem.replace('_gap', '').replace('_', ' ').title()
            files.append((display_name, str(f)))

    logger.debug(f"Found {len(files)} gap explanation files")
    return sorted(files, key=lambda x: x[0])


def load_gap_explanation(gap_file_path: str) -> str:
    """
    Load gap explanation paragraph from JSON file.

    Args:
        gap_file_path: Absolute path to gap JSON file

    Returns:
        Gap explanation paragraph text, or empty string if file doesn't exist/is invalid
    """
    if not gap_file_path or not Path(gap_file_path).exists():
        logger.debug(f"Gap file not found or path empty: {gap_file_path}")
        return ""

    try:
        with open(gap_file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        gap_text = data.get("gap_explanation", "")
        logger.debug(f"Loaded gap explanation from {gap_file_path}")
        return gap_text
    except (json.JSONDecodeError, KeyError, FileNotFoundError) as e:
        logger.warning(f"Error loading gap explanation from {gap_file_path}: {e}")
        return ""


def derive_gap_file_from_bullet_file(bullet_file_path: str) -> str:
    """
    Derive gap file path from bullet file path.

    Args:
        bullet_file_path: Path to bullet JSON file (e.g., "bullet_libs/help_desk.json")

    Returns:
        Path to matching gap file (e.g., "gap_libs/help_desk_gap.json")
        Returns empty string if derivation fails or file doesn't exist
    """
    if not bullet_file_path:
        return ""

    bullet_path = Path(bullet_file_path)
    base_name = bullet_path.stem  # e.g., "help_desk"

    # Construct gap file path
    gap_file = Path(__file__).parent.parent / "gap_libs" / f"{base_name}_gap.json"

    if gap_file.exists():
        logger.debug(f"Derived gap file: {gap_file}")
        return str(gap_file)
    else:
        logger.debug(f"No matching gap file found for {bullet_file_path}")
        return ""
