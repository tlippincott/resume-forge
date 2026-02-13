"""
UI formatting helpers for Gradio event handlers.

This module extracts formatting logic from oversized event handlers,
improving maintainability and testability. All functions are pure
(no side effects) and focus on formatting data for UI display.
"""

from typing import Dict, List, Tuple, Any
import gradio as gr


def format_removed_bullet_display(bullet: Dict, bullet_index: int) -> str:
    """
    Format removed bullet for markdown display in suggestion panel.

    Args:
        bullet: Bullet dict with 'text', 'category', 'jd_score' keys
        bullet_index: 1-based bullet index for display

    Returns:
        Formatted markdown string showing bullet details

    Example:
        >>> bullet = {"text": "Led team...", "category": "Leadership", "jd_score": 8.5}
        >>> format_removed_bullet_display(bullet, 3)
        '#### Replacing Bullet #3:\n**Original:** Led team...\n\n**Category:** Leadership | **JD Score:** 8.5\n'
    """
    removed_text = bullet.get("text", str(bullet))
    truncated_text = removed_text[:150] + "..." if len(removed_text) > 150 else removed_text
    category = bullet.get("category", "unknown")
    jd_score = bullet.get("jd_score", 0)

    return f"""#### Replacing Bullet #{bullet_index}:
**Original:** {truncated_text}

**Category:** {category} | **JD Score:** {jd_score}
"""


def format_suggestion_choices(suggestions: List[Dict]) -> List[Tuple[str, str]]:
    """
    Convert suggestion list to Radio component choices.

    Each choice is a tuple of (display_label, bullet_id).
    Display label includes score, category, and truncated text.

    Args:
        suggestions: List of suggestion dicts with 'bullet', 'score', 'explanation' keys

    Returns:
        List of (label, value) tuples for gr.Radio choices parameter

    Example:
        >>> suggestions = [{
        ...     "bullet": {"text": "Developed feature...", "category": "Technical", "bullet_id": "b123"},
        ...     "score": 9.2,
        ...     "explanation": "..."
        ... }]
        >>> format_suggestion_choices(suggestions)
        [('⭐ 9.2 | [Technical] Developed feature...', 'b123')]
    """
    choices = []
    for sugg in suggestions:
        bullet = sugg["bullet"]
        score = sugg["score"]
        text = bullet["text"]
        display_text = text[:100] + "..." if len(text) > 100 else text
        choice_label = f"⭐ {score:.1f} | [{bullet['category']}] {display_text}"
        choices.append((choice_label, bullet["bullet_id"]))

    return choices


def format_suggestion_explanation(suggestion: Dict) -> str:
    """
    Format bullet explanation as markdown for first suggestion.

    Shows why the suggestion was chosen, including category, keywords,
    impact flag, and JD score.

    Args:
        suggestion: Suggestion dict with 'bullet', 'explanation', 'score' keys

    Returns:
        Formatted markdown string with explanation details

    Example:
        >>> suggestion = {
        ...     "explanation": "Matches technical requirements",
        ...     "bullet": {
        ...         "category": "Technical",
        ...         "keywords": ["Python", "API", "REST"],
        ...         "has_impact": True,
        ...         "jd_score": 8.7
        ...     }
        ... }
        >>> format_suggestion_explanation(suggestion)
        '#### Why This Suggestion?\nMatches technical requirements...'
    """
    bullet = suggestion["bullet"]
    keywords = bullet.get("keywords", [])
    keywords_str = ", ".join(keywords[:5]) if keywords else "None"
    has_impact = "✓ Yes" if bullet.get("has_impact", False) else "✗ No"

    return f"""#### Why This Suggestion?
{suggestion['explanation']}

**Details:**
- **Category:** {bullet.get('category', 'unknown')}
- **Keywords:** {keywords_str}
- **Has Impact:** {has_impact}
- **JD Score:** {bullet.get('jd_score', 0)}
"""


