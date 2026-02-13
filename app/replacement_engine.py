"""
Intelligent bullet replacement engine.

This module contains business logic for generating and executing intelligent
bullet replacements. Previously scattered across 235 lines in ui/gradio_app.py.

Architecture:
- Returns structured data (dicts, not UI components)
- No Gradio imports
- Pure business logic testable without UI
"""

from typing import Dict, List, Any, Set, Tuple, Optional
from app.bullet_intelligence import suggest_replacements, generate_explanation
from app.data_extractors import replace_bullet_in_list, extract_bullet_texts
from app.text_processors import bullets_to_text
from app.exceptions import ValidationError
from app.logging_config import get_logger

logger = get_logger(__name__)


def get_replacement_suggestions(
    section_name: str,
    bullet_index: int,
    spins_list: List[Dict[str, Any]],
    programmer_list: List[Dict[str, Any]],
    analyst_list: List[Dict[str, Any]],
    analyzed_bullets: List[Dict[str, Any]],
    jd_analysis: Dict[str, Any],
    used_bullet_ids: Set[str]
) -> Dict[str, Any]:
    """
    Generate intelligent replacement suggestions.

    Args:
        section_name: Target section ("SPINS", "Programmer", "Analyst")
        bullet_index: 1-based bullet index in section
        spins_list: SPINS section bullets with intelligence
        programmer_list: Programmer section bullets with intelligence
        analyst_list: Analyst section bullets with intelligence
        analyzed_bullets: Full pool of analyzed bullets
        jd_analysis: Job description analysis
        used_bullet_ids: Set of bullet IDs currently in use

    Returns:
        Dict containing:
        - success: bool
        - error_message: str (if failed)
        - removed_bullet: dict (if successful)
        - suggestions: List[dict] (if successful)
        - target_section: str
        - target_index: int (0-based)
        - skills_coverage_warning: Optional[str]

    Raises:
        ValidationError: If bullet index is invalid
    """
    logger.info(f"Getting replacement suggestions for {section_name} bullet #{bullet_index}")

    # Convert 1-based to 0-based
    index = int(bullet_index) - 1

    # Get active section
    if section_name == "SPINS":
        active_list = spins_list
    elif section_name == "Programmer":
        active_list = programmer_list
    else:  # Analyst
        active_list = analyst_list

    # Validate index
    if index < 0 or index >= len(active_list):
        logger.warning(f"Invalid bullet index: {bullet_index}, section has {len(active_list)} bullets")
        raise ValidationError(
            f"Invalid bullet index: {bullet_index}. Section has {len(active_list)} bullets."
        )

    # Get removed bullet
    removed_bullet = active_list[index]
    removed_text = removed_bullet.get("text", str(removed_bullet))

    logger.debug(f"Removed bullet: {removed_text[:50]}...")

    # Get top 5 suggestions
    suggestions = suggest_replacements(
        removed_bullet=removed_bullet,
        all_bullets=analyzed_bullets,
        active_bullet_ids=used_bullet_ids,
        active_bullets=active_list,
        jd_analysis=jd_analysis
    )

    logger.info(f"Generated {len(suggestions)} replacement suggestions")

    # Check skills coverage (warning if top suggestion has high overlap)
    skills_coverage_warning = None
    if suggestions:
        top_bullet = suggestions[0]["bullet"]
        active_keywords = set()
        for b in active_list:
            active_keywords.update(b.get("keywords", []))

        top_keywords = set(top_bullet.get("keywords", []))
        overlap = top_keywords & active_keywords

        if len(overlap) >= 3:
            overlap_list = ', '.join(list(overlap)[:4])
            skills_coverage_warning = (
                f"Top suggestion shares {len(overlap)} skills with existing bullets: "
                f"{overlap_list}. Consider lower-ranked suggestions for better skill diversity."
            )
            logger.info(f"Skills coverage warning: {len(overlap)} overlapping skills")

    return {
        "success": True,
        "removed_bullet": removed_bullet,
        "suggestions": suggestions,
        "target_section": section_name,
        "target_index": index,
        "skills_coverage_warning": skills_coverage_warning
    }


