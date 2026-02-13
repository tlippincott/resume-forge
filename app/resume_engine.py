import json
import os
import random

from app.distribution_engine import classify_bullets, rebalance
from app.openai_client import call_openai_json
from app.prompts import bullet_selection_prompt, rewrite_prompt
from app.bullet_intelligence import (
    analyze_job_description,
    analyze_bullets,
    score_bullets_against_jd
)


def generate_resume(job_description, company_name,
                    company_info, bullet_file, job_change,):

    if not os.path.exists(bullet_file):
        raise ValueError(f"Bullet file not found: {bullet_file}")
    with open(bullet_file, "r", encoding="utf-8") as f:
        bullet_data = json.load(f)
        all_bullets = bullet_data["bullets"]
        role = bullet_data.get("role", "General")  # Default to "General" if role not present

    # 1. Score all bullets
    scored = call_openai_json(
        bullet_selection_prompt(job_description, all_bullets)
    )["scored_bullets"]

    # 2. Sort by score (deterministic)
    sorted_bullets = sorted(scored, key=lambda x: x["score"], reverse=True)

    # 3. Select top 38-42 (increased from 28-32 for larger replacement pool)
    count = random.randint(38, 42)
    selected = [item["bullet"] for item in sorted_bullets[:count]]

    # 4. Rewrite selected bullets for clarity and alignment
    rewritten = call_openai_json(
        rewrite_prompt(
            job_description,
            company_name,
            company_info,
            selected,
            job_change,
            role  # Pass role for strategy selection
        ),
        temperature=0.7
    )
    rewritten_bullets = rewritten["rewritten_bullets"]

    # === NEW: INTELLIGENT ANALYSIS ===

    # Step 1: Analyze job description (1 LLM call)
    jd_analysis = analyze_job_description(job_description)

    # Step 2: Analyze all rewritten bullets (1 LLM call for batch)
    analyzed_bullets = analyze_bullets(rewritten_bullets)

    # Step 3: Score bullets against JD (rule-based, no LLM)
    analyzed_bullets = score_bullets_against_jd(analyzed_bullets, jd_analysis)

    # 5. Classify bullets into sections
    assignments = classify_bullets(rewritten_bullets)

    # Add classification to analyzed bullets
    assignment_map = {a["bullet"]: a["section"] for a in assignments["assignments"]}
    for bullet_data in analyzed_bullets:
        bullet_data["section"] = assignment_map.get(bullet_data["text"], "analyst")

    # 6. Rebalance sections (enforce 10-12 per primary section)
    sections = rebalance(assignments)

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

    return result
