import html
from app.config import config
from app.openai_client import call_openai_json
from app.exceptions import DataProcessingError
from app.logging_config import get_logger

logger = get_logger(__name__)

def cover_letter_prompt(summary, bullets, job_title, job_description, company_name,
                        company_info, job_change, company_interest=None,
                        gap_explanation=None, jd_analysis=None):
   # Format company_interest for better readability
   company_interest_text = "Not provided"
   if company_interest:
      lines = []
      if company_interest.get('hook'):
         lines.append(f"  - Hook: {company_interest['hook']}")
      if company_interest.get('alignment'):
         lines.append(f"  - Alignment: {company_interest['alignment']}")
      if company_interest.get('credibility_anchor'):
         lines.append(f"  - Credibility Anchor: {company_interest['credibility_anchor']}")
      company_interest_text = "\n".join(lines) if lines else "Not provided"

   # Format JD analysis if provided (Phase 1A: reuse pre-analyzed JD intelligence)
   jd_intelligence_text = ""
   if jd_analysis:
      jd_intelligence_text = f"""
=== JOB DESCRIPTION INTELLIGENCE (PRE-ANALYZED) ===

Use this pre-extracted intelligence from the job description instead of re-analyzing the raw JD text:

REQUIRED SKILLS:
{', '.join(jd_analysis.get('required_skills', []))}

PREFERRED SKILLS:
{', '.join(jd_analysis.get('preferred_skills', []))}

KEY CATEGORIES:
{', '.join(jd_analysis.get('job_categories', []))}

ALL KEYWORDS:
{', '.join(jd_analysis.get('all_keywords', []))}

When writing the cover letter, prioritize alignment with REQUIRED SKILLS and reference PREFERRED SKILLS where your experience overlaps.
"""

   # Determine which case to use
   has_company_interest = bool(company_interest)
   has_gap = bool(gap_explanation and gap_explanation.strip())

   if has_company_interest and has_gap:
      case_to_use = "CASE 4 (6 paragraphs: both motivation and gap)"
   elif has_company_interest:
      case_to_use = "CASE 2 (5 paragraphs: motivation only)"
   elif has_gap:
      case_to_use = "CASE 3 (5 paragraphs: gap only)"
   else:
      case_to_use = "CASE 1 (4 paragraphs: base)"

   return [{
      "role": "user",
      "content": f"""
=== ROLE ===
You are a professional cover letter writer specializing in authentic, grounded narratives.
Your goal is to connect documented experience to employer needs WITHOUT inventing claims.

=== TASK ===
Write a cover letter body that:
1. Opens with immediate alignment and clear intent
2. Optionally includes motivation/company interest (if provided)
3. Provides evidence of capability through specific experience
4. Differentiates the candidate with unique value and context
5. Closes with forward motion and professionalism

The letter must be grounded in ONLY the provided summary and bullets.
The structure will be 4 OR 5 paragraphs depending on whether company_interest is provided.

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

The letter structure adapts based on which optional sections are provided:

CASE 1: Base structure (4 paragraphs - neither company_interest nor gap_explanation):
   - P1: Immediate alignment and intent (60-80 words)
   - P2: Evidence of capability (90-120 words)
   - P3: Differentiation and context (70-100 words)
   - P4: Forward motion and professionalism (30-50 words)

CASE 2: With company_interest ONLY (5 paragraphs):
   - P1: Immediate alignment and intent (60-80 words)
   - P2: Motivation/company interest (50-70 words)
   - P3: Evidence of capability (90-120 words)
   - P4: Differentiation and context (70-100 words)
   - P5: Forward motion and professionalism (30-50 words)

CASE 3: With gap_explanation ONLY (5 paragraphs):
   - P1: Immediate alignment and intent (60-80 words)
   - P2: Evidence of capability (90-120 words)
   - P3: Differentiation and context (70-100 words)
   - P4: Gap explanation (60-90 words)
   - P5: Forward motion and professionalism (30-50 words)

CASE 4: With BOTH company_interest AND gap_explanation (6 paragraphs):
   - P1: Immediate alignment and intent (60-80 words)
   - P2: Motivation/company interest (50-70 words)
   - P3: Evidence of capability (90-120 words)
   - P4: Differentiation and context (70-100 words)
   - P5: Gap explanation (60-90 words)
   - P6: Forward motion and professionalism (30-50 words)

CRITICAL INSERTION RULES:
- Gap explanation ALWAYS goes immediately before the closing paragraph
- Gap explanation is ALWAYS the second-to-last paragraph
- Motivation paragraph (if present) goes after P1 (alignment)
- Closing paragraph is ALWAYS last

Paragraph 1 (IMMEDIATE ALIGNMENT AND INTENT): 3-4 sentences, 60-80 words
- State the role you're applying for in the opening sentence
- Immediately establish relevant background from summary that aligns with their needs
- Create a clear connection between your experience and what they're looking for
- Do NOT use clichés like "I am writing to apply for..." or "I was excited to see..."
- Focus on immediate relevance, not enthusiasm

[CONDITIONAL] Paragraph 2 (MOTIVATION/COMPANY INTEREST): 2-3 sentences, 50-70 words
- ONLY GENERATE IF company_interest is provided with at least one non-empty field
- Synthesize only the provided fields (hook, alignment, credibility anchor) into a specific, grounded statement; omit any field not present
- Show "I chose you on purpose" without being gushy or generic
- Reference concrete aspects: product features, tech stack, market position, problems they solve
- Avoid mission-statement plagiarism or enthusiasm-heavy language ("thrilled", "perfect fit")
- DO NOT invent company facts not in company_interest or company_info
- Skip entirely if company_interest is not provided or all fields are empty

Paragraph N (EVIDENCE OF CAPABILITY): 4-5 sentences, 90-120 words
- This is P3 if motivation included, P2 if not
- Identify 1-2 key responsibilities or requirements from the job description
- Match them to specific documented experience from bullets
- Use concrete but grounded language - reference actual work done
- Show understanding of what the role requires through how you describe your experience
- Synthesize themes across bullets rather than listing individual accomplishments
- Do NOT invent claims or extrapolate beyond documented work

Paragraph N+1 (DIFFERENTIATION AND CONTEXT): 3-4 sentences, 70-100 words
- This is P4 if motivation included, P3 if not
- Provide context that differentiates you or explains your career positioning
- If job_change is True: acknowledge the transition and emphasize transferable skills/value
- If job_change is False: emphasize depth of expertise and growth trajectory in similar roles
- Reference unique aspects of your background that create value for this specific role
- Use company_info (if provided) to show genuine research and alignment
- Avoid generic statements that could apply to any candidate

[CONDITIONAL] Paragraph N+2 (GAP EXPLANATION): 3-4 sentences, 60-90 words
- ONLY GENERATE IF gap_explanation is provided and not empty
- This paragraph is ALWAYS second-to-last (before closing)
- Use the EXACT TEXT provided in gap_explanation parameter
- Do NOT modify, rephrase, or embellish the provided text
- Do NOT add additional context or commentary
- Simply include the provided paragraph verbatim

Paragraph FINAL (FORWARD MOTION AND PROFESSIONALISM): 1-2 sentences, 30-50 words
- This is ALWAYS the last paragraph
- Briefly reaffirm interest in the specific role and company
- Professional, confident close without desperation or excessive enthusiasm
- Do NOT include availability for interview - that's assumed
- Do NOT use phrases like "I look forward to hearing from you"
- Keep it short and direct

=== INPUT ===

JOB TITLE:
{job_title}

JOB DESCRIPTION:
{job_description}
{jd_intelligence_text}
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

COMPANY INTEREST (OPTIONAL):
{company_interest_text}

GAP EXPLANATION (OPTIONAL):
{gap_explanation or "Not provided"}

=== YOU MUST USE: {case_to_use} ===

CONDITIONAL PARAGRAPH LOGIC:

MOTIVATION PARAGRAPH:
- IF company_interest is provided with at least one non-empty field:
  * Generate Paragraph 2 (Motivation/Company Interest, 50-70 words)
  * Synthesize only the provided (non-empty) fields into a specific, grounded statement
  * Use "I chose you on purpose" tone, not "passionate about synergy"
  * Reference concrete aspects (product, tech, market, problem they solve)
  * Avoid gushy language and mission-statement plagiarism
- IF company_interest is NOT provided or all fields are empty:
  * Skip Paragraph 2 entirely

GAP EXPLANATION PARAGRAPH:
- IF gap_explanation is provided and not empty:
  * Insert gap paragraph as SECOND-TO-LAST paragraph (immediately before closing)
  * Use VERBATIM text from gap_explanation parameter
  * Do NOT modify, rephrase, or add commentary
- IF gap_explanation is NOT provided or empty:
  * Skip gap paragraph entirely

=== OUTPUT CONTRACT ===

Return ONLY valid JSON with this exact structure based on which optional sections are provided:

CASE 1: Neither company_interest nor gap_explanation (4 paragraphs):
{{
   "cover_letter_body": [
      "Paragraph 1: immediate alignment and intent (60-80 words)",
      "Paragraph 2: evidence of capability (90-120 words)",
      "Paragraph 3: differentiation and context (70-100 words)",
      "Paragraph 4: forward motion and professionalism (30-50 words)"
   ]
}}

CASE 2: company_interest ONLY (5 paragraphs):
{{
   "cover_letter_body": [
      "Paragraph 1: immediate alignment and intent (60-80 words)",
      "Paragraph 2: motivation/company interest (50-70 words)",
      "Paragraph 3: evidence of capability (90-120 words)",
      "Paragraph 4: differentiation and context (70-100 words)",
      "Paragraph 5: forward motion and professionalism (30-50 words)"
   ]
}}

CASE 3: gap_explanation ONLY (5 paragraphs):
{{
   "cover_letter_body": [
      "Paragraph 1: immediate alignment and intent (60-80 words)",
      "Paragraph 2: evidence of capability (90-120 words)",
      "Paragraph 3: differentiation and context (70-100 words)",
      "Paragraph 4: gap explanation - VERBATIM from input (60-90 words)",
      "Paragraph 5: forward motion and professionalism (30-50 words)"
   ]
}}

CASE 4: BOTH company_interest AND gap_explanation (6 paragraphs):
{{
   "cover_letter_body": [
      "Paragraph 1: immediate alignment and intent (60-80 words)",
      "Paragraph 2: motivation/company interest (50-70 words)",
      "Paragraph 3: evidence of capability (90-120 words)",
      "Paragraph 4: differentiation and context (70-100 words)",
      "Paragraph 5: gap explanation - VERBATIM from input (60-90 words)",
      "Paragraph 6: forward motion and professionalism (30-50 words)"
   ]
}}

REQUIREMENTS:
- CRITICAL: The JSON array MUST contain EXACTLY the number of elements specified by your case:
  * CASE 1: Exactly 4 array elements
  * CASE 2: Exactly 5 array elements
  * CASE 3: Exactly 5 array elements
  * CASE 4: Exactly 6 array elements
- Each paragraph is a single string (complete paragraph, not individual sentences)
- DO NOT combine paragraphs - each must be separate
- Gap explanation (if included) uses EXACT TEXT from gap_explanation parameter
- Total word count varies by structure:
  * 4 paragraphs: 250-400 words
  * 5 paragraphs: 300-470 words
  * 6 paragraphs: 350-540 words
- No additional keys or fields

=== VERIFICATION CHECKLIST ===

Before returning your response, verify:
1. Every claim is grounded in summary or bullets
2. No technologies mentioned that aren't in the resume content
3. No unverifiable personality claims or enthusiasm statements
4. Paragraphs meet length requirements based on structure:
   - 4 paragraphs: (60-80, 90-120, 70-100, 30-50 words)
   - 5 paragraphs with motivation: (60-80, 50-70, 90-120, 70-100, 30-50 words)
   - 5 paragraphs with gap: (60-80, 90-120, 70-100, 60-90, 30-50 words)
   - 6 paragraphs: (60-80, 50-70, 90-120, 70-100, 60-90, 30-50 words)
5. Letter is specific to THIS job/company, not generic
6. Tone is professional and authentic, not desperate or hyperbolic
7. JSON is valid with exactly 4, 5, OR 6 array elements (based on optional sections)
8. Total word count matches structure:
   - 4 paragraphs: 250-400 words
   - 5 paragraphs: 300-470 words
   - 6 paragraphs: 350-540 words
9. If Paragraph 2 (motivation) is included, it avoids gushy language and mission-statement plagiarism
10. If gap explanation is included, it uses VERBATIM text from gap_explanation parameter
"""
   }]