def format_skills_coverage_warning(overlap_count: int, overlap_skills: List[str]) -> str:
    """
    Format skills coverage warning message.

    Warns user when multiple bullets cover the same skills,
    potentially reducing skill diversity in resume.

    Args:
        overlap_count: Number of overlapping skills
        overlap_skills: List of skill names that overlap

    Returns:
        Formatted markdown warning string

    Example:
        >>> format_skills_coverage_warning(3, ["Python", "Docker", "AWS"])
        '⚠️ **Skills Coverage Warning**\n3 overlapping skills: Python, Docker, AWS\n'
    """
    skills_str = ", ".join(overlap_skills[:10])  # Limit to 10 for display
    if len(overlap_skills) > 10:
        skills_str += f" (+{len(overlap_skills) - 10} more)"

    return f"""⚠️ **Skills Coverage Warning**
{overlap_count} overlapping skills: {skills_str}
"""


def format_replacement_success(section: str, index: int, bullet: Dict) -> str:
    """
    Format replacement success message with bullet preview.

    Args:
        section: Target section name (e.g., "SPINS", "Programmer")
        index: 0-based bullet index
        bullet: Replacement bullet dict with 'text' key

    Returns:
        Formatted markdown success message

    Example:
        >>> bullet = {"text": "Led cross-functional team of 8 engineers..."}
        >>> format_replacement_success("SPINS", 2, bullet)
        '✓ **Replacement Complete!**\nBullet #3 in SPINS updated.\n\n**New bullet:** Led cross-functional team...'
    """
    bullet_text = bullet.get("text", "")
    truncated = bullet_text[:100] + "..." if len(bullet_text) > 100 else bullet_text

    return f"""✓ **Replacement Complete!**
Bullet #{index + 1} in {section} updated.

**New bullet:** {truncated}
"""


def create_error_response(error_msg: str, num_outputs: int, include_markdown: bool = True) -> tuple:
    """
    Create standardized error response tuple for Gradio handlers.

    Gradio event handlers must return a tuple matching their outputs.
    This helper creates error responses with hidden UI components.

    Args:
        error_msg: Error message to display (will be prefixed with ❌)
        num_outputs: Number of outputs expected by handler
        include_markdown: If True, first output is error Markdown, rest are gr.update()

    Returns:
        Tuple of length num_outputs with error message and hidden UI updates

    Example:
        >>> create_error_response("Invalid bullet index", 10)
        (Markdown(value="❌ Invalid bullet index", visible=True), gr.update(), ...)
    """
    formatted_error = f"❌ {error_msg}" if not error_msg.startswith("❌") else error_msg

    if include_markdown:
        # First output is error markdown, rest are no-op updates
        return tuple([gr.Markdown(value=formatted_error, visible=True)] +
                    [gr.update()] * (num_outputs - 1))
    else:
        # Return list of gr.update() with error as last item
        return tuple([gr.update()] * (num_outputs - 1) + [formatted_error])


def sync_bullet_choices(bullets_text: str) -> List[Tuple[str, int]]:
    """
    Parse bullets text and create Radio component choices for selection.

    Used to sync Radio components when user edits bullet textboxes.
    Each choice shows 1-based index and truncated bullet text.

    Args:
        bullets_text: Newline-separated bullet text from textbox

    Returns:
        List of (display_label, index) tuples for gr.Radio choices
        Empty list if no bullets found

    Example:
        >>> bullets_text = "Led team of 8\\nDeveloped API\\nReduced latency by 40%"
        >>> sync_bullet_choices(bullets_text)
        [('#1: Led team of 8', 1), ('#2: Developed API', 2), ('#3: Reduced latency by 40%', 3)]
    """
    from app.text_processors import text_to_bullets

    bullets = text_to_bullets(bullets_text)
    if not bullets:
        return []

    choices = []
    for idx, bullet_text in enumerate(bullets, start=1):
        # Truncate to 80 chars for readability
        display_text = bullet_text[:80] + "..." if len(bullet_text) > 80 else bullet_text
        choice_label = f"#{idx}: {display_text}"
        choices.append((choice_label, idx))

    return choices


