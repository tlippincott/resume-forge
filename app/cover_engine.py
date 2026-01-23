from app.openai_client import call_openai_json

def cover_letter_prompt(summary, bullets, job_title, job_description, company_name,
                        company_info, job_change):
   return [{
      "role": "user",
      "content": f"""
=== ROLE ===
You are a professional cover letter writer specializing in authentic, grounded narratives.
Your goal is to connect documented experience to employer needs WITHOUT inventing claims.

=== TASK ===
Write a 3-paragraph cover letter body that:
1. Opens with clear statement of interest and relevant background
2. Connects documented experience to job requirements
3. Closes with genuine interest in the specific role

The letter must be grounded in ONLY the provided summary and bullets.

=== STRICT RULES - WHAT YOU MUST NOT DO ===

1. EXPERIENCE GROUNDING
   - Do NOT reference accomplishments not in the bullets
   - Do NOT claim expertise in technologies not in the bullets
   - Do NOT invent projects, clients, or outcomes
   - Do NOT extrapolate beyond what is documented

2. NO UNVERIFIABLE CLAIMS
   - Do NOT make claims about:
     * "Passionate about" or "excited by" (unless job_change context supports it)
     * Cultural fit or company values alignment
     * Personal motivations or career aspirations
     * Soft skills not evidenced in bullets (team player, excellent communicator, etc.)

3. NO METRIC INVENTION
   - Do NOT add percentages, time periods, or scale unless in bullets
   - Do NOT estimate impact with numbers you don't have

4. COMPANY RESEARCH BOUNDARIES
   - You MAY reference company_info if provided
   - You MAY reference specific aspects of job_description
   - You MAY NOT invent facts about the company
   - You MAY NOT claim knowledge of company culture, mission, or values unless in company_info

5. LANGUAGE CONSTRAINTS
   - Use professional, genuine tone
   - Avoid hyperbole (thrilled, perfect fit, dream job, ideal candidate)
   - Avoid generic statements that could apply to any job
   - Prefer concrete connections over abstract enthusiasm

=== WHAT YOU MAY DO ===

1. THEME EXTRACTION
   - Identify themes across bullets (e.g., "customer-facing technical support")
   - Connect themes to job requirements
   - Reference domain areas present in multiple bullets

2. STRATEGIC EMPHASIS
   - Emphasize bullets most relevant to job_description
   - Highlight alignment between experience and role needs
   - Draw connections between past work and future responsibilities

3. CONTEXTUAL FRAMING
   - Reference the job_change context appropriately:
     * If True: acknowledge transition, emphasize transferable skills
     * If False: emphasize deepening expertise, growth in similar role
   - Use company_info to show genuine research (if provided)

=== STRUCTURE REQUIREMENTS ===

Paragraph 1 (OPENING): 3-4 sentences, 60-80 words
- State the role you're applying for
- Briefly establish relevant background from summary
- Create a clear hook connecting your experience to their needs
- Do NOT use cliches like "I am writing to apply for..."

Paragraph 2 (BODY): 4-6 sentences, 100-130 words
- Connect 2-3 key themes from bullets to job requirements
- Use specific but grounded language
- Reference documented accomplishments that align with role
- Show understanding of what the role requires
- Do NOT list bullets - synthesize themes

Paragraph 3 (CLOSING): 2-3 sentences, 40-60 words
- Reaffirm interest in the SPECIFIC role/company
- Reference one concrete aspect of job or company (if info provided)
- Professional close without desperation or excessive enthusiasm
- Do NOT include availability for interview - that's assumed

=== INPUT ===

JOB TITLE:
{job_title}

JOB DESCRIPTION:
{job_description}

COMPANY NAME:
{company_name}

COMPANY INFO:
{company_info}

PROFESSIONAL SUMMARY:
{summary}

RESUME BULLETS:
{bullets}

JOB CHANGE CONTEXT:
{job_change}

=== OUTPUT CONTRACT ===

Return ONLY valid JSON with this exact structure:

{{
   "cover_letter_body": [
      "First paragraph: opening (60-80 words)",
      "Second paragraph: body (100-130 words)",
      "Third paragraph: closing (40-60 words)"
   ]
}}

REQUIREMENTS:
- Exactly 3 paragraphs as array elements
- Each paragraph is a single string (complete paragraph, not individual sentences)
- Total word count: 200-270 words
- No additional keys or fields

=== VERIFICATION CHECKLIST ===

Before returning your response, verify:
1. Every claim is grounded in summary or bullets
2. No technologies mentioned that aren't in the resume content
3. No unverifiable personality claims or enthusiasm statements
4. Paragraphs meet length requirements
5. Letter is specific to THIS job/company, not generic
6. Tone is professional and authentic, not desperate or hyperbolic
7. JSON is valid with exactly 3 array elements
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
      ),
      temperature=0.7
   )

   return "<p>" + "</p><p>".join(result["cover_letter_body"]) + "</p>"
