import json
from app.openai_client import call_openai_json
from app.prompts import bullet_selection_prompt, rewrite_prompt

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
        )
    )

    bullet_html = "\n".join(f"<li>{b}</li>" for b in rewritten["rewritten_bullets"])
    return rewritten["summary"], bullet_html


def generate_resume(job_description, company_name,
                    company_info, job_change, bullet_files):

    result = {"summary": "", "spins": "", "programmer": "", "analyst": ""}
    summary_written = False

    for section, path in bullet_files.items():
        summary, bullets = process_section(
            path, job_description, company_name, company_info, job_change
        )
        result[section] = bullets
        if not summary_written:
            result["summary"] = summary
            summary_written = True

    return result
