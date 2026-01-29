import gradio as gr
from app.resume_engine import generate_resume
from app.cover_engine import generate_cover_letter
from pathlib import Path
from ui.resume_helpers import (
    build_html_bullets,
    bullets_to_text,
    text_to_bullets,
    load_resume_html,
    generate_pdf_file,
    load_cover_letter_html,
    generate_cover_letter_pdf_file,
    list_gap_files,
    load_gap_explanation,
    derive_gap_file_from_bullet_file
)

BULLET_DIR = "bullet_libs"
excluded_list = ["bullet_example.json"]

def list_bullet_files():
    bullet_path = Path(BULLET_DIR)
    if not bullet_path.exists():
        return []
    return sorted([
        (f.name, str(f))
        for f in Path(BULLET_DIR).iterdir()
        if f.is_file() and f.name not in excluded_list
    ])


def handle_generate(jd, job_title, company, info, bullet_file, job_change):
    """Generate resume and populate all tabs."""
    if not bullet_file:
        return {"error": "Please select a bullet file"}, "", "", "", "", "", [], [], [], "", ""

    # Call existing generate_resume()
    result = generate_resume(jd, company, info, bullet_file, job_change)

    # Extract plain lists (no parsing needed)
    summary = result["summary"]
    spins_list = result["spins"]
    programmer_list = result["programmer"]
    analyst_list = result["analyst"]

    # Convert to edit textbox format
    spins_text = bullets_to_text(spins_list)
    programmer_text = bullets_to_text(programmer_list)
    analyst_text = bullets_to_text(analyst_list)

    return (
        result,                # JSON output
        summary,               # Edit: summary textbox
        spins_text,           # Edit: spins textbox
        programmer_text,      # Edit: programmer textbox
        analyst_text,         # Edit: analyst textbox
        summary,               # State
        spins_list,           # State
        programmer_list,      # State
        analyst_list,         # State
        job_title,            # State: job_title
        bullet_file           # NEW: State: selected_bullet_file
    )


def handle_preview_update(summary_text, spins_text, programmer_text, analyst_text):
    """Update preview from edit fields."""
    # Convert textbox content to bullet lists
    spins_list = text_to_bullets(spins_text)
    programmer_list = text_to_bullets(programmer_text)
    analyst_list = text_to_bullets(analyst_text)

    # Build HTML strings
    spins_html = build_html_bullets(spins_list)
    programmer_html = build_html_bullets(programmer_list)
    analyst_html = build_html_bullets(analyst_list)

    # Load template and substitute
    html = load_resume_html(summary_text, spins_html, programmer_html, analyst_html)

    return html


def handle_pdf_generation(html_content):
    """Generate PDF from current preview."""
    try:
        pdf_path = generate_pdf_file(html_content)
        return pdf_path, f"PDF generated successfully: {Path(pdf_path).name}"
    except Exception as e:
        return None, f"Error generating PDF: {str(e)}"


def handle_generate_cover_letter(summary_text, spins_text, programmer_text, analyst_text,
                                   jd, job_title, company, info, job_change,
                                   company_hook, personal_alignment, credibility_anchor,
                                   include_gap, gap_text):
    """Generate cover letter from edited resume content and job details."""
    try:
        # Validate required inputs
        if not summary_text or not summary_text.strip():
            return {"error": "Please generate a resume first"}, ""

        if not job_title or not job_title.strip():
            return {"error": "Please enter a job title in the Generate tab"}, ""

        if not jd or not jd.strip():
            return {"error": "Job description is required"}, ""

        if not company or not company.strip():
            return {"error": "Company name is required"}, ""

        # Convert edit textboxes to bullet lists
        spins_list = text_to_bullets(spins_text)
        programmer_list = text_to_bullets(programmer_text)
        analyst_list = text_to_bullets(analyst_text)

        # Build resume_data dict
        resume_data = {
            "summary": summary_text,
            "spins": spins_list,
            "programmer": programmer_list,
            "analyst": analyst_list
        }

        # Build company_interest dict (pass None if all empty)
        company_interest = None
        if company_hook or personal_alignment or credibility_anchor:
            company_interest = {
                "hook": company_hook.strip() if company_hook else "",
                "alignment": personal_alignment.strip() if personal_alignment else "",
                "credibility_anchor": credibility_anchor.strip() if credibility_anchor else ""
            }

        # NEW: Prepare gap explanation (pass None if not included or empty)
        gap_explanation = None
        if include_gap and gap_text and gap_text.strip():
            gap_explanation = gap_text.strip()

        # Generate cover letter
        cover_letter_html = generate_cover_letter(
            resume_data, job_title, jd, company, info, job_change,
            company_interest,
            gap_explanation
        )

        # Return JSON output and HTML state
        return {
            "status": "success",
            "paragraphs": cover_letter_html.count("<p>"),
            "preview": cover_letter_html[:200] + "..."
        }, cover_letter_html

    except Exception as e:
        return {"error": str(e)}, ""


