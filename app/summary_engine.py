"""
Summary Engine: 2-call post-rewrite summary generation pipeline.

Pipeline:
  Call 1: Extract 5–7 core competencies from JD + score rewritten bullets against them
  Call 2: Generate 3–4 sentence summary using fixed opening sentence, competencies, matched bullets
"""

from typing import List
from app.config import config
from app.openai_client import call_openai_json
from app.prompts import competency_and_scoring_prompt, summary_generation_prompt
from app.logging_config import get_logger

logger = get_logger(__name__)

# Fixed opening sentences keyed by role string (from bullet_data.get("role", "General")).
# Keys must match the actual "role" field values stored in each bullet library JSON.
_SUMMARY_OPENING_SENTENCES = {
    "Programmer": "Software Engineer with 20+ years designing and maintaining production systems in small startup and state government environments.",
    "Help Desk": "Technical Support Specialist with 20+ years troubleshooting software and infrastructure issues in both startup and government settings.",
    "Sales Engineer": "Technical Solutions Consultant with 20+ years bridging technical systems and executive stakeholders in startup and state government environments.",
    "Analyst": "Systems Analyst with 20+ years translating business and executive requirements into technical solutions across startup and state government environments.",
    "Project Manager": "Technical Project Manager with 20+ years delivering software and operational initiatives in resource-constrained startup and government environments.",
}
_DEFAULT_OPENING = "Technology professional with 20+ years of experience across startup and state government environments."

# Role-specific emphasis injected into the summary generation prompt
_SUMMARY_ROLE_EMPHASIS = {
    "Help Desk": """
ROLE-SPECIFIC EMPHASIS (Help Desk / Technical Support):
- Emphasize customer service excellence and technical troubleshooting breadth
- Highlight first-call resolution capabilities
- Stress communication with non-technical users
""",
    "Programmer": """
ROLE-SPECIFIC EMPHASIS (Programmer / Software Developer):
- Emphasize full development lifecycle proficiency
- Highlight architecture, design patterns, and code quality
- Stress ability to acquire and apply new technologies independently
""",
    "Analyst": """
ROLE-SPECIFIC EMPHASIS (Analyst / Business Intelligence):
- Emphasize data analysis, BI, and SQL proficiency
- Highlight dashboards, KPIs, and reporting automation
- Stress translating data into actionable business recommendations
""",
}


def generate_summary(
    job_description: str,
    rewritten_bullets: List[str],
    job_title: str,
    role: str = "General"
) -> str:
    """
    Generate a professional summary via 2-step LLM pipeline.

    Step 1: Extract competencies + score bullets (single merged call)
    Step 2: Generate summary using fixed opening sentence + competencies + matched bullets

    Args:
        job_description: Target job description text
        rewritten_bullets: List of rewritten bullet strings from the rewrite step
        job_title: Target job title (reserved for future use in prompt enrichment)
        role: Role string from bullet library (e.g. "Help Desk", "Programmer", "Analyst")

    Returns:
        Summary string (3–4 sentences, 90–120 words)
    """
    logger.debug(f"Generating summary for role='{role}', {len(rewritten_bullets)} bullets")

    # Call 1: competency extraction + experience scoring
    call1_result = call_openai_json(
        competency_and_scoring_prompt(job_description, rewritten_bullets),
        temperature=config.llm.temperature_deterministic,
        timeout=config.llm.analysis_timeout
    )
    competencies = call1_result.get("competencies", [])
    matched_bullets = (
        call1_result.get("strong_matches", []) + call1_result.get("partial_matches", [])
    )
    logger.debug(
        f"Competency extraction: {len(competencies)} competencies, "
        f"{len(matched_bullets)} matched bullets"
    )

    # Fall back to all bullets if matching returns nothing
    if not matched_bullets:
        logger.warning("No matched bullets from competency scoring; using all rewritten bullets")
        matched_bullets = rewritten_bullets

    opening_sentence = _SUMMARY_OPENING_SENTENCES.get(role, _DEFAULT_OPENING)
    role_rules = _SUMMARY_ROLE_EMPHASIS.get(role, "")

    # Call 2: summary generation
    call2_result = call_openai_json(
        summary_generation_prompt(opening_sentence, competencies, matched_bullets, role_rules),
        temperature=config.llm.temperature_creative,
        timeout=config.llm.rewriting_timeout
    )
    summary = call2_result["summary"]
    logger.info(f"Summary generated ({len(summary.split())} words)")
    return summary