def create_hidden_ui_state() -> Dict[str, Any]:
    """
    Create standardized 'hide all panels' UI update dict.

    Used to hide suggestion/replacement panels when cancelling
    or completing operations.

    Returns:
        Dict mapping component names to gr.update() hide configs

    Example:
        >>> create_hidden_ui_state()
        {
            'removed_display': gr.Markdown(value="", visible=False),
            'suggestion_radio': gr.Radio(choices=[], visible=False),
            ...
        }
    """
    return {
        "removed_display": gr.Markdown(value="", visible=False),
        "suggestion_radio": gr.Radio(choices=[], visible=False),
        "explanation_display": gr.Markdown(value="", visible=False),
        "warning_display": gr.Markdown(value="", visible=False),
        "confirm_button": gr.Button(visible=False),
        "cancel_button": gr.Button(visible=False),
    }


def enrich_section_lists_with_ids(
    spins_list: List[str],
    programmer_list: List[str],
    analyst_list: List[str],
    analyzed_bullets: List[Dict]
) -> Tuple[List[Dict], List[Dict], List[Dict]]:
    """
    Enhance section bullet lists with IDs for tracking.

    Builds a lookup map from bullet text to full bullet data,
    then enriches each section's text-only bullets with their
    metadata (ID, category, keywords, etc.).

    Args:
        spins_list: List of SPINS bullet text strings
        programmer_list: List of Programmer bullet text strings
        analyst_list: List of Analyst bullet text strings
        analyzed_bullets: List of analyzed bullet dicts with full metadata

    Returns:
        Tuple of (spins_with_ids, programmer_with_ids, analyst_with_ids)
        Each is a list of dicts with 'text' and 'bullet_id' keys

    Example:
        >>> spins = ["Led team of 8"]
        >>> analyzed = [{"text": "Led team of 8", "bullet_id": "b123", "category": "Leadership"}]
        >>> enrich_section_lists_with_ids(spins, [], [], analyzed)
        ([{"text": "Led team of 8", "bullet_id": "b123", ...}], [], [])
    """
    # Build bullet lookup map (text → full bullet data)
    bullet_map = {b["text"]: b for b in analyzed_bullets}

    def add_bullet_ids(text_list: List[str]) -> List[Dict]:
        """Add IDs to text-only bullet list."""
        return [bullet_map.get(text, {"text": text, "bullet_id": ""}) for text in text_list]

    return (
        add_bullet_ids(spins_list),
        add_bullet_ids(programmer_list),
        add_bullet_ids(analyst_list)
    )


def create_bullet_library_response(
    success: bool,
    role: str = "",
    bullets_text: str = "",
    status: str = "",
    file_path: str = "",
    bullet_count: int = 0,
    validation: str = "Ready"
) -> tuple:
    """
    Create standardized response tuple for bullet library loading.

    Handles both success and error cases for handle_load_bullet_library().

    Args:
        success: True if library loaded successfully, False for error
        role: Role name (e.g., "Software Engineer")
        bullets_text: Newline-separated bullet text
        status: Status message to display
        file_path: Path to loaded file (empty for errors)
        bullet_count: Number of bullets loaded
        validation: Validation summary string

    Returns:
        9-element tuple matching handle_load_bullet_library() outputs

    Example:
        >>> create_bullet_library_response(False, status="File not found")
        (gr.update(), gr.update(), gr.update(visible=False), "File not found", "", "", "", "0 bullets", "Ready")

        >>> create_bullet_library_response(True, role="Engineer", bullets_text="...", status="Loaded", file_path="...", bullet_count=25, validation="Valid")
        (gr.update(value="Engineer"), gr.update(value="..."), gr.update(visible=True), "Loaded", "...", "Engineer", "...", "25 bullets", "Valid")
    """
    if not success:
        return (
            gr.update(),  # role_editor
            gr.update(),  # bullets_editor
            gr.update(visible=False),  # editor_group
            status,  # editor_status
            "",  # current_bullet_file_path
            "",  # original_role
            "",  # original_bullets_text
            "0 bullets",  # bullet_count_display
            "Ready"  # validation_display
        )

    return (
        gr.update(value=role),  # role_editor
        gr.update(value=bullets_text),  # bullets_editor
        gr.update(visible=True),  # editor_group
        status,  # editor_status
        file_path,  # current_bullet_file_path
        role,  # original_role
        bullets_text,  # original_bullets_text
        f"{bullet_count} bullets",  # bullet_count_display
        validation  # validation_display
    )
