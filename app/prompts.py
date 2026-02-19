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
                                selected_bullets, job_change, role_specific_rules=""):
    """
    Base prompt builder with injection point for role-specific summary rules.

    Args:
        job_description: Target job description
        company_name: Target company name
        company_info: Additional company context
        selected_bullets: List of selected bullet strings
        job_change: Context about job change (customer-facing, etc.)
        role_specific_rules: Role-specific summary generation rules to inject

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
Then generate a 3-4 sentence professional summary based ONLY on the rewritten bullets.
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

=== SUMMARY GENERATION RULES ===

- 3-4 complete sentences (60-90 words total)
- Write in a résumé style using an implied subject
- No first-person pronouns (I, me, my)
- No third-person phrases such as “the candidate” or “this person”
- Prioritize the skills and experience most likely to be scanned by a technical recruiter or ATS(Applicant Tracking System) for this role.
- Optimized for clarity and recruiter skimmability
- Emphasize impact, outcomes, or problem-solving patterns
- Match the seniority and tone of job description
- Grounded in themes from the REWRITTEN BULLETS ONLY
- Free of unverifiable claims about passion, enthusiasm, or cultural fit
- Focused on role experience and key technical/domain areas present in bullets

{role_specific_rules}

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
    "summary": "3-4 sentence professional summary grounded in the bullets above"
}}

REQUIREMENTS:
- rewritten_bullets: array with same count as input bullets
- Each bullet must be factually equivalent to its original
- summary: single string, 3-4 sentences, 60-90 words
- No additional keys or fields

=== VERIFICATION CHECKLIST ===

Before returning your response, verify:
1. Every rewritten bullet has a corresponding input bullet
2. No new technologies or tools were added
3. No metrics or numbers were invented
4. Scope and seniority remain unchanged
6. JSON is valid and complete
"""
    }]

def rewrite_prompt_helpdesk(job_description, company_name, company_info,
                            selected_bullets, job_change):
    """Generate prompt with Help Desk role-specific summary rules"""
    role_rules = """
ROLE-SPECIFIC EMPHASIS (Help Desk / Technical Support):
- Emphasize 10+ years of customer service excellence and technical troubleshooting capabilities
- Highlight 90%% first-call resolution rate
- Stress communication skills with non-technical users and escalation handling
- Focus on breadth of technical knowledge across multiple platforms and systems
- Showcase application programming skills directly transferable to help desk roles
"""
    return _build_base_rewrite_prompt(
        job_description, company_name, company_info,
        selected_bullets, job_change, role_rules
    )

def rewrite_prompt_programmer(job_description, company_name, company_info,
                            selected_bullets, job_change):
    """Generate prompt with Programmer/Developer role-specific summary rules"""
    role_rules = """
ROLE-SPECIFIC EMPHASIS (Programmer / Software Developer):
- Emphasize 10+ years of software development lifecycle proficiency and coding expertise
- Highlight experience acquiring and applying new technologies independently, adapting quickly to changing requirements and contributing practical solutions in real-world settings 
- Focus on architecture, design patterns, code quality, and technical problem-solving
- Stress communication skills that bridge the gap between technical and non-technical individuals
- Showcase ability to build, deploy, and maintain software systems
"""
    return _build_base_rewrite_prompt(
        job_description, company_name, company_info,
        selected_bullets, job_change, role_rules
    )

def rewrite_prompt_analyst(job_description, company_name, company_info,
                        selected_bullets, job_change):
    """Generate prompt with Analyst role-specific summary rules"""
    role_rules = """
ROLE-SPECIFIC EMPHASIS (Analyst / Business Intelligence):
- Emphasize data analysis, business intelligence, and insights generation capabilities
- Highlight SQL proficiency, data visualization tools, and analytical frameworks
- Focus on business impact, reporting accuracy, and stakeholder communication
- Stress problem-solving through data, requirements gathering, and process improvement
- Include experience with dashboards, KPIs, data modeling, and reporting automation
- Showcase ability to translate data into actionable business recommendations
"""
    return _build_base_rewrite_prompt(
        job_description, company_name, company_info,
        selected_bullets, job_change, role_rules
    )

def rewrite_prompt_default(job_description, company_name, company_info,
                        selected_bullets, job_change):
    """Generate prompt with default/generic summary rules (no role-specific emphasis)"""
    return _build_base_rewrite_prompt(
        job_description, company_name, company_info,
        selected_bullets, job_change, ""
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

