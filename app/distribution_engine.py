"""
Distribution Engine: Deterministic Section Size Enforcement

This module implements the deterministic layer of the resume generation pipeline.
Per the architecture philosophy: "LLMs classify, code enforces hard constraints."

LLM Responsibility (probabilistic):
- Classify bullets into presentation sections based on semantic fit

Code Responsibility (deterministic):
- Enforce section size limits (min/max bullets per section)
- Manage overflow to the catch-all section
- Ensure consistent, repeatable distributions

Configuration:
- Section metadata is defined in SECTION_CONFIG
- Primary sections (spins, programmer): 10-12 bullets each
- Overflow section (analyst): no limits, receives overflow
"""

from typing import List, Dict
from app.types import BulletAssignment
from app.config import config
from app.openai_client import call_openai_json
from app.prompts import distribution_prompt
from app.exceptions import ValidationError, DataProcessingError
from app.logging_config import get_logger

logger = get_logger(__name__)


def _build_section_config() -> Dict:
    """
    Build section configuration from app config.

    This allows section limits to be configured via environment variables
    while maintaining the same structure expected by the rest of the module.
    """
    return {
        "spins": {
            "min_bullets": config.business.spins_min,
            "max_bullets": config.business.spins_max,
            "priority": "primary",
            "description": "End-user support, customer interaction, service delivery"
        },
        "programmer": {
            "min_bullets": config.business.programmer_min,
            "max_bullets": config.business.programmer_max,
            "priority": "primary",
            "description": "Technical implementation, automation, scripting"
        },
        "analyst": {
            "min_bullets": config.business.analyst_min,
            "max_bullets": config.business.analyst_max,
            "priority": "overflow",
            "description": "Troubleshooting, root cause analysis, documentation"
        }
    }


# Configuration: Single Source of Truth (built from config)
SECTION_CONFIG = _build_section_config()

# Derived constants (computed from config)
PRIMARY_SECTIONS = [name for name, config in SECTION_CONFIG.items()
                    if config["priority"] == "primary"]
OVERFLOW_SECTION = next(name for name, config in SECTION_CONFIG.items()
                        if config["priority"] == "overflow")
VALID_SECTIONS = set(SECTION_CONFIG.keys())


def validate_assignments(assignments: List[BulletAssignment]) -> None:
    """
    Validate assignment structure and content.

    Args:
        assignments: List of assignment dicts from LLM

    Raises:
        ValidationError: If structure is invalid or contains invalid data
    """
    if not isinstance(assignments, list):
        raise ValidationError(f"Expected list, got {type(assignments).__name__}")

    if not assignments:
        raise ValidationError("Assignments list is empty")

    for i, assignment in enumerate(assignments):
        # Check required keys
        if not isinstance(assignment, dict):
            raise ValidationError(f"Assignment {i} is not a dict: {assignment}")

        if "bullet" not in assignment:
            raise ValidationError(f"Assignment {i} missing 'bullet' key: {assignment}")

        if "section" not in assignment:
            raise ValidationError(f"Assignment {i} missing 'section' key: {assignment}")

        # Check data types
        bullet = assignment["bullet"]
        if not isinstance(bullet, str):
            raise ValidationError(f"Assignment {i} bullet is not string: {type(bullet).__name__}")

        if not bullet.strip():
            raise ValidationError(f"Assignment {i} has empty bullet")

        # Check section validity
        section = assignment["section"]
        if section not in VALID_SECTIONS:
            raise ValidationError(
                f"Assignment {i} has invalid section '{section}'. "
                f"Valid sections: {', '.join(sorted(VALID_SECTIONS))}"
            )


def validate_section_distribution(sections: Dict[str, List[str]]) -> None:
    """
    Validate that section distribution meets configured constraints.

    Args:
        sections: Dict mapping section names to bullet lists

    Raises:
        ValidationError: If constraints are violated

    Note: This is used for post-rebalance verification in tests/debugging
    """
    for section_name, bullets in sections.items():
        config = SECTION_CONFIG[section_name]
        count = len(bullets)

        min_bullets = config["min_bullets"]
        max_bullets = config["max_bullets"]

        if min_bullets and count < min_bullets:
            raise ValidationError(
                f"Section '{section_name}' has {count} bullets, "
                f"requires minimum {min_bullets}"
            )

        if max_bullets and count > max_bullets:
            raise ValidationError(
                f"Section '{section_name}' has {count} bullets, "
                f"requires maximum {max_bullets}"
            )


