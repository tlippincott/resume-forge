import json
import os
import random

from app.distribution_engine import classify_bullets, rebalance
from app.openai_client import call_openai_json
from app.prompts import bullet_selection_prompt, rewrite_prompt
from app.bullet_intelligence import (
    get_cached_jd_analysis,
    analyze_bullets,
    score_bullets_against_jd
)
from app.exceptions import FileOperationError, ValidationError, DataProcessingError
from app.logging_config import get_logger

logger = get_logger(__name__)


def generate_resume(job_description, company_name,
                    company_info, bullet_file, job_change,):
    """
    Generate a tailored resume based on job description and bullet library.

    Args:
        job_description: Target job description
        company_name: Target company name
        company_info: Information about the target company
        bullet_file: Path to bullet library JSON file
        job_change: Boolean indicating if this is a career change

    Returns:
        Dict containing summary, section bullets, and intelligence metadata

    Raises:
        FileOperationError: If bullet file is missing or invalid
        ValidationError: If bullet data is malformed
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

    if "bullets" not in bullet_data:
        logger.error(f"Bullet file missing 'bullets' key: {bullet_file}")
        raise ValidationError("Bullet file must contain 'bullets' key")

    all_bullets = bullet_data["bullets"]
    if not all_bullets:
        logger.error(f"Bullet file contains empty bullets list: {bullet_file}")
        raise ValidationError("Bullet file must contain at least one bullet")

    role = bullet_data.get("role", "General")  # Default to "General" if role not present
    logger.info(f"Loaded {len(all_bullets)} bullets for role: {role}")

    # 1. Score all bullets
    logger.debug("Scoring bullets against job description")
    try:
        scored = call_openai_json(
            bullet_selection_prompt(job_description, all_bullets),
            timeout=90
        )["scored_bullets"]
        logger.info(f"Scored {len(scored)} bullets")
    except KeyError as e:
        logger.error(f"LLM response missing expected key: {e}")
        raise DataProcessingError(f"Invalid LLM response structure: missing {e}")

    # 2. Sort by score (deterministic)
    sorted_bullets = sorted(scored, key=lambda x: x["score"], reverse=True)

    # 3. Select top 38-42 (increased from 28-32 for larger replacement pool)
    count = random.randint(38, 42)
    selected = [item["bullet"] for item in sorted_bullets[:count]]

    # 4. Rewrite selected bullets for clarity and alignment
    logger.debug(f"Rewriting {len(selected)} selected bullets")
    try:
        rewritten = call_openai_json(
            rewrite_prompt(
                job_description,
                company_name,
                company_info,
                selected,
                job_change,
                role  # Pass role for strategy selection
            ),
            temperature=0.7,
            timeout=120
        )
        rewritten_bullets = rewritten["rewritten_bullets"]
        logger.info(f"Rewrote {len(rewritten_bullets)} bullets")
    except KeyError as e:
        logger.error(f"LLM response missing expected key: {e}")
        raise DataProcessingError(f"Invalid LLM response structure: missing {e}")

    # === NEW: INTELLIGENT ANALYSIS ===

    # Step 1: Analyze job description (1 LLM call)
    logger.debug("Analyzing job description")
    jd_analysis = get_cached_jd_analysis(job_description)

    # Step 2: Analyze all rewritten bullets (1 LLM call for batch)
    logger.debug("Analyzing rewritten bullets")
    analyzed_bullets = analyze_bullets(rewritten_bullets)

    # Step 3: Score bullets against JD (rule-based, no LLM)
    logger.debug("Scoring bullets against job description")
    analyzed_bullets = score_bullets_against_jd(analyzed_bullets, jd_analysis)

    # 5. Classify bullets into sections
    logger.debug("Classifying bullets into sections")
    assignments = classify_bullets(rewritten_bullets)

    # Add classification to analyzed bullets
    assignment_map = {a["bullet"]: a["section"] for a in assignments}
    for bullet_data in analyzed_bullets:
        bullet_data["section"] = assignment_map.get(bullet_data["text"], "analyst")

    # 6. Rebalance sections (enforce 10-12 per primary section)
    logger.debug("Rebalancing sections")
    sections = rebalance(assignments)
    logger.info(f"Final sections: spins={len(sections['spins'])}, programmer={len(sections['programmer'])}, analyst={len(sections['analyst'])}")

    # === NEW: ENHANCED RETURN WITH INTELLIGENCE ===

    # Identify which bullets are actually used in final sections
    used_texts = set(sections["spins"] + sections["programmer"] + sections["analyst"])
    used_bullet_ids = {
        b["bullet_id"] for b in analyzed_bullets
        if b["text"] in used_texts
    }

    result = {
        "summary": rewritten["summary"],
        "spins": sections["spins"],
        "programmer": sections["programmer"],
        "analyst": sections["analyst"],
        "metadata": {
            "analyzed_bullets": analyzed_bullets,  # Full intelligence per bullet
            "jd_analysis": jd_analysis,            # JD keywords and skills
            "used_bullet_ids": used_bullet_ids     # Track which bullets are active
        }
    }

    logger.info(f"Resume generation complete for {company_name}")
    return result