def handle_cover_letter_preview_update(cover_letter_html):
    """Update cover letter preview from state."""
    if not cover_letter_html:
        return "<p>No cover letter generated yet. Generate a cover letter first.</p>"

    try:
        # Load full HTML template with cover letter body
        html = load_cover_letter_html(cover_letter_html)
        return html
    except Exception as e:
        return f"<p>Error loading preview: {str(e)}</p>"


def handle_cover_letter_pdf_generation(cover_letter_html):
    """Generate PDF from cover letter HTML."""
    if not cover_letter_html:
        return None, "Please generate a cover letter first"

    try:
        # Load full HTML template
        html = load_cover_letter_html(cover_letter_html)

        # Generate PDF
        pdf_path = generate_cover_letter_pdf_file(html)
        return pdf_path, f"PDF generated successfully: {Path(pdf_path).name}"
    except Exception as e:
        return None, f"Error generating PDF: {str(e)}"


def handle_gap_role_change(gap_file_path):
    """Load gap explanation text when user changes gap role dropdown."""
    gap_text = load_gap_explanation(gap_file_path)
    return gap_text


def launch_app():
    with gr.Blocks() as demo:
        gr.Markdown("## Resume Forge")

        # State components
        state_summary = gr.State(value="")
        state_spins = gr.State(value=[])
        state_programmer = gr.State(value=[])
        state_analyst = gr.State(value=[])
        state_job_title = gr.State(value="")
        state_cover_letter_html = gr.State(value="")
        state_selected_bullet_file = gr.State(value="")

        # Tab 1: Generate
        with gr.Tab("Generate"):
            jd = gr.Textbox(label="Job Description", lines=10)
            job_title = gr.Textbox(label="Job Title")
            company = gr.Textbox(label="Company Name")
            info = gr.Textbox(label="Company Info", lines=5)
            bullet_file = gr.Dropdown(
                choices=list_bullet_files(),
                label="Select bullet list",
                value=None
            )
            job_change = gr.Checkbox(label="Customer-facing role")

            output = gr.JSON()

            run = gr.Button("Generate Resume")

        # Tab 2: Edit
        with gr.Tab("Edit"):
            edit_summary = gr.Textbox(label="Summary", lines=4, interactive=True)
            edit_spins = gr.Textbox(label="SPINS Bullets (one per line)", lines=12, interactive=True)
            edit_programmer = gr.Textbox(label="Programmer Bullets (one per line)", lines=12, interactive=True)
            edit_analyst = gr.Textbox(label="Analyst Bullets (one per line)", lines=12, interactive=True)

        # Tab 3: Preview & Export
        with gr.Tab("Preview & Export") as preview_tab:
            preview_html = gr.HTML(label="Resume Preview")
            generate_pdf_btn = gr.Button("Generate PDF")
            pdf_file_output = gr.File(label="Download PDF")
            status_message = gr.Textbox(label="Status", interactive=False)

        # Tab 4: Generate Cover Letter
        with gr.Tab("Generate Cover Letter"):
            gr.Markdown("""
            ### Cover Letter Generation

            Generates a cover letter based on:
            - Your **edited** resume content (from the Edit tab)
            - Job details entered in the Generate tab

            **Important:** Generate and edit your resume first before creating a cover letter.
            """)

            # NEW: Motivation Inputs Section
            gr.Markdown("### Optional: Company Interest & Motivation")
            gr.Markdown("Fill any or all fields below to add a motivation paragraph (Paragraph 2). Leave all empty for a standard 4-paragraph letter.")

            company_hook = gr.Textbox(
                label="Company Hook (one sentence)",
                placeholder="What caught your attention? (e.g., 'Your focus on real-time data infrastructure')",
                lines=2,
                interactive=True
            )

            personal_alignment = gr.Textbox(
                label="Personal Alignment (one sentence)",
                placeholder="How does that align with you? (e.g., 'aligns with my 5 years optimizing distributed systems')",
                lines=2,
                interactive=True
            )

            credibility_anchor = gr.Textbox(
                label="Credibility Anchor (concrete reference)",
                placeholder="Specific reference (e.g., 'your recent Series B funding to expand to healthcare')",
                lines=2,
                interactive=True
            )

            # NEW: Gap Explanation Section
            gr.Markdown("---")
            gr.Markdown("### Optional: Employment Gap Explanation")
            gr.Markdown("Include a paragraph addressing career transitions or employment gaps. Auto-loaded based on your selected role. Checked by default.")

            # Checkbox (default checked)
            include_gap = gr.Checkbox(
                label="Include gap explanation paragraph",
                value=True,
                interactive=True
            )

            # Dropdown (auto-populated from gap_libs/)
            gap_role_dropdown = gr.Dropdown(
                label="Select gap explanation role",
                choices=[],
                value=None,
                interactive=True
            )

            # Textbox (editable, loads from selected file)
            gap_text = gr.Textbox(
                label="Gap Explanation Paragraph (editable)",
                placeholder="Auto-loads when you select a role above. Edit freely—changes won't be saved to file.",
                lines=4,
                interactive=True,
                value=""
            )

            generate_cover_btn = gr.Button("Generate Cover Letter", variant="primary")
            cover_output = gr.JSON(label="Cover Letter Data")

        # Tab 5: Cover Letter Preview & Export
        with gr.Tab("Cover Letter Preview & Export") as cover_preview_tab:
            cover_preview_html = gr.HTML(label="Cover Letter Preview")
            generate_cover_pdf_btn = gr.Button("Generate PDF")
            cover_pdf_file_output = gr.File(label="Download Cover Letter PDF")
            cover_status_message = gr.Textbox(label="Status", interactive=False)

        # Event handlers
        run.click(
            fn=handle_generate,
            inputs=[jd, job_title, company, info, bullet_file, job_change],
            outputs=[
                output,              # Tab 1: JSON
                edit_summary,        # Tab 2
                edit_spins,          # Tab 2
                edit_programmer,     # Tab 2
                edit_analyst,        # Tab 2
                state_summary,       # State
                state_spins,         # State
                state_programmer,    # State
                state_analyst,       # State
                state_job_title,     # State
                state_selected_bullet_file  # NEW: State
            ]
        )

        # Auto-update preview when tab is selected
        preview_tab.select(
            fn=handle_preview_update,
            inputs=[edit_summary, edit_spins, edit_programmer, edit_analyst],
            outputs=preview_html
        )

        # Generate PDF
        generate_pdf_btn.click(
            fn=handle_pdf_generation,
            inputs=preview_html,
            outputs=[pdf_file_output, status_message]
        )

        # Generate cover letter
        generate_cover_btn.click(
            fn=handle_generate_cover_letter,
            inputs=[
                edit_summary, edit_spins, edit_programmer, edit_analyst,
                jd, state_job_title, company, info, job_change,
                company_hook, personal_alignment, credibility_anchor,
                include_gap, gap_text
            ],
            outputs=[cover_output, state_cover_letter_html]
        )

        # Auto-update cover letter preview when tab selected
        cover_preview_tab.select(
            fn=handle_cover_letter_preview_update,
            inputs=state_cover_letter_html,
            outputs=cover_preview_html
        )

        # Generate cover letter PDF
        generate_cover_pdf_btn.click(
            fn=handle_cover_letter_pdf_generation,
            inputs=state_cover_letter_html,
            outputs=[cover_pdf_file_output, cover_status_message]
        )

        # NEW: Auto-populate gap dropdown on app load
        demo.load(
            fn=lambda: gr.Dropdown(choices=list_gap_files()),
            outputs=gap_role_dropdown
        )

        # NEW: Auto-load gap explanation when bullet file selected (Tab 1 → Tab 4)
        bullet_file.change(
            fn=lambda bf: derive_gap_file_from_bullet_file(bf),
            inputs=bullet_file,
            outputs=gap_role_dropdown
        )

        # NEW: Load gap text when gap role dropdown changes
        gap_role_dropdown.change(
            fn=handle_gap_role_change,
            inputs=gap_role_dropdown,
            outputs=gap_text
        )

    demo.launch(theme=gr.themes.Soft())
