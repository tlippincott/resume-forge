import json
import os
import random

from app.distribution_engine import classify_bullets, rebalance
from app.openai_client import call_openai_json
from app.prompts import bullet_selection_prompt, rewrite_prompt


def generate_resume(job_description, company_name,
                    company_info, bullet_file, job_change,):

    if not os.path.exists(bullet_file):
        raise ValueError(f"Bullet file not found: {bullet_file}")
    with open(bullet_file, "r", encoding="utf-8") as f:
        all_bullets = json.load(f)["bullets"]

    # 1. Score all bullets
    scored = call_openai_json(
        bullet_selection_prompt(job_description, all_bullets)
    )["scored_bullets"]

    # 2. Sort by score (deterministic)
    sorted_bullets = sorted(scored, key=lambda x: x["score"], reverse=True)

    # 3. Select top 28-32
    count = random.randint(28, 32)
    selected = [item["bullet"] for item in sorted_bullets[:count]]

    # 4. Rewrite selected bullets for clarity and alignment
    rewritten = call_openai_json(
        rewrite_prompt(
            job_description,
            company_name,
            company_info,
            selected,
            job_change
        ),
        temperature=0.7
    )
    rewritten_bullets = rewritten["rewritten_bullets"]

    # 5. Classify bullets into sections
    assignments = classify_bullets(rewritten_bullets)

    # 6. Rebalance sections (enforce 10-12 per primary section)
    sections = rebalance(assignments)

    # 7. Return plain lists
    result = {
        "summary": rewritten["summary"],
        "spins": sections["spins"],
        "programmer": sections["programmer"],
        "analyst": sections["analyst"],
    }

    return result
