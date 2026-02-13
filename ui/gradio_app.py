import gradio as gr
from pathlib import Path
from ui.adapters import generate_resume_adapter, generate_cover_letter_adapter
from app.error_result import Success, Failure
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
from ui.bullet_editor_helpers import (
    load_bullet_library,
    save_bullet_library,
    create_new_bullet_library,
    count_bullets,
    get_validation_summary
)
from ui.ui_formatters import (
    format_removed_bullet_display,
    format_suggestion_choices,
    format_suggestion_explanation,
    format_skills_coverage_warning,
    format_replacement_success,
    create_error_response,
    sync_bullet_choices,
    create_hidden_ui_state,
    enrich_section_lists_with_ids,
    create_bullet_library_response
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


def handle_generate(jd, job_title, company, info, bullet_file, job_change, progress=gr.Progress()):
    """Generate resume and populate all tabs."""
    progress(0.0, desc="Starting generation...")

    if not bullet_file:
        error_status = gr.Markdown(value="❌ Please select a bullet file", visible=True)
        return {"error": "Please select a bullet file"}, "", "", "", "", "", [], [], [], "", "", [], {}, set(), "", [], gr.Radio(choices=[]), gr.Radio(choices=[]), gr.Radio(choices=[]), error_status

    # Call adapter (no try/except needed - adapter handles all exceptions)
    progress(0.2, desc="Calling resume engine...")
    result_obj = generate_resume_adapter(jd, company, info, bullet_file, job_change)

    # Check for failure
    if isinstance(result_obj, Failure):
        error_output = {"error": result_obj.error_message, "error_type": result_obj.error_type}
        error_status = gr.Markdown(value=f"❌ {result_obj.error_message}", visible=True)
        return error_output, "", "", "", "", "", [], [], [], "", "", [], {}, set(), "", [], gr.Radio(choices=[]), gr.Radio(choices=[]), gr.Radio(choices=[]), error_status

    # Extract result from Success
    progress(0.5, desc="Processing results...")
    result = result_obj.value

    # Extract section lists and intelligence metadata
    summary = result["summary"]
    spins_list = result["spins"]
    programmer_list = result["programmer"]
    analyst_list = result["analyst"]
    metadata = result.get("metadata", {})
    analyzed_bullets = metadata.get("analyzed_bullets", [])
    jd_analysis = metadata.get("jd_analysis", {})
    used_bullet_ids = metadata.get("used_bullet_ids", set())

    # Enhance section lists with IDs for tracking
    progress(0.7, desc="Building intelligence metadata...")
    spins_with_ids, programmer_with_ids, analyst_with_ids = enrich_section_lists_with_ids(
        spins_list, programmer_list, analyst_list, analyzed_bullets
    )

    # Convert to text for textboxes
    spins_text = bullets_to_text(spins_list)
    programmer_text = bullets_to_text(programmer_list)
    analyst_text = bullets_to_text(analyst_list)

    # Create canonical state (single source of truth)
    progress(0.9, desc="Creating canonical state...")
    from app.data_extractors import create_canonical_bullets
    canonical_bullets = create_canonical_bullets(spins_with_ids, programmer_with_ids, analyst_with_ids)

    # Create radio choices for bullet selection
    spins_radio_choices = sync_bullet_choices(spins_text)
    programmer_radio_choices = sync_bullet_choices(programmer_text)
    analyst_radio_choices = sync_bullet_choices(analyst_text)

    progress(1.0, desc="Complete!")
    success_status = gr.Markdown(value="✓ Resume generated successfully", visible=True)

    return (
        result,                # JSON output
        summary,               # Edit: summary textbox
        spins_text,           # Edit: spins textbox
        programmer_text,      # Edit: programmer textbox
        analyst_text,         # Edit: analyst textbox
        summary,               # State: summary
        spins_with_ids,        # State: spins (NOW includes IDs)
        programmer_with_ids,   # State: programmer (NOW includes IDs)
        analyst_with_ids,      # State: analyst (NOW includes IDs)
        job_title,            # State: job_title
        bullet_file,          # State: selected_bullet_file
        analyzed_bullets,      # State: analyzed_bullets
        jd_analysis,           # State: jd_analysis
        used_bullet_ids,       # State: used_bullet_ids
        jd,                    # State: job_description
        canonical_bullets,     # State: canonical_bullets
        gr.Radio(choices=spins_radio_choices, value=spins_radio_choices[0][1] if spins_radio_choices else None),  # spins_bullet_radio
        gr.Radio(choices=programmer_radio_choices, value=programmer_radio_choices[0][1] if programmer_radio_choices else None),  # programmer_bullet_radio
        gr.Radio(choices=analyst_radio_choices, value=analyst_radio_choices[0][1] if analyst_radio_choices else None),  # analyst_bullet_radio
        success_status         # generate_status
    )


def handle_preview_update(summary_text, state_canonical_bullets):
    """
    Update preview from canonical state (Phase 3B: one-way conversion).

    IMPORTANT: This function now uses canonical state instead of text to prevent
    intelligence data loss. Preview is always derived from the single source of truth.
    """
    from app.data_extractors import get_section_bullets, extract_bullet_texts

    # Derive section views from canonical state (model → view)
    spins = get_section_bullets(state_canonical_bullets, "spins")
    programmer = get_section_bullets(state_canonical_bullets, "programmer")
    analyst = get_section_bullets(state_canonical_bullets, "analyst")

    # Extract text for HTML generation
    spins_list = extract_bullet_texts(spins)
    programmer_list = extract_bullet_texts(programmer)
    analyst_list = extract_bullet_texts(analyst)

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
                                    include_gap, gap_text, jd_analysis, progress=gr.Progress()):
    """Generate cover letter from edited resume content and job details (Phase 1A: uses pre-analyzed JD)."""
    progress(0.0, desc="Starting cover letter generation...")

    # Validate required inputs (UI-level validation)
    if not summary_text or not summary_text.strip():
        error_status = gr.Markdown(value="❌ Please generate a resume first", visible=True)
        return {"error": "Please generate a resume first"}, "", error_status

    if not job_title or not job_title.strip():
        error_status = gr.Markdown(value="❌ Please enter a job title in the Generate tab", visible=True)
        return {"error": "Please enter a job title in the Generate tab"}, "", error_status

    if not jd or not jd.strip():
        error_status = gr.Markdown(value="❌ Job description is required", visible=True)
        return {"error": "Job description is required"}, "", error_status

    if not company or not company.strip():
        error_status = gr.Markdown(value="❌ Company name is required", visible=True)
        return {"error": "Company name is required"}, "", error_status

    # Convert edit textboxes to bullet lists
    progress(0.2, desc="Processing resume data...")
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

    # Call adapter (no try/except needed - adapter handles all exceptions)
    progress(0.4, desc="Calling cover letter engine...")
    result_obj = generate_cover_letter_adapter(
        resume_data, job_title, jd, company, info, job_change,
        company_interest,
        gap_explanation,
        jd_analysis  # Phase 1A: Pass pre-analyzed JD intelligence to eliminate redundant analysis
    )

    # Check for failure
    if isinstance(result_obj, Failure):
        error_output = {"error": result_obj.error_message, "error_type": result_obj.error_type}
        error_status = gr.Markdown(value=f"❌ {result_obj.error_message}", visible=True)
        return error_output, "", error_status

    # Extract cover letter HTML from Success
    progress(0.8, desc="Formatting cover letter...")
    cover_letter_html = result_obj.value

    progress(1.0, desc="Complete!")
    success_status = gr.Markdown(value="✓ Cover letter generated successfully", visible=True)

    # Return JSON output and HTML state
    return {
        "status": "success",
        "paragraphs": cover_letter_html.count("<p>"),
        "preview": cover_letter_html[:200] + "..."
    }, cover_letter_html, success_status


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


