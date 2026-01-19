def bullet_selection_prompt(job_description, bullets):
    return [{
        "role": "user",
        "content": f"""
Select the 8–10 most relevant bullets.

JOB DESCRIPTION:
{job_description}

BULLETS:
{bullets}

RULES:
- Select only from provided bullets
- Do not rewrite or invent

RETURN JSON:
{{ "selected_bullets": [] }}
"""
    }]

def rewrite_prompt(job_description, company_name, company_info, selected_bullets, job_change):
    return [{
        "role": "user",
        "content": f"""
Rewrite bullets and generate a summary.

JOB DESCRIPTION:
{job_description}

COMPANY:
{company_name}

INFO:
{company_info}

BULLETS:
{selected_bullets}

JOB CHANGE: {job_change}

RETURN JSON:
{{
    "summary": "",
    "rewritten_bullets": []
}}
"""
    }]
