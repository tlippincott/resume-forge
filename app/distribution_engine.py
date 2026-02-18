"""
Distribution Engine: Section Grouping

Groups analyzed bullets by their pre-designated sections.
Section assignments are read directly from bullet library JSON files;
no LLM classification is performed.
"""

from typing import List, Dict
from app.types import AnalyzedBullet
from app.config import config
from app.logging_config import get_logger

logger = get_logger(__name__)

VALID_SECTIONS = {"spins", "programmer", "analyst"}


def group_by_section(analyzed_bullets: List[AnalyzedBullet]) -> Dict[str, List[str]]:
    """
    Group analyzed bullets by their designated sections.

    Section counts are already guaranteed by select_bullets_by_section().

    Args:
        analyzed_bullets: List of analyzed bullets with 'section' and 'text' fields

    Returns:
        Dict mapping section names to bullet text lists:
        {"spins": [...], "programmer": [...], "analyst": [...]}
    """
    sections: Dict[str, List[str]] = {"spins": [], "programmer": [], "analyst": []}
    for bullet in analyzed_bullets:
        section = bullet.get("section", "analyst")
        if section in sections:
            sections[section].append(bullet["text"])
        else:
            logger.warning(f"Unknown section '{section}', routing to analyst")
            sections["analyst"].append(bullet["text"])

    logger.info(
        f"Grouped sections: spins={len(sections['spins'])}, "
        f"programmer={len(sections['programmer'])}, analyst={len(sections['analyst'])}"
    )
    return sections


def get_section_limits(section_name: str) -> tuple:
    """
    Get the exact bullet count for a section.

    Args:
        section_name: Name of the section

    Returns:
        Tuple of (count, count) — exact count used for both min and max

    Raises:
        KeyError: If section_name is not a valid section
    """
    counts = {
        "spins": config.business.spins_count,
        "programmer": config.business.programmer_count,
        "analyst": config.business.analyst_count,
    }
    count = counts[section_name]
    return count, count
