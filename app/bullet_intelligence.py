"""
Intelligent bullet analysis and scoring system.
Extracts keywords, categories, impact metrics, and computes JD alignment scores.
"""

import re
from typing import List, Dict, Set
from app.types import JDAnalysis, AnalyzedBullet, Suggestion
from app.config import config
from app.openai_client import call_openai_json
from app.logging_config import get_logger

logger = get_logger(__name__)


# ===== JOB DESCRIPTION ANALYSIS =====

def analyze_job_description(job_description: str) -> JDAnalysis:
    """
    Extract intelligence from job description using LLM.

    Returns:
        JDAnalysis TypedDict with required_skills, preferred_skills,
        all_keywords, and job_categories
    """
    logger.debug("Analyzing job description for keywords and skills")
    prompt = _build_jd_analysis_prompt(job_description)
    result = call_openai_json(prompt, temperature=0.0, timeout=60)

    # Normalize to lowercase for matching
    analysis = {
        "required_skills": [s.lower() for s in result.get("required_skills", [])],
        "preferred_skills": [s.lower() for s in result.get("preferred_skills", [])],
        "all_keywords": [k.lower() for k in result.get("all_keywords", [])],
        "job_categories": result.get("job_categories", [])
    }
    logger.info(f"JD analysis: {len(analysis['required_skills'])} required skills, "
                f"{len(analysis['preferred_skills'])} preferred skills, "
                f"{len(analysis['job_categories'])} categories")
    return analysis


def _build_jd_analysis_prompt(job_description: str) -> List[Dict[str, str]]:
    """Build LLM prompt for JD keyword extraction."""
    return [{
        "role": "user",
        "content": f"""Analyze this job description and extract structured information.

Job Description:
{job_description}

Return JSON with:
- required_skills: List of explicitly required/must-have technical skills, tools, and technologies
- preferred_skills: List of preferred/nice-to-have technical skills
- all_keywords: Complete list of ALL relevant keywords (skills, tools, verbs, domains)
- job_categories: Relevant categories from: frontend, backend, fullstack, data, devops, cloud, mobile, qa, collaboration, leadership, user-support, documentation

Focus on technical skills, tools, frameworks, and action verbs.
Return format:
{{
  "required_skills": ["skill1", "skill2"],
  "preferred_skills": ["skill3"],
  "all_keywords": ["skill1", "skill2", "skill3", "verb1"],
  "job_categories": ["frontend", "backend"]
}}"""
    }]


# ===== BULLET ANALYSIS =====

def analyze_bullets(bullets: List[str]) -> List[AnalyzedBullet]:
    """
    Extract intelligence from all rewritten bullets using LLM batch call.

    Args:
        bullets: List of rewritten bullet texts

    Returns:
        List of AnalyzedBullet TypedDicts with bullet_id, text, keywords,
        category, and has_impact fields
    """
    logger.debug(f"Analyzing {len(bullets)} bullets for keywords and categories")
    prompt = _build_bullet_analysis_prompt(bullets)
    result = call_openai_json(prompt, temperature=0.0, timeout=90)

    # Add bullet IDs and normalize keywords
    import uuid
    analyzed = []
    for i, bullet_data in enumerate(result.get("bullets", [])):
        analyzed.append({
            "bullet_id": str(uuid.uuid4()),
            "text": bullets[i],
            "keywords": [k.lower() for k in bullet_data.get("keywords", [])],
            "category": bullet_data.get("category", "general"),
            "has_impact": bullet_data.get("has_impact", False)
        })

    logger.info(f"Analyzed {len(analyzed)} bullets with intelligence metadata")
    return analyzed


def _build_bullet_analysis_prompt(bullets: List[str]) -> List[Dict[str, str]]:
    """Build LLM prompt for batch bullet analysis."""
    bullets_text = "\n\n".join([f"{i+1}. {bullet}" for i, bullet in enumerate(bullets)])

    return [{
        "role": "user",
        "content": f"""Analyze these resume bullets and extract structured information for each.

Bullets:
{bullets_text}

For EACH bullet, extract:
- keywords: List of technical skills, tools, technologies, and key action verbs
- category: Single best-fit category from: frontend, backend, fullstack, data, devops, cloud, mobile, qa, collaboration, leadership, user-support, documentation, general
- has_impact: Boolean - true if bullet contains quantified metrics (%, numbers, time saved, users served)

Return JSON with format:
{{
  "bullets": [
    {{
      "keywords": ["keyword1", "keyword2"],
      "category": "frontend",
      "has_impact": true
    }},
    ...
  ]
}}

Note: Return exactly {len(bullets)} bullet analyses in the same order."""
    }]


# ===== SCORING =====

def score_bullets_against_jd(
    analyzed_bullets: List[AnalyzedBullet],
    jd_analysis: JDAnalysis
) -> List[AnalyzedBullet]:
    """
    Score each bullet based on JD alignment.

    Scoring formula:
    - +3 points per required skill match
    - +1 point per preferred skill match
    - +2 points if has quantified impact

    Args:
        analyzed_bullets: Output from analyze_bullets()
        jd_analysis: Output from analyze_job_description()

    Returns:
        Same AnalyzedBullet dicts with added jd_score, required_matches,
        and preferred_matches fields
    """
    required = set(jd_analysis["required_skills"])
    preferred = set(jd_analysis["preferred_skills"])

    for bullet in analyzed_bullets:
        score = 0
        bullet_keywords = set(bullet["keywords"])

        # Match required skills
        required_matches = bullet_keywords & required
        score += len(required_matches) * config.scoring.required_skill_weight

        # Match preferred skills
        preferred_matches = bullet_keywords & preferred
        score += len(preferred_matches) * config.scoring.preferred_skill_weight

        # Impact bonus
        if bullet["has_impact"]:
            score += config.scoring.impact_bonus

        bullet["jd_score"] = score
        bullet["required_matches"] = list(required_matches)
        bullet["preferred_matches"] = list(preferred_matches)

    return analyzed_bullets