def classify_bullets(bullets: List[str]) -> List[BulletAssignment]:
    """
    Classify resume bullets into presentation sections using LLM.

    This function handles the probabilistic semantic classification. The LLM
    determines which presentation lens (spins/programmer/analyst) best showcases
    each bullet. Deterministic enforcement of size limits happens in rebalance().

    Args:
        bullets: List of resume bullet strings to classify

    Returns:
        List of BulletAssignment TypedDicts with bullet text and section

    Raises:
        DataProcessingError: If LLM response is invalid or malformed

    Example:
        >>> bullets = ["Fixed customer issues", "Wrote Python scripts"]
        >>> classify_bullets(bullets)
        [
            {"bullet": "Fixed customer issues", "section": "spins"},
            {"bullet": "Wrote Python scripts", "section": "programmer"}
        ]
    """
    logger.debug(f"Classifying {len(bullets)} bullets into sections")
    response = call_openai_json(
        distribution_prompt(bullets),
        temperature=0.0,  # Deterministic classification
        timeout=60
    )

    # Validate response structure
    if not isinstance(response, dict):
        logger.error(f"Expected dict from LLM, got {type(response).__name__}")
        raise DataProcessingError(f"Expected dict from LLM, got {type(response).__name__}")

    if "assignments" not in response:
        logger.error(f"LLM response missing 'assignments' key. Got keys: {list(response.keys())}")
        raise DataProcessingError(
            f"LLM response missing 'assignments' key. Got keys: {list(response.keys())}"
        )

    assignments = response["assignments"]

    # Validate assignments
    validate_assignments(assignments)

    logger.info(f"Successfully classified {len(assignments)} bullets")
    return assignments


def rebalance(assignments: List[BulletAssignment]) -> Dict[str, List[str]]:
    """
    Enforce deterministic section size limits on classified bullets.

    This is the deterministic enforcement layer. After the LLM classifies bullets
    semantically, this function enforces hard constraints on section sizes.

    Algorithm:
    1. Distribute bullets to initial sections based on LLM assignments
    2. Enforce max limits on primary sections, collect overflow
    3. Enforce min limits on primary sections, pulling from overflow section
    4. Add overflow to overflow section (the flexible catch-all)

    Args:
        assignments: List of dicts with keys "bullet" (str) and "section" (str)

    Returns:
        Dict mapping section names to lists of bullet strings:
        {
            "spins": [bullet1, bullet2, ...],      # 10-12 bullets
            "programmer": [bullet1, bullet2, ...], # 10-12 bullets
            "analyst": [bullet1, bullet2, ...]     # remainder (no limits)
        }

    Raises:
        ValidationError: If assignments structure is invalid

    Example:
        >>> assignments = [
        ...     {"bullet": "Helped customers", "section": "spins"},
        ...     {"bullet": "Wrote Python", "section": "programmer"}
        ... ]
        >>> rebalance(assignments)
        {'spins': ['Helped customers'], 'programmer': ['Wrote Python'], 'analyst': []}

    Note:
        This implements the deterministic layer mandated by the architecture.
        LLMs classify (semantic work), code enforces constraints (structural work).
    """
    # Validate input
    validate_assignments(assignments)

    logger.debug(f"Rebalancing {len(assignments)} bullets across sections")

    # 1. Initialize sections from configuration
    sections: Dict[str, List[str]] = {name: [] for name in SECTION_CONFIG.keys()}

    # 2. Distribute bullets based on LLM assignments
    for assignment in assignments:
        section = assignment["section"]
        bullet = assignment["bullet"]
        sections[section].append(bullet)

    # 3. Enforce maximum limits on primary sections
    overflow: List[str] = []

    for section_name in PRIMARY_SECTIONS:
        max_bullets = SECTION_CONFIG[section_name]["max_bullets"]

        if len(sections[section_name]) > max_bullets:
            # Extract overflow bullets
            overflow_bullets = sections[section_name][max_bullets:]
            sections[section_name] = sections[section_name][:max_bullets]
            overflow.extend(overflow_bullets)

    # 4. Enforce minimum limits on primary sections
    for section_name in PRIMARY_SECTIONS:
        min_bullets = SECTION_CONFIG[section_name]["min_bullets"]
        needed = min_bullets - len(sections[section_name])

        if needed > 0:
            # Pull from overflow section
            overflow_source = sections[OVERFLOW_SECTION]
            available = len(overflow_source)
            take = min(needed, available)

            if take > 0:
                # Take from end of overflow section
                sections[section_name].extend(overflow_source[-take:])
                sections[OVERFLOW_SECTION] = overflow_source[:-take]

    # 5. Add collected overflow to overflow section
    sections[OVERFLOW_SECTION].extend(overflow)

    logger.info(f"Rebalanced sections: spins={len(sections['spins'])}, "
                f"programmer={len(sections['programmer'])}, analyst={len(sections['analyst'])}")
    return sections


def get_section_limits(section_name: str) -> tuple:
    """
    Get min and max bullet limits for a section.

    Args:
        section_name: Name of the section

    Returns:
        Tuple of (min_bullets, max_bullets)
        max_bullets is None for unlimited sections

    Raises:
        KeyError: If section_name is not in configuration
    """
    config = SECTION_CONFIG[section_name]
    return config["min_bullets"], config["max_bullets"]
