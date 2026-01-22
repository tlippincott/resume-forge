from app.distribution_engine import classify_bullets, rebalance
from app.openai_client import call_openai_json
from app.prompts import bullet_selection_prompt, rewrite_prompt
import json

def process_section(bullet_file, job_description,
                    company_name, company_info, job_change):

    with open(bullet_file, "r", encoding="utf-8") as f:
        bullets = json.load(f)["bullets"]

    selected = call_openai_json(
        bullet_selection_prompt(job_description, bullets)
    )["selected_bullets"]

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

    bullet_html = "\n".join(f"<li>{b}</li>" for b in rewritten["rewritten_bullets"])
    return rewritten["summary"], bullet_html


def generate_resume(job_description, company_name,
                    company_info, bullet_file, job_change,):

    with open(bullet_file, "r", encoding="utf-8") as f:
        all_bullets = json.load(f)["bullets"]

    # 1. Select top 28–32 bullets
    selected = call_openai_json(
        bullet_selection_prompt(job_description, all_bullets)
    )["selected_bullets"]

    # 2. Rewrite selected bullets
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

    # 3. Classify + rebalance
    assignments = classify_bullets(rewritten_bullets)
    sections = rebalance(assignments)

    # 4. Convert to HTML
    result = {
        "summary": rewritten["summary"],
        "spins": "\n".join(f"<li>{b}</li>" for b in sections["spins"]),
        "programmer": "\n".join(f"<li>{b}</li>" for b in sections["programmer"]),
        "analyst": "\n".join(f"<li>{b}</li>" for b in sections["analyst"]),
    }

    return result
