import json
import os

from typing import List, Dict, Tuple
from app.types import ResumeData, BulletLibraryItem
from app.config import config
from app.distribution_engine import group_by_section
from app.openai_client import call_openai_json
from app.prompts import bullet_selection_prompt, rewrite_prompt
from app.bullet_intelligence import (
    get_cached_jd_analysis,
    analyze_bullets,
    score_bullets_against_jd
)
from app.bullet_library_manager import validate_bullet_library
from app.exceptions import FileOperationError, ValidationError, DataProcessingError
from app.logging_config import get_logger

logger = get_logger(__name__)


def select_bullets_by_section(
    scored: List[dict],
    bullet_items: List[BulletLibraryItem]
) -> List[BulletLibraryItem]:
    """
    Select top-scoring bullets per section based on exact configured counts.

    Args:
        scored: List of {"bullet": text, "score": N} from LLM scoring
        bullet_items: List of BulletLibraryItems with text and section fields

    Returns:
        List of selected BulletLibraryItems (spins_count + programmer_count + analyst_count)

    Raises:
        ValidationError: If any section has insufficient bullets in the library
    """
    # Build score lookup
    score_map: Dict[str, float] = {item["bullet"]: item["score"] for item in scored}

    # Group library items by section with their scores
    by_section: Dict[str, List[Tuple[float, BulletLibraryItem]]] = {
        "spins": [], "programmer": [], "analyst": []
    }
    for item in bullet_items:
        section = item["section"]
        if section in by_section:
            score = score_map.get(item["text"], 0.0)
            by_section[section].append((score, item))

    counts = {
        "spins": config.business.spins_count,
        "programmer": config.business.programmer_count,
        "analyst": config.business.analyst_count,
    }

    selected: List[BulletLibraryItem] = []
    for section_name, count in counts.items():
        items = by_section[section_name]
        if len(items) < count:
            raise ValidationError(
                f"Section '{section_name}' has {len(items)} bullets in library, "
                f"needs {count}. Add more '{section_name}' bullets to the library."
            )
        # Sort by score descending and take top count
        items.sort(key=lambda x: x[0], reverse=True)
        selected.extend(item for _, item in items[:count])

    logger.info(
        f"Selected {len(selected)} bullets: "
        f"{counts['spins']} spins, {counts['programmer']} programmer, {counts['analyst']} analyst"
    )
    return selected


def generate_resume(job_description, company_name,
                    company_info, bullet_file, job_change) -> ResumeData:
    """
    Generate a tailored resume based on job description and bullet library.

    Args:
        job_description: Target job description
        company_name: Target company name
        company_info: Information about the target company
        bullet_file: Path to bullet library JSON file
        job_change: Boolean indicating if this is a career change

    Returns:
        ResumeData TypedDict containing summary, section bullets (spins,
        programmer, analyst), and intelligence metadata

    Raises:
        FileOperationError: If bullet file is missing or invalid
        ValidationError: If bullet data is malformed or has insufficient bullets
        DataProcessingError: If processing fails
    """
    logger.info(f"Generating resume for {company_name} using bullet file: {bullet_file}")

    if not os.path.exists(bullet_file):
        logger.error(f"Bullet file not found: {bullet_file}")
        raise FileOperationError(f"Bullet file not found: {bullet_file}")

    try:
        with open(bullet_file, "r", encoding="utf-8") as f:
            bullet_data = json.load(f)
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in bullet file {bullet_file}: {e}")
        raise FileOperationError(f"Invalid JSON in bullet file: {e}")
    except IOError as e:
        logger.error(f"Error reading bullet file {bullet_file}: {e}")
        raise FileOperationError(f"Error reading bullet file: {e}")

    # Validate new format
    is_valid, validation_errors = validate_bullet_library(bullet_data)
    if not is_valid:
        logger.error(f"Bullet library validation failed: {validation_errors}")
        raise ValidationError("Bullet library validation failed:\n" + "\n".join(validation_errors))

    bullet_items: List[BulletLibraryItem] = bullet_data["bullets"]
    role = bullet_data.get("role", "General")
    all_bullet_texts = [item["text"] for item in bullet_items]
    logger.info(f"Loaded {len(bullet_items)} bullets for role: {role}")

    # 1. Score all bullets
    logger.debug("Scoring bullets against job description")
    try:
        scored = call_openai_json(
            bullet_selection_prompt(job_description, all_bullet_texts),
            timeout=config.llm.scoring_timeout
        )["scored_bullets"]
        logger.info(f"Scored {len(scored)} bullets")
    except KeyError as e:
        logger.error(f"LLM response missing expected key: {e}")
        raise DataProcessingError(f"Invalid LLM response structure: missing {e}")

    # 2. Section-aware selection
    selected_items = select_bullets_by_section(scored, bullet_items)
    selected_texts = [item["text"] for item in selected_items]

    # 3. Rewrite selected bullets
    logger.debug(f"Rewriting {len(selected_texts)} selected bullets")
    try:
        rewritten = call_openai_json(
            rewrite_prompt(
                job_description,
                company_name,
                company_info,
                selected_texts,
                job_change,
                role
            ),
            temperature=config.llm.temperature_creative,
            timeout=config.llm.rewriting_timeout
        )
        rewritten_bullets = rewritten["rewritten_bullets"]
        logger.info(f"Rewrote {len(rewritten_bullets)} bullets")
    except KeyError as e:
        logger.error(f"LLM response missing expected key: {e}")
        raise DataProcessingError(f"Invalid LLM response structure: missing {e}")

    # 4. Analyze bullets
    logger.debug("Analyzing job description")
    jd_analysis = get_cached_jd_analysis(job_description)

    logger.debug("Analyzing rewritten bullets")
    analyzed_bullets = analyze_bullets(rewritten_bullets)

    logger.debug("Scoring bullets against job description")
    analyzed_bullets = score_bullets_against_jd(analyzed_bullets, jd_analysis)

    # 5. Propagate section designations from library items to analyzed bullets
    for bullet_dict, selected_item in zip(analyzed_bullets, selected_items):
        bullet_dict["section"] = selected_item["section"]

    sections = group_by_section(analyzed_bullets)
    logger.info(
        f"Final sections: spins={len(sections['spins'])}, "
        f"programmer={len(sections['programmer'])}, analyst={len(sections['analyst'])}"
    )

    # Identify which bullets are actually used
    used_texts = set(sections["spins"] + sections["programmer"] + sections["analyst"])
    used_bullet_ids = {
        b["bullet_id"] for b in analyzed_bullets
        if b.get("text") in used_texts
    }

    result = {
        "summary": rewritten["summary"],
        "spins": sections["spins"],
        "programmer": sections["programmer"],
        "analyst": sections["analyst"],
        "metadata": {
            "analyzed_bullets": analyzed_bullets,
            "jd_analysis": jd_analysis,
            "used_bullet_ids": used_bullet_ids
        }
    }

    logger.info(f"Resume generation complete for {company_name}")
    return result
