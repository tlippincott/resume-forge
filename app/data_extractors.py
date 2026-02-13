"""
Data extraction and manipulation functions for bullet intelligence.

This module contains business logic for working with intelligence-enriched
bullet data structures. Previously in ui/resume_helpers.py.
"""

from typing import List, Dict, Any, Optional


def get_bullet_by_text(bullet_text: str, analyzed_bullets: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Retrieve full bullet intelligence by text.

    NOTE: This is a FRAGILE function that breaks if text is edited.
    Phase 3C will replace this with ID-based lookups.

    Args:
        bullet_text: Bullet text string
        analyzed_bullets: List of analyzed bullet dicts

    Returns:
        Full bullet dict with intelligence, or empty dict if not found

    Example:
        >>> analyzed = [{"text": "Fixed bugs", "bullet_id": "123", "keywords": ["python"]}]
        >>> get_bullet_by_text("Fixed bugs", analyzed)
        {'text': 'Fixed bugs', 'bullet_id': '123', 'keywords': ['python']}
    """
    for bullet in analyzed_bullets:
        if bullet.get("text") == bullet_text:
            return bullet
    return {}


def get_bullet_by_id(bullet_id: str, analyzed_bullets: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """
    Retrieve full bullet intelligence by ID (ROBUST - Phase 3C).

    This is the preferred way to lookup bullets. Unlike text-based lookup,
    this works even if the bullet text is edited.

    Args:
        bullet_id: Unique bullet identifier
        analyzed_bullets: List of analyzed bullet dicts

    Returns:
        Full bullet dict with intelligence, or None if not found

    Example:
        >>> analyzed = [{"text": "Fixed bugs", "bullet_id": "123", "keywords": ["python"]}]
        >>> get_bullet_by_id("123", analyzed)
        {'text': 'Fixed bugs', 'bullet_id': '123', 'keywords': ['python']}
    """
    for bullet in analyzed_bullets:
        if bullet.get("bullet_id") == bullet_id:
            return bullet
    return None


def replace_bullet_in_list(
    bullets: List[Dict[str, Any]],
    target_index: int,
    replacement_bullet: Dict[str, Any]
) -> List[Dict[str, Any]]:
    """
    Replace bullet at target_index with replacement_bullet.

    Args:
        bullets: Current bullet list with intelligence (List[Dict])
        target_index: Index to replace (0-based)
        replacement_bullet: New bullet with full intelligence (Dict)

    Returns:
        Updated bullet list

    Example:
        >>> bullets = [{"text": "Old", "bullet_id": "1"}]
        >>> new_bullet = {"text": "New", "bullet_id": "2"}
        >>> replace_bullet_in_list(bullets, 0, new_bullet)
        [{'text': 'New', 'bullet_id': '2'}]
    """
    if 0 <= target_index < len(bullets):
        bullets[target_index] = replacement_bullet
    return bullets


def extract_bullet_texts(bullets_with_intelligence: List[Any]) -> List[str]:
    """
    Extract just the text from intelligence-enriched bullets.

    Handles both Dict (with intelligence) and str (plain text) bullets.

    Args:
        bullets_with_intelligence: List of bullets (can be Dict or str)

    Returns:
        List of bullet text strings

    Example:
        >>> bullets = [
        ...     {"text": "Fixed bugs", "bullet_id": "123"},
        ...     "Plain text bullet"
        ... ]
        >>> extract_bullet_texts(bullets)
        ['Fixed bugs', 'Plain text bullet']
    """
    return [
        b.get("text", "") if isinstance(b, dict) else b
        for b in bullets_with_intelligence
    ]


def get_section_bullets(all_bullets: List[Dict[str, Any]], section: str) -> List[Dict[str, Any]]:
    """
    Get bullets for a specific section (view function for Phase 3).

    This is a view generator that filters bullets by section without
    modifying the canonical state.

    Args:
        all_bullets: Canonical bullet list with "section" field
        section: Section name ("spins", "programmer", "analyst")

    Returns:
        Bullets belonging to the specified section

    Example:
        >>> all_bullets = [
        ...     {"text": "A", "section": "spins"},
        ...     {"text": "B", "section": "programmer"}
        ... ]
        >>> get_section_bullets(all_bullets, "spins")
        [{'text': 'A', 'section': 'spins'}]
    """
    return [b for b in all_bullets if b.get("section") == section]


def bullets_to_display_text(bullets: List[Dict[str, Any]]) -> str:
    """
    Convert List[Dict] to text for Gradio textbox (one-way conversion).

    This is a MODEL → VIEW conversion for Phase 3. The inverse (text → Dict)
    is NOT provided because it loses intelligence data.

    Args:
        bullets: List of bullet dicts with "text" field

    Returns:
        Newline-separated bullet text

    Example:
        >>> bullets = [{"text": "First", "bullet_id": "1"}, {"text": "Second", "bullet_id": "2"}]
        >>> bullets_to_display_text(bullets)
        'First\\nSecond'
    """
    texts = [b.get("text", "") if isinstance(b, dict) else b for b in bullets]
    return "\n".join(text.strip() for text in texts if text.strip())


# ===== PHASE 3A: CANONICAL STATE FUNCTIONS =====

def create_canonical_bullets(
    spins_list: List[Dict[str, Any]],
    programmer_list: List[Dict[str, Any]],
    analyst_list: List[Dict[str, Any]]
) -> List[Dict[str, Any]]:
    """
    Create canonical bullet representation with section tags.

    Consolidates 3 separate lists into single source of truth with "section" field.
    This is the foundation for Phase 3A state unification.

    Args:
        spins_list: SPINS section bullets with intelligence
        programmer_list: Programmer section bullets with intelligence
        analyst_list: Analyst section bullets with intelligence

    Returns:
        Single list with all bullets, each tagged with "section" field

    Example:
        >>> spins = [{"text": "A", "bullet_id": "1"}]
        >>> programmer = [{"text": "B", "bullet_id": "2"}]
        >>> analyst = [{"text": "C", "bullet_id": "3"}]
        >>> canonical = create_canonical_bullets(spins, programmer, analyst)
        >>> len(canonical)
        3
        >>> canonical[0]["section"]
        'spins'
    """
    canonical = []

    # Add section tag to each bullet
    for bullet in spins_list:
        bullet_copy = bullet.copy()
        bullet_copy["section"] = "spins"
        canonical.append(bullet_copy)

    for bullet in programmer_list:
        bullet_copy = bullet.copy()
        bullet_copy["section"] = "programmer"
        canonical.append(bullet_copy)

    for bullet in analyst_list:
        bullet_copy = bullet.copy()
        bullet_copy["section"] = "analyst"
        canonical.append(bullet_copy)

    return canonical


def get_used_bullet_ids(canonical_bullets: List[Dict[str, Any]]) -> set:
    """
    Derive used bullet IDs from canonical state (no separate tracking needed).

    Args:
        canonical_bullets: Canonical bullet list with all sections

    Returns:
        Set of bullet IDs currently in use

    Example:
        >>> bullets = [
        ...     {"bullet_id": "1", "section": "spins"},
        ...     {"bullet_id": "2", "section": "programmer"}
        ... ]
        >>> get_used_bullet_ids(bullets)
        {'1', '2'}
    """
    return {b.get("bullet_id") for b in canonical_bullets if b.get("bullet_id")}


def split_canonical_bullets(
    canonical_bullets: List[Dict[str, Any]]
) -> tuple[List[Dict[str, Any]], List[Dict[str, Any]], List[Dict[str, Any]]]:
    """
    Split canonical state back into section-specific lists (for backward compatibility).

    This allows gradual migration from separate states to canonical state.
    During transition, handlers can work with either representation.

    Args:
        canonical_bullets: Canonical bullet list with "section" field

    Returns:
        Tuple of (spins_list, programmer_list, analyst_list)

    Example:
        >>> canonical = [
        ...     {"text": "A", "section": "spins"},
        ...     {"text": "B", "section": "programmer"}
        ... ]
        >>> spins, prog, analyst = split_canonical_bullets(canonical)
        >>> len(spins), len(prog), len(analyst)
        (1, 1, 0)
    """
    spins = get_section_bullets(canonical_bullets, "spins")
    programmer = get_section_bullets(canonical_bullets, "programmer")
    analyst = get_section_bullets(canonical_bullets, "analyst")

    return spins, programmer, analyst