# ===== REPLACEMENT SUGGESTIONS =====

def suggest_replacements(
    removed_bullet: AnalyzedBullet,
    all_bullets: List[AnalyzedBullet],
    active_bullet_ids: Set[str],
    active_bullets: List[AnalyzedBullet],
    jd_analysis: JDAnalysis
) -> List[Suggestion]:
    """
    Suggest top 5 replacement bullets based on:
    - Category similarity
    - Skill overlap with removed bullet
    - JD alignment score
    - Skills coverage penalty (avoid overloading same skills)

    Args:
        removed_bullet: The bullet being replaced (AnalyzedBullet)
        all_bullets: Full pool of analyzed bullets
        active_bullet_ids: Set of bullet IDs currently in use
        active_bullets: List of bullets currently active in target section
        jd_analysis: Job description analysis

    Returns:
        Top 5 Suggestion TypedDicts with bullet, score, and explanation
    """
    logger.debug(f"Suggesting replacements for bullet in category '{removed_bullet.get('category')}', "
                 f"{len(all_bullets)} candidates available, {len(active_bullet_ids)} already in use")
    candidates = []

    for bullet in all_bullets:
        # Skip bullets already in use
        if bullet["bullet_id"] in active_bullet_ids:
            continue

        # Calculate category similarity
        category_similarity = (
            config.scoring.category_similarity_weight
            if bullet["category"] == removed_bullet["category"]
            else 0
        )

        # Calculate skill overlap
        bullet_keywords = set(bullet["keywords"])
        removed_keywords = set(removed_bullet["keywords"])
        skill_overlap = len(bullet_keywords & removed_keywords) * config.scoring.skill_overlap_weight

        # Calculate skills coverage penalty
        coverage_penalty = calculate_skill_coverage_penalty(bullet, active_bullets)

        # Final score
        final_score = (
            bullet["jd_score"]
            + category_similarity
            + skill_overlap
            - coverage_penalty
        )

        # Generate explanation
        explanation = generate_explanation(bullet, removed_bullet, jd_analysis)

        candidates.append({
            "bullet": bullet,
            "score": final_score,
            "explanation": explanation
        })

    # Sort by score (descending) and return top 5
    candidates.sort(key=lambda x: x["score"], reverse=True)
    top_5 = candidates[:5]
    logger.info(f"Generated {len(top_5)} replacement suggestions")
    return top_5


def calculate_skill_coverage_penalty(
    bullet: AnalyzedBullet,
    active_bullets: List[AnalyzedBullet]
) -> float:
    """
    Calculate penalty for skill redundancy.

    Penalize bullets that duplicate skills already heavily represented
    in the active section.

    Args:
        bullet: Candidate bullet
        active_bullets: Bullets currently in the target section

    Returns:
        Penalty score (higher = more redundant)
    """
    # Collect all keywords from active bullets
    active_keywords = set()
    for active in active_bullets:
        active_keywords.update(active.get("keywords", []))

    # Count how many of candidate's keywords are already used
    bullet_keywords = set(bullet["keywords"])
    duplicated_skills = bullet_keywords & active_keywords

    penalty = len(duplicated_skills) * config.scoring.skill_coverage_penalty
    return penalty


def generate_explanation(
    bullet: AnalyzedBullet,
    removed_bullet: AnalyzedBullet,
    jd_analysis: JDAnalysis
) -> str:
    """
    Generate human-readable explanation for why this replacement is suggested.

    Args:
        bullet: Candidate replacement bullet
        removed_bullet: The bullet being replaced
        jd_analysis: Job description analysis

    Returns:
        Explanation string
    """
    # Priority 1: Required skill matches
    if bullet.get("required_matches"):
        matched = ", ".join(bullet["required_matches"][:3])  # First 3
        return f"✓ Strong alignment with required skills: {matched}"

    # Priority 2: Same category
    if bullet["category"] == removed_bullet.get("category"):
        return f"✓ Same category ({bullet['category']}) as removed bullet"

    # Priority 3: Quantified impact
    if bullet["has_impact"]:
        return "✓ Demonstrates measurable impact, strengthening results-driven narrative"

    # Priority 4: Preferred skill matches
    if bullet.get("preferred_matches"):
        matched = ", ".join(bullet["preferred_matches"][:3])
        return f"✓ Aligns with preferred skills: {matched}"

    # Default
    return "✓ Supports overall technical alignment with job description"


# ===== GLOBAL ANALYSIS CACHE =====
# Store JD analysis to avoid redundant LLM calls
_jd_analysis_cache = {}

def get_cached_jd_analysis(job_description: str) -> JDAnalysis:
    """Get or create cached JD analysis."""
    jd_hash = hash(job_description)
    if jd_hash not in _jd_analysis_cache:
        logger.debug("JD analysis cache miss, analyzing job description")
        _jd_analysis_cache[jd_hash] = analyze_job_description(job_description)
    else:
        logger.debug("JD analysis cache hit")
    return _jd_analysis_cache[jd_hash]