def generate_cover_letter(resume_data, job_title, job_description, company_name,
                           company_info, job_change, company_interest=None,
                           gap_explanation=None, jd_analysis=None):
   """
   Generate a tailored cover letter based on resume data and job description.

   Args:
       resume_data: Resume data dict containing summary and section bullets
       job_title: Target job title
       job_description: Target job description
       company_name: Target company name
       company_info: Information about the target company
       job_change: Boolean indicating if this is a career change
       company_interest: Optional dict with hook, alignment, credibility_anchor
       gap_explanation: Optional employment gap explanation text
       jd_analysis: Optional pre-analyzed JD intelligence (Phase 1A optimization)

   Returns:
       HTML-formatted cover letter body

   Raises:
       DataProcessingError: If cover letter generation fails
   """
   logger.info(f"Generating cover letter for {job_title} at {company_name}")

   # Phase 1A: Log whether we're using pre-analyzed JD intelligence
   if jd_analysis:
      logger.info("Using pre-analyzed JD intelligence (Phase 1A optimization - no redundant analysis)")
   else:
      logger.info("No pre-analyzed JD provided - will analyze raw JD text")

   bullets = resume_data["spins"] + resume_data["programmer"] + resume_data["analyst"]
   logger.debug(f"Using {len(bullets)} bullets from resume")

   try:
      result = call_openai_json(
         cover_letter_prompt(
               resume_data["summary"], bullets,
               job_title, job_description,
               company_name, company_info, job_change,
               company_interest,
               gap_explanation,
               jd_analysis
         ),
         temperature=config.llm.temperature_creative,
         timeout=config.llm.cover_letter_timeout
      )
   except Exception as e:
      logger.error(f"Failed to generate cover letter: {e}")
      raise

   if "cover_letter_body" not in result:
      logger.error("LLM response missing 'cover_letter_body' key")
      raise DataProcessingError("Invalid LLM response: missing cover_letter_body")

   if not isinstance(result["cover_letter_body"], list):
      logger.error("cover_letter_body is not a list")
      raise DataProcessingError("Invalid LLM response: cover_letter_body must be a list")

   logger.info(f"Generated cover letter with {len(result['cover_letter_body'])} paragraphs")
   escaped_paragraphs = [html.escape(p) for p in result["cover_letter_body"]]
   return "<p>" + "</p><p>".join(escaped_paragraphs) + "</p>"
