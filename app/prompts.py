def bullet_selection_prompt(job_description, bullets):
    """
    Build LLM prompt for scoring resume bullets against job description.

    Args:
        job_description: Target job description text
        bullets: List of bullet strings to score

    Returns:
        OpenAI chat messages list with scoring instructions
    """
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

def _build_base_rewrite_prompt(job_description, company_name, company_info,
                                selected_bullets, job_change):
    """
    Base prompt builder for bullet rewriting.

    Args:
        job_description: Target job description
        company_name: Target company name
        company_info: Additional company context
        selected_bullets: List of selected bullet strings
        job_change: Context about job change (customer-facing, etc.)

    Returns:
        List with single dict containing role and content keys for OpenAI API
    """
    return [{
        "role": "user",
        "content": f"""
=== ROLE ===
You are an expert technical recruiter and resume optimization specialist focused on clarity, relevance, and FACTUAL ACCURACY.
Your only goal is to rewrite bullets for better alignment with the job description WITHOUT changing their meaning.

=== TASK ===
Rewrite the provided resume bullets to better align with the job description.
Prioritize the skills and experiences most likely to be scanned by a technical recruiter or ATS(Applicant Tracking System) for the role.

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
    - If a sentence requires a subject, rewrite it to foreground the skill, achievement, or role instead
    - Use active, professional, confident, neutral tone
    - Avoid superlatives (best, optimal, cutting-edge, innovative) unless in original
    - Avoid marketing language (transformative, game-changing, revolutionary)
    - Prefer concrete verbs over abstract ones
    - Do NOT end bullets with a period

6. ALIGNMENT RULES
    - You MAY emphasize aspects that match the job description
    - You MAY reorder information within a bullet for clarity
    - You MAY use terminology from the job description if it's synonymous with original meaning
    - You MAY NOT add content to "fit better" with the job

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
    ]
}}

REQUIREMENTS:
- rewritten_bullets: array with same count as input bullets
- Each bullet must be factually equivalent to its original
- No additional keys or fields

=== VERIFICATION CHECKLIST ===

Before returning your response, verify:
1. Every rewritten bullet has a corresponding input bullet
2. No new technologies or tools were added
3. No metrics or numbers were invented
4. Scope and seniority remain unchanged
5. JSON is valid and complete
"""
    }]

def rewrite_prompt_helpdesk(job_description, company_name, company_info,
                            selected_bullets, job_change):
    """Generate prompt for Help Desk role bullet rewriting."""
    return _build_base_rewrite_prompt(
        job_description, company_name, company_info,
        selected_bullets, job_change
    )

def rewrite_prompt_programmer(job_description, company_name, company_info,
                            selected_bullets, job_change):
    """Generate prompt for Programmer/Developer role bullet rewriting."""
    return _build_base_rewrite_prompt(
        job_description, company_name, company_info,
        selected_bullets, job_change
    )

def rewrite_prompt_analyst(job_description, company_name, company_info,
                        selected_bullets, job_change):
    """Generate prompt for Analyst role bullet rewriting."""
    return _build_base_rewrite_prompt(
        job_description, company_name, company_info,
        selected_bullets, job_change
    )

def rewrite_prompt_default(job_description, company_name, company_info,
                        selected_bullets, job_change):
    """Generate prompt for default/generic role bullet rewriting."""
    return _build_base_rewrite_prompt(
        job_description, company_name, company_info,
        selected_bullets, job_change
    )