def handle_load_bullet_library(file_path):
    """Load bullet library from file."""
    if not file_path:
        return create_bullet_library_response(False, status="Please select a file")

    role, bullets_text, status = load_bullet_library(file_path)

    if not role:  # Error occurred
        return create_bullet_library_response(False, status=status)

    # Success - get metadata and create response
    bullet_count = count_bullets(bullets_text)
    validation = get_validation_summary(bullets_text)

    return create_bullet_library_response(
        True,
        role=role,
        bullets_text=bullets_text,
        status=status,
        file_path=file_path,
        bullet_count=bullet_count,
        validation=validation
    )


def handle_create_new_library(role_name):
    """Create new bullet library file."""
    if not role_name or not role_name.strip():
        return (
            gr.update(),  # role_editor
            gr.update(),  # bullets_editor
            gr.update(visible=False),  # editor_group
            "Please enter a role name",  # editor_status
            "",  # current_bullet_file_path
            "",  # original_role
            "",  # original_bullets_text
            "0 bullets",  # bullet_count_display
            "Ready",  # validation_display
            gr.update()  # new_role_name (don't clear on error)
        )

    success, file_path, status = create_new_bullet_library(role_name)

    if not success:
        return (
            gr.update(),  # role_editor
            gr.update(),  # bullets_editor
            gr.update(visible=False),  # editor_group
            status,  # editor_status
            "",  # current_bullet_file_path
            "",  # original_role
            "",  # original_bullets_text
            "0 bullets",  # bullet_count_display
            "Ready",  # validation_display
            gr.update()  # new_role_name (don't clear on error)
        )

    # Success - show editor with empty bullets
    return (
        gr.update(value=role_name.strip()),  # role_editor
        gr.update(value=""),  # bullets_editor (empty)
        gr.update(visible=True),  # editor_group
        status,  # editor_status
        file_path,  # current_bullet_file_path
        role_name.strip(),  # original_role
        "",  # original_bullets_text (empty)
        "0 bullets",  # bullet_count_display
        "✓ All bullets valid",  # validation_display
        gr.update(value="")  # new_role_name (clear on success)
    )


