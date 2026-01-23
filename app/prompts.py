def bullet_selection_prompt(job_description, bullets):
    return [{
        "role": "user",
        "content": f"""
You are evaluating resume bullets against a job description.

TASK:
For each bullet, assign a relevance score from 0–5 based on how well
it matches the job description.

SCORING GUIDE:
5 = Direct, strong match to core responsibilities
4 = Clear match to important requirements
3 = Partial or supporting relevance
2 = Weak or indirect relevance
1 = Very minimal relevance
0 = No relevance

RULES:
- Do not rewrite bullets
- Do not invent bullets
- Score every bullet independently

INPUT:
JOB DESCRIPTION:
{job_description}

BULLETS:
{bullets}

RETURN JSON:
{{
    "scored_bullets": [
    {{ "bullet": "...", "score": 0-5 }}
    ]
}}
"""
    }]

def rewrite_prompt(job_description, company_name, company_info, selected_bullets, job_change):
    return [{
        "role": "user",
        "content": f"""
=== ROLE ===
You are a resume optimization specialist focused on clarity, relevance, and FACTUAL ACCURACY.
Your only goal is to rewrite bullets for better alignment WITHOUT changing their meaning.

=== TASK ===
Rewrite the provided resume bullets to better align with the job description.
Then generate a 2-3 sentence professional summary based ONLY on the rewritten bullets.

CRITICAL: You are refining language, NOT inventing experience.

=== STRICT RULES - WHAT YOU MUST NOT DO ===

1. PRESERVE SCOPE AND MEANING
    - Do NOT inflate team sizes, project scope, or seniority level
    - Do NOT change what was actually done
    - Do NOT change "contributed to" into "led" or "owned"
    - Do NOT change "supported" into "architected" or "designed"

2. NO TECHNOLOGY INVENTION
    - Do NOT add technologies, tools, frameworks, or platforms not in the original
    - Do NOT add specific version numbers unless present in original
    - Do NOT add methodologies (Agile, SCRUM, etc.) unless present in original

3. NO METRIC INVENTION
    - Do NOT add percentages, numbers, or performance metrics unless present in original
    - Do NOT add time periods or durations unless present in original
    - Do NOT estimate impact with numbers you don't have

4. NO EXPERIENCE FABRICATION
    - Do NOT add responsibilities not in the original bullet
    - Do NOT add stakeholders or teams not mentioned in original
    - Do NOT add outcomes or results not in the original

5. LANGUAGE CONSTRAINTS
    - Use active, professional, neutral tone
    - Avoid superlatives (best, optimal, cutting-edge, innovative) unless in original
    - Avoid marketing language (transformative, game-changing, revolutionary)
    - Prefer concrete verbs over abstract ones

6. ALIGNMENT RULES
    - You MAY emphasize aspects that match the job description
    - You MAY reorder information within a bullet for clarity
    - You MAY use terminology from the job description if it's synonymous with original meaning
    - You MAY NOT add content to "fit better" with the job

=== SUMMARY GENERATION RULES ===

The summary must be:
- 2-3 complete sentences (40-60 words total)
- Grounded in themes from the REWRITTEN BULLETS ONLY
- Free of unverifiable claims about passion, enthusiasm, or cultural fit
- Focused on role experience and key technical/domain areas present in bullets
- Written in third person or first person (match resume style)

Do NOT include in summary:
- Technologies not present in bullets
- Claims about years of experience (unless counting from bullets)
- Statements about career goals or aspirations
- Personality traits or soft skills not evidenced in bullets

=== INPUT ===

JOB DESCRIPTION:
{job_description}

COMPANY NAME:
{company_name}

COMPANY INFO:
{company_info}

BULLETS TO REWRITE:
{selected_bullets}

JOB CHANGE CONTEXT:
{job_change}

=== OUTPUT CONTRACT ===

Return ONLY valid JSON with this exact structure:

{{
    "rewritten_bullets": [
        "First rewritten bullet preserving original meaning",
        "Second rewritten bullet preserving original meaning",
        "..."
    ],
    "summary": "2-3 sentence professional summary grounded in the bullets above"
}}

REQUIREMENTS:
- rewritten_bullets: array with same count as input bullets
- Each bullet must be factually equivalent to its original
- summary: single string, 2-3 sentences, 40-60 words
- No additional keys or fields

=== VERIFICATION CHECKLIST ===

Before returning your response, verify:
1. Every rewritten bullet has a corresponding input bullet
2. No new technologies or tools were added
3. No metrics or numbers were invented
4. Scope and seniority remain unchanged
5. Summary only references content in rewritten bullets
6. JSON is valid and complete
"""
    }]

def distribution_prompt(bullets):
    return [{
        "role": "user",
        "content": f"""
Assign each bullet to exactly one section.

SECTIONS:
- spins: end-user support, customer interaction, issue resolution,
        communication, collaboration, service delivery, operational impact

- programmer: tooling, automation, scripting, system configuration,
        integrations, deployments, technical implementation

- analyst: troubleshooting methodology, root cause analysis,
        documentation, reporting, metrics, process improvement


RULES:
- Do not rewrite bullets
- Do not invent bullets
- Each bullet appears once

GUIDANCE:
- Most bullet sets should naturally span all three sections
- Prefer balanced distribution unless a bullet strongly fits one section

BULLETS:
{bullets}

RETURN JSON:
{{
    "assignments": [
        {{ "bullet": "...", "section": "spins|programmer|analyst" }}
    ]
}}
"""
    }]