def get_suggestion_explanation(
    selected_bullet_id: str,
    analyzed_bullets: List[Dict[str, Any]],
    jd_analysis: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Get explanation for a selected suggestion.

    Args:
        selected_bullet_id: Bullet ID of selected suggestion
        analyzed_bullets: Full pool of analyzed bullets
        jd_analysis: Job description analysis

    Returns:
        Dict containing:
        - success: bool
        - bullet: dict (if found)
        - explanation: str
        - error_message: str (if not found)
    """
    logger.debug(f"Getting explanation for bullet ID: {selected_bullet_id}")

    # Find selected bullet
    selected = None
    for bullet in analyzed_bullets:
        if bullet["bullet_id"] == selected_bullet_id:
            selected = bullet
            break

    if not selected:
        logger.warning(f"Bullet not found: {selected_bullet_id}")
        return {
            "success": False,
            "error_message": f"Bullet not found: {selected_bullet_id}"
        }

    explanation = generate_explanation(selected, {}, jd_analysis)

    return {
        "success": True,
        "bullet": selected,
        "explanation": explanation
    }


def execute_replacement(
    target_section: str,
    target_index: int,
    selected_bullet_id: str,
    spins_list: List[Dict[str, Any]],
    programmer_list: List[Dict[str, Any]],
    analyst_list: List[Dict[str, Any]],
    analyzed_bullets: List[Dict[str, Any]],
    used_bullet_ids: Set[str]
) -> Dict[str, Any]:
    """
    Execute intelligent bullet replacement.

    Args:
        target_section: Target section name
        target_index: 0-based bullet index in section
        selected_bullet_id: Bullet ID of replacement
        spins_list: SPINS section bullets with intelligence
        programmer_list: Programmer section bullets with intelligence
        analyst_list: Analyst section bullets with intelligence
        analyzed_bullets: Full pool of analyzed bullets
        used_bullet_ids: Set of bullet IDs currently in use

    Returns:
        Dict containing:
        - success: bool
        - error_message: str (if failed)
        - updated_spins: List[Dict] (if successful)
        - updated_programmer: List[Dict]
        - updated_analyst: List[Dict]
        - updated_used_ids: Set[str]
        - spins_text: str
        - programmer_text: str
        - analyst_text: str
        - replacement_bullet: dict

    Raises:
        ValidationError: If bullet ID not found
    """
    logger.info(f"Executing replacement in {target_section} at index {target_index} with bullet {selected_bullet_id}")

    # Find replacement bullet by ID
    replacement_bullet = None
    for bullet in analyzed_bullets:
        if bullet["bullet_id"] == selected_bullet_id:
            replacement_bullet = bullet
            break

    if not replacement_bullet:
        logger.error(f"Replacement bullet not found: {selected_bullet_id}")
        raise ValidationError(f"Could not find selected bullet: {selected_bullet_id}")

    # Update appropriate section
    if target_section == "SPINS":
        old_bullet = spins_list[target_index]
        updated_spins = replace_bullet_in_list(spins_list.copy(), target_index, replacement_bullet)
        updated_programmer = programmer_list
        updated_analyst = analyst_list
    elif target_section == "Programmer":
        old_bullet = programmer_list[target_index]
        updated_spins = spins_list
        updated_programmer = replace_bullet_in_list(programmer_list.copy(), target_index, replacement_bullet)
        updated_analyst = analyst_list
    else:  # Analyst
        old_bullet = analyst_list[target_index]
        updated_spins = spins_list
        updated_programmer = programmer_list
        updated_analyst = replace_bullet_in_list(analyst_list.copy(), target_index, replacement_bullet)

    # Update used bullet IDs
    updated_used_ids = used_bullet_ids.copy()
    updated_used_ids.discard(old_bullet.get("bullet_id", ""))
    updated_used_ids.add(replacement_bullet["bullet_id"])

    # Convert to text for UI display
    spins_text = bullets_to_text(extract_bullet_texts(updated_spins))
    programmer_text = bullets_to_text(extract_bullet_texts(updated_programmer))
    analyst_text = bullets_to_text(extract_bullet_texts(updated_analyst))

    logger.info(f"Replacement complete: {old_bullet.get('text', '')[:50]} → {replacement_bullet['text'][:50]}")

    return {
        "success": True,
        "updated_spins": updated_spins,
        "updated_programmer": updated_programmer,
        "updated_analyst": updated_analyst,
        "updated_used_ids": updated_used_ids,
        "spins_text": spins_text,
        "programmer_text": programmer_text,
        "analyst_text": analyst_text,
        "replacement_bullet": replacement_bullet,
        "old_bullet": old_bullet
    }