def handle_save_bullet_library(file_path, role, bullets_text):
    """Save bullet library to file."""
    if not file_path:
        return (
            "Error: No file loaded",  # editor_status
            gr.update(),  # original_role
            gr.update(),  # original_bullets_text
            gr.update()  # bullet_lib_dropdown
        )

    success, status = save_bullet_library(file_path, role, bullets_text)

    if success:
        # Update original states (new baseline)
        return (
            status,  # editor_status
            role,  # original_role (new baseline)
            bullets_text,  # original_bullets_text (new baseline)
            gr.update(choices=list_bullet_files())  # refresh dropdown
        )
    else:
        return (
            status,  # editor_status
            gr.update(),  # original_role (no change)
            gr.update(),  # original_bullets_text (no change)
            gr.update()  # bullet_lib_dropdown (no change)
        )


def handle_discard_changes(original_role, original_bullets_text):
    """Discard changes and restore original values."""
    bullet_count = count_bullets(original_bullets_text)
    validation = get_validation_summary(original_bullets_text)

    return (
        gr.update(value=original_role),  # role_editor
        gr.update(value=original_bullets_text),  # bullets_editor
        f"{bullet_count} bullets",  # bullet_count_display
        validation,  # validation_display
        "Changes discarded"  # editor_status
    )


def handle_refresh_from_file(file_path):
    """Reload bullet library from file, discarding unsaved changes."""
    if not file_path:
        return (
            gr.update(),  # role_editor
            gr.update(),  # bullets_editor
            "0 bullets",  # bullet_count_display
            "Ready",  # validation_display
            "Error: No file loaded",  # editor_status
            "",  # original_role
            ""  # original_bullets_text
        )

    role, bullets_text, status = load_bullet_library(file_path)

    if not role:  # Error occurred
        return (
            gr.update(),  # role_editor
            gr.update(),  # bullets_editor
            "0 bullets",  # bullet_count_display
            "Ready",  # validation_display
            status,  # editor_status
            "",  # original_role
            ""  # original_bullets_text
        )

    # Success
    bullet_count = count_bullets(bullets_text)
    validation = get_validation_summary(bullets_text)

    return (
        gr.update(value=role),  # role_editor
        gr.update(value=bullets_text),  # bullets_editor
        f"{bullet_count} bullets",  # bullet_count_display
        validation,  # validation_display
        status,  # editor_status
        role,  # original_role (update baseline)
        bullets_text  # original_bullets_text (update baseline)
    )