def rewrite_prompt(job_description, company_name, company_info,
                selected_bullets, job_change, role="General"):
    """
    Main entry point for generating rewrite prompts.
    Dispatches to appropriate role-specific strategy function.

    Args:
        job_description: Target job description
        company_name: Target company name
        company_info: Additional company context
        selected_bullets: List of selected bullet strings
        job_change: Context about job change (customer-facing, etc.)
        role: Role type from bullet file (e.g., "Help Desk", "Programmer", "Analyst")

    Returns:
        Role-specific prompt with appropriate summary generation rules
    """
    # Strategy mapping: role name -> strategy function
    ROLE_STRATEGIES = {
        "Help Desk": rewrite_prompt_helpdesk,
        "Programmer": rewrite_prompt_programmer,
        "Analyst": rewrite_prompt_analyst,
        # Add more roles here as bullet files are created:
        # "DevOps Engineer": rewrite_prompt_devops,
        # "QA Engineer": rewrite_prompt_qa,
    }

    # Select strategy or use default
    strategy_fn = ROLE_STRATEGIES.get(role, rewrite_prompt_default)

    # Execute selected strategy
    return strategy_fn(
        job_description, company_name, company_info,
        selected_bullets, job_change
    )


def competency_and_scoring_prompt(job_description, rewritten_bullets):
    """
    Merged Step 1+2: Extract core competencies from JD and score rewritten bullets against them.

    Args:
        job_description: Target job description text
        rewritten_bullets: List of rewritten bullet strings

    Returns:
        OpenAI chat messages list
    """
    bullets_text = "\n".join(f"- {b}" for b in rewritten_bullets)
    return [{
        "role": "user",
        "content": f"""Analyze the following job description and rewritten resume bullets.

PART 1 — COMPETENCY EXTRACTION:
Extract the 5–7 most critical competencies required for success in this role.
- Focus on technical skills, domain knowledge, tools, scope of responsibility, and problem types.
- Ignore generic phrases: 'fast-paced,' 'team player,' 'excellent communication skills,' etc.
- Group similar requirements into higher-level competencies.

PART 2 — EXPERIENCE MATCHING:
For each competency, identify which bullets are strong matches or partial matches.
Strong match: bullet directly demonstrates this competency.
Partial match: bullet is relevant but not a direct demonstration.

JOB DESCRIPTION:
{job_description}

REWRITTEN BULLETS:
{bullets_text}

Return ONLY valid JSON:
{{
    "competencies": ["competency 1", "competency 2"],
    "strong_matches": ["bullet text", "..."],
    "partial_matches": ["bullet text", "..."]
}}"""
    }]


def summary_generation_prompt(opening_sentence, competencies, matched_bullets,
                               role_specific_rules=""):
    """
    Step 2: Generate a 3–4 sentence professional summary using competencies and matched bullets.

    Args:
        opening_sentence: Fixed role-keyed opening sentence (used verbatim as first sentence)
        competencies: List of extracted core competencies
        matched_bullets: List of bullet strings (strong + partial matches)
        role_specific_rules: Optional role-specific emphasis block

    Returns:
        OpenAI chat messages list
    """
    competencies_text = "\n".join(f"- {c}" for c in competencies)
    bullets_text = "\n".join(f"- {b}" for b in matched_bullets)
    return [{
        "role": "user",
        "content": f"""Write a 3–4 sentence professional résumé summary using the inputs below.

REQUIRED OPENING SENTENCE (use verbatim as the first sentence):
{opening_sentence}

Extracted Core Competencies:
{competencies_text}

Relevant Experience Highlights:
{bullets_text}

Constraints:
- Begin with the REQUIRED OPENING SENTENCE exactly as written above.
- Emphasize concrete technical scope and environments (startup, state government, executive-level support).
- After the opening sentence, at most 2 sentences may contain a measurable result (a specific percentage, headcount, dollar figure, or fixed integer). All other sentences must describe competencies, technical scope, or environments — no quantified metrics.
- Avoid soft-skill buzzwords (no 'results-driven,' 'passionate,' 'dynamic,' etc.).
- Do not mention that you are applying for the role.
- Keep tone direct and factual.
- Limit to 90–120 words total (including the opening sentence).
- If some experience is less directly aligned with the job title, reframe it in a way that highlights transferable technical or operational skills.
- Write in résumé style with implied subject (no 'I,' 'me,' 'my,' no 'the candidate').

{role_specific_rules}

Return ONLY valid JSON:
{{"summary": "3–4 sentence summary here"}}"""
    }]
