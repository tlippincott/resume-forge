from app.openai_client import call_openai_json

def cover_letter_prompt(summary, bullets, job_title, job_description, company_name,
                        company_info, job_change):
    return [{
        "role": "user",
        "content": f"""
Write a cover letter body.

JOB TITLE: {job_title}
COMPANY: {company_name}

SUMMARY:
{summary}

BULLETS:
{bullets}

RETURN JSON:
{{ "cover_letter_body": [] }}
"""
    }]

def generate_cover_letter(resume_data, job_title, job_description, company_name,
                            company_info, job_change):
    
    bullets = resume_data["spins"] + resume_data["programmer"] + resume_data["analyst"]

    result = call_openai_json(
        cover_letter_prompt(
            resume_data["summary"], bullets,
            job_title, job_description,
            company_name, company_info, job_change
        )
    )

    return "<p>" + "</p><p>".join(result["cover_letter_body"]) + "</p>"