def handle_bullets_change(bullets_text):
    """Update displays when bullets text changes."""
    bullet_count = count_bullets(bullets_text)
    validation = get_validation_summary(bullets_text)

    return (
        f"{bullet_count} bullets",  # bullet_count_display
        validation  # validation_display
    )


# ===== INTELLIGENT REPLACEMENT EVENT HANDLERS =====

def handle_get_suggestions(
    section_name: str,
    bullet_index: int,
    spins_list: list,
    programmer_list: list,
    analyst_list: list,
    analyzed_bullets: list,
    jd_analysis: dict,
    used_bullet_ids: set
):
    """
    Generate intelligent replacement suggestions (UI handler).

    Returns:
        Tuple of UI component updates
    """
    from app.replacement_engine import get_replacement_suggestions
    from app.exceptions import ValidationError

    # Call business logic
    try:
        result = get_replacement_suggestions(
            section_name, bullet_index,
            spins_list, programmer_list, analyst_list,
            analyzed_bullets, jd_analysis, used_bullet_ids
        )
    except ValidationError as e:
        return (
            gr.Markdown(value="", visible=False),
            gr.Radio(choices=[], visible=False),
            gr.Markdown(value="", visible=False),
            gr.Markdown(value="", visible=False),
            "",
            0,
            {},
            gr.Button(visible=False),
            gr.Button(visible=False),
            gr.Markdown(value=f"❌ {str(e)}", visible=True)
        )

    # Format UI components using helpers
    removed_display = format_removed_bullet_display(result["removed_bullet"], bullet_index)
    choices = format_suggestion_choices(result["suggestions"])

    # Format first suggestion explanation
    first_explanation = ""
    if result["suggestions"]:
        first_explanation = format_suggestion_explanation(result["suggestions"][0])

    # Format skills coverage warning if present
    coverage_warning = None
    if result.get("skills_coverage_warning"):
        # Extract overlap info from warning message (parsing existing format)
        warning_msg = result["skills_coverage_warning"]
        coverage_warning = gr.Markdown(value=f"⚠️ **Skills Coverage Warning**\n{warning_msg}", visible=True)

    return (
        gr.Markdown(value=removed_display, visible=True),
        gr.Radio(choices=choices, value=choices[0][1] if choices else None, visible=True),
        gr.Markdown(value=first_explanation, visible=True),
        coverage_warning if coverage_warning else gr.Markdown(value="", visible=False),
        result["target_section"],
        result["target_index"],
        result["removed_bullet"],
        gr.Button(visible=True),
        gr.Button(visible=True),
        gr.Markdown(value="", visible=False)
    )


def handle_suggestion_selected(
    selected_bullet_id: str,
    analyzed_bullets: list,
    jd_analysis: dict
):
    """Update explanation when user selects a different suggestion (UI handler)."""
    from app.replacement_engine import get_suggestion_explanation

    # Call business logic
    result = get_suggestion_explanation(selected_bullet_id, analyzed_bullets, jd_analysis)

    if not result["success"]:
        return ""

    # Format explanation for UI
    selected = result["bullet"]
    explanation = f"""#### Why This Suggestion?
{result['explanation']}

**Details:**
- **Category:** {selected['category']}
- **Keywords:** {', '.join(selected['keywords'][:5])}
- **Has Impact:** {'✓ Yes' if selected['has_impact'] else '✗ No'}
- **JD Score:** {selected['jd_score']}
"""
    return explanation


def handle_confirm_replacement(
    target_section: str,
    target_index: int,
    selected_bullet_id: str,
    spins_list: list,
    programmer_list: list,
    analyst_list: list,
    analyzed_bullets: list,
    used_bullet_ids: set
):
    """
    Execute the intelligent bullet replacement (UI handler).

    Returns updated state and UI elements.
    """
    from app.replacement_engine import execute_replacement
    from app.exceptions import ValidationError
    from app.data_extractors import create_canonical_bullets

    # Call business logic
    try:
        result = execute_replacement(
            target_section, target_index, selected_bullet_id,
            spins_list, programmer_list, analyst_list,
            analyzed_bullets, used_bullet_ids
        )
    except ValidationError as e:
        return create_error_response(f"Error: {str(e)}", 14)

    # Format success message using helper
    success_msg = format_replacement_success(
        target_section,
        target_index,
        result["replacement_bullet"]
    )

    # Update canonical state after replacement
    updated_canonical = create_canonical_bullets(
        result["updated_spins"],
        result["updated_programmer"],
        result["updated_analyst"]
    )

    return (
        gr.Markdown(value=success_msg, visible=True),
        result["spins_text"],
        result["programmer_text"],
        result["analyst_text"],
        result["updated_spins"],
        result["updated_programmer"],
        result["updated_analyst"],
        result["updated_used_ids"],
        gr.Markdown(value="", visible=False),
        gr.Radio(choices=[], visible=False),
        gr.Markdown(value="", visible=False),
        gr.Markdown(value="", visible=False),
        gr.Button(visible=False),
        gr.Button(visible=False),
        updated_canonical
    )


def handle_cancel_replacement():
    """Cancel replacement and hide suggestions panel."""
    return (
        gr.Markdown(value="", visible=False),
        gr.Radio(choices=[], visible=False),
        gr.Markdown(value="", visible=False),
        gr.Markdown(value="", visible=False),
        gr.Button(visible=False),
        gr.Button(visible=False),
        gr.Markdown(value="", visible=False)
    )


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

        # NEW states for intelligent replacement
        state_analyzed_bullets = gr.State(value=[])       # All bullet intelligence
        state_jd_analysis = gr.State(value={})            # JD keywords/skills
        state_used_bullet_ids = gr.State(value=set())     # Track which bullets are active
        state_job_description = gr.State(value="")        # Preserve for suggestions

        # Phase 3: Canonical state (single source of truth for section bullets)
        state_canonical_bullets = gr.State(value=[])      # All section bullets with "section" field

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
            generate_status = gr.Markdown(value="", visible=False)

        # Tab 2: Edit
        with gr.Tab("Edit"):
            gr.Markdown("### Review and Edit Generated Content")

            with gr.Row():
                # Left column: Existing edit textboxes
                with gr.Column(scale=2):
                    edit_summary = gr.Textbox(
                        label="Professional Summary",
                        lines=4,
                        interactive=True
                    )

                    with gr.Accordion("SPINS Bullets (End-User Interaction)", open=True):
                        edit_spins = gr.Textbox(
                            label="Edit bullets (one per line)",
                            lines=12,
                            interactive=True
                        )
                        gr.Markdown("**Select bullet to replace:**")
                        spins_bullet_radio = gr.Radio(
                            label="",
                            choices=[],
                            value=None,
                            interactive=True
                        )
                        open_replacement_spins = gr.Button("Get Suggestions for Selected Bullet", size="sm", variant="primary")
                        spins_suggestion_status = gr.Markdown(value="", visible=False)

                    with gr.Accordion("Programmer Bullets (Technical Implementation)", open=True):
                        edit_programmer = gr.Textbox(
                            label="Edit bullets (one per line)",
                            lines=12,
                            interactive=True
                        )
                        gr.Markdown("**Select bullet to replace:**")
                        programmer_bullet_radio = gr.Radio(
                            label="",
                            choices=[],
                            value=None,
                            interactive=True
                        )
                        open_replacement_programmer = gr.Button("Get Suggestions for Selected Bullet", size="sm", variant="primary")
                        programmer_suggestion_status = gr.Markdown(value="", visible=False)

                    with gr.Accordion("Analyst Bullets (Analysis & Documentation)", open=True):
                        edit_analyst = gr.Textbox(
                            label="Edit bullets (one per line)",
                            lines=12,
                            interactive=True
                        )
                        gr.Markdown("**Select bullet to replace:**")
                        analyst_bullet_radio = gr.Radio(
                            label="",
                            choices=[],
                            value=None,
                            interactive=True
                        )
                        open_replacement_analyst = gr.Button("Get Suggestions for Selected Bullet", size="sm", variant="primary")
                        analyst_suggestion_status = gr.Markdown(value="", visible=False)

                # Right column: Intelligent Suggestions Panel (NEW)
                with gr.Column(scale=1) as suggestions_panel:
                    gr.Markdown("### 🎯 Smart Replacement Suggestions")
                    gr.Markdown("*AI-ranked suggestions based on skills, category, and job fit*")

                    # Display removed bullet context
                    removed_bullet_display = gr.Markdown(
                        value="",
                        visible=False,
                        label="Replacing:"
                    )

                    # Top 5 suggestions with explanations
                    suggestions_radio = gr.Radio(
                        choices=[],
                        label="Top 5 Recommended Replacements",
                        interactive=True,
                        visible=False
                    )

                    # Show detailed explanation for selected suggestion
                    suggestion_explanation = gr.Markdown(
                        value="",
                        visible=False
                    )

                    # Skills coverage warning
                    coverage_warning = gr.Markdown(
                        value="",
                        visible=False
                    )

                    # Active replacement tracking (state)
                    replacement_target_section = gr.State(value="")
                    replacement_target_index = gr.State(value=0)
                    replacement_removed_bullet = gr.State(value={})

                    # Action buttons
                    with gr.Row():
                        confirm_replace_btn = gr.Button(
                            "✓ Confirm Replacement",
                            variant="primary",
                            visible=False
                        )
                        cancel_replace_btn = gr.Button(
                            "✗ Cancel",
                            visible=False
                        )

                    # Status/feedback
                    replacement_status = gr.Markdown(
                        value="",
                        visible=False
                    )

        # Tab 3: Bullet Library Editor
        with gr.Tab("Bullet Library Editor"):
            gr.Markdown("### Edit Bullet Libraries\nManage bullet library files (bullet_libs/*.json)")

            # File Selection Section
            with gr.Row():
                bullet_lib_dropdown = gr.Dropdown(
                    label="Select Bullet Library File",
                    choices=list_bullet_files(),
                    value=None
                )
                load_file_btn = gr.Button("Load File")

            gr.Markdown("---\n**OR create a new bullet library:**")

            with gr.Row():
                new_role_name = gr.Textbox(
                    label="New Role Name",
                    placeholder="e.g., Software Developer, Help Desk"
                )
                create_new_btn = gr.Button("Create New Library", variant="secondary")

            gr.Markdown("---")

            # Editor Section (hidden until file loaded/created)
            with gr.Group(visible=False) as editor_group:
                role_editor = gr.Textbox(label="Role Name", lines=1)

                bullets_editor = gr.Textbox(
                    label="Bullets (one per line)",
                    lines=25,
                    max_lines=100,
                    info="Enter one bullet per line. No periods at end."
                )

                with gr.Row():
                    bullet_count_display = gr.Label(label="\nBullet Count", value="0 bullets")
                    validation_display = gr.Label(label="Text Validation", value="Ready")

                with gr.Row():
                    save_btn = gr.Button("Save Changes", variant="primary")
                    discard_btn = gr.Button("Discard Changes", variant="secondary")
                    refresh_btn = gr.Button("Refresh from File", variant="secondary")

            editor_status = gr.Textbox(label="Status", interactive=False, lines=2)

            # Hidden state variables
            current_bullet_file_path = gr.State(value="")
            original_role = gr.State(value="")
            original_bullets_text = gr.State(value="")

        # Tab 4: Preview & Export (Resume)
        with gr.Tab("Preview & Export") as preview_tab:
            preview_html = gr.HTML(label="Resume Preview")
            generate_pdf_btn = gr.Button("Generate PDF")
            pdf_file_output = gr.File(label="Download PDF")
            status_message = gr.Textbox(label="Status", interactive=False)

        # Tab 5: Generate Cover Letter
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
            cover_generation_status = gr.Markdown(value="", visible=False)
            cover_output = gr.JSON(label="Cover Letter Data")

        # Tab 6: Cover Letter Preview & Export
        with gr.Tab("Cover Letter Preview & Export") as cover_preview_tab:
            cover_preview_html = gr.HTML(label="Cover Letter Preview")
            generate_cover_pdf_btn = gr.Button("Generate PDF")
            cover_pdf_file_output = gr.File(label="Download Cover Letter PDF")
            cover_status_message = gr.Textbox(label="Status", interactive=False)

        # Event handlers (Tab 1: Generate)
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
                state_spins,         # State (NOW includes intelligence)
                state_programmer,    # State (NOW includes intelligence)
                state_analyst,       # State (NOW includes intelligence)
                state_job_title,     # State
                state_selected_bullet_file,  # State
                state_analyzed_bullets,      # NEW: Full intelligence per bullet
                state_jd_analysis,           # NEW: JD keywords/skills
                state_used_bullet_ids,       # NEW: Track active bullets
                state_job_description,       # NEW: Preserve JD for suggestions
                state_canonical_bullets,     # Phase 3: Canonical state (single source of truth)
                spins_bullet_radio,          # Radio: SPINS bullet selection
                programmer_bullet_radio,     # Radio: Programmer bullet selection
                analyst_bullet_radio,        # Radio: Analyst bullet selection
                generate_status              # Status: Generation status message
            ]
        )

        # Event handlers (Tab 3: Bullet Library Editor)
        load_file_btn.click(
            fn=handle_load_bullet_library,
            inputs=bullet_lib_dropdown,
            outputs=[role_editor, bullets_editor, editor_group, editor_status,
                    current_bullet_file_path, original_role, original_bullets_text,
                    bullet_count_display, validation_display]
        )

        create_new_btn.click(
            fn=handle_create_new_library,
            inputs=new_role_name,
            outputs=[role_editor, bullets_editor, editor_group, editor_status,
                    current_bullet_file_path, original_role, original_bullets_text,
                    bullet_count_display, validation_display, new_role_name]
        )

        save_btn.click(
            fn=handle_save_bullet_library,
            inputs=[current_bullet_file_path, role_editor, bullets_editor],
            outputs=[editor_status, original_role, original_bullets_text, bullet_lib_dropdown]
        )

        discard_btn.click(
            fn=handle_discard_changes,
            inputs=[original_role, original_bullets_text],
            outputs=[role_editor, bullets_editor, bullet_count_display,
                    validation_display, editor_status]
        )

        refresh_btn.click(
            fn=handle_refresh_from_file,
            inputs=current_bullet_file_path,
            outputs=[role_editor, bullets_editor, bullet_count_display,
                    validation_display, editor_status, original_role, original_bullets_text]
        )

        bullets_editor.change(
            fn=handle_bullets_change,
            inputs=bullets_editor,
            outputs=[bullet_count_display, validation_display]
        )

        # Event handlers (Tab 4: Preview & Export)
        # Auto-update preview when tab is selected (Phase 3B: uses canonical state)
        preview_tab.select(
            fn=handle_preview_update,
            inputs=[state_summary, state_canonical_bullets],
            outputs=preview_html
        )

        # Generate PDF
        generate_pdf_btn.click(
            fn=handle_pdf_generation,
            inputs=preview_html,
            outputs=[pdf_file_output, status_message]
        )

        # Generate cover letter (Phase 1A: now passes pre-analyzed JD)
        generate_cover_btn.click(
            fn=handle_generate_cover_letter,
            inputs=[
                edit_summary, edit_spins, edit_programmer, edit_analyst,
                jd, state_job_title, company, info, job_change,
                company_hook, personal_alignment, credibility_anchor,
                include_gap, gap_text, state_jd_analysis
            ],
            outputs=[cover_output, state_cover_letter_html, cover_generation_status]
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

        # ===== INTELLIGENT REPLACEMENT EVENT HANDLERS =====

        # SPINS section - Get suggestions
        open_replacement_spins.click(
            fn=handle_get_suggestions,
            inputs=[
                gr.State(value="SPINS"),
                spins_bullet_radio,
                state_spins,
                state_programmer,
                state_analyst,
                state_analyzed_bullets,
                state_jd_analysis,
                state_used_bullet_ids
            ],
            outputs=[
                removed_bullet_display,
                suggestions_radio,
                suggestion_explanation,
                coverage_warning,
                replacement_target_section,
                replacement_target_index,
                replacement_removed_bullet,
                confirm_replace_btn,
                cancel_replace_btn,
                replacement_status
            ]
        )

        # Programmer section - Get suggestions
        open_replacement_programmer.click(
            fn=handle_get_suggestions,
            inputs=[
                gr.State(value="Programmer"),
                programmer_bullet_radio,
                state_spins,
                state_programmer,
                state_analyst,
                state_analyzed_bullets,
                state_jd_analysis,
                state_used_bullet_ids
            ],
            outputs=[
                removed_bullet_display,
                suggestions_radio,
                suggestion_explanation,
                coverage_warning,
                replacement_target_section,
                replacement_target_index,
                replacement_removed_bullet,
                confirm_replace_btn,
                cancel_replace_btn,
                replacement_status
            ]
        )

        # Analyst section - Get suggestions
        open_replacement_analyst.click(
            fn=handle_get_suggestions,
            inputs=[
                gr.State(value="Analyst"),
                analyst_bullet_radio,
                state_spins,
                state_programmer,
                state_analyst,
                state_analyzed_bullets,
                state_jd_analysis,
                state_used_bullet_ids
            ],
            outputs=[
                removed_bullet_display,
                suggestions_radio,
                suggestion_explanation,
                coverage_warning,
                replacement_target_section,
                replacement_target_index,
                replacement_removed_bullet,
                confirm_replace_btn,
                cancel_replace_btn,
                replacement_status
            ]
        )

        # Update explanation when selection changes
        suggestions_radio.change(
            fn=handle_suggestion_selected,
            inputs=[suggestions_radio, state_analyzed_bullets, state_jd_analysis],
            outputs=[suggestion_explanation]
        )

        # Confirm replacement
        confirm_replace_btn.click(
            fn=handle_confirm_replacement,
            inputs=[
                replacement_target_section,
                replacement_target_index,
                suggestions_radio,
                state_spins,
                state_programmer,
                state_analyst,
                state_analyzed_bullets,
                state_used_bullet_ids
            ],
            outputs=[
                replacement_status,
                edit_spins,
                edit_programmer,
                edit_analyst,
                state_spins,
                state_programmer,
                state_analyst,
                state_used_bullet_ids,
                removed_bullet_display,
                suggestions_radio,
                suggestion_explanation,
                coverage_warning,
                confirm_replace_btn,
                cancel_replace_btn,
                state_canonical_bullets  # Phase 3: Update canonical state on replacement
            ]
        )

        # Cancel replacement
        cancel_replace_btn.click(
            fn=handle_cancel_replacement,
            outputs=[
                removed_bullet_display,
                suggestions_radio,
                suggestion_explanation,
                coverage_warning,
                confirm_replace_btn,
                cancel_replace_btn,
                replacement_status
            ]
        )

        # Sync radio choices when bullets are edited (Phase 2: Radio Selection)
        edit_spins.change(
            fn=lambda text: gr.Radio(choices=sync_bullet_choices(text), value=sync_bullet_choices(text)[0][1] if sync_bullet_choices(text) else None),
            inputs=[edit_spins],
            outputs=[spins_bullet_radio]
        )

        edit_programmer.change(
            fn=lambda text: gr.Radio(choices=sync_bullet_choices(text), value=sync_bullet_choices(text)[0][1] if sync_bullet_choices(text) else None),
            inputs=[edit_programmer],
            outputs=[programmer_bullet_radio]
        )

        edit_analyst.change(
            fn=lambda text: gr.Radio(choices=sync_bullet_choices(text), value=sync_bullet_choices(text)[0][1] if sync_bullet_choices(text) else None),
            inputs=[edit_analyst],
            outputs=[analyst_bullet_radio]
        )

    demo.launch(theme=gr.themes.Soft())


if __name__ == "__main__":
    launch_app()
