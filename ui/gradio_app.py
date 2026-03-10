import gradio as gr
from datetime import date
from pathlib import Path
from ui.adapters import generate_resume_adapter, generate_cover_letter_adapter
from app.error_result import Success, Failure
from app.job_tracker import (
    init_db,
    save_application,
    update_rejection,
    update_interview,
    update_pdf_paths,
    list_applications,
)
from app.application_archive import archive_pdfs
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
    derive_gap_file_from_bullet_file,
    cover_letter_html_to_text,
    cover_letter_text_to_html,
)
from ui.bullet_editor_helpers import (
    load_bullet_library,
    save_bullet_library,
    create_new_bullet_library,
    rows_to_section_summary,
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


def _get_default_tools_text() -> str:
    """Return default tools_and_environments bullets as newline-joined string."""
    import json
    from pathlib import Path
    config_path = Path(__file__).parent.parent / "config" / "technical_skills.json"
    try:
        with open(config_path, 'r') as f:
            config = json.load(f)
        bullets = config["sections"]["tools_and_environments"]["bullets"]
        return "\n".join(bullets)
    except Exception:
        return "Git, GitHub\nJira, Confluence, Notion\nVisual Studio"

# Section column header derived from VALID_SECTIONS — updates automatically if sections are added
from app.bullet_library_manager import VALID_SECTIONS as _VALID_SECTIONS
_SECTION_HEADER = "Section (" + "/".join(sorted(_VALID_SECTIONS)) + ")"


def _validate_rows_summary(rows: list) -> str:
    """Return validation display string for Dataframe rows (UI helper)."""
    safe = rows or []
    if not safe:
        return "Ready"
    errors = sum(
        1 for r in safe
        if not (isinstance(r, (list, tuple)) and len(r) >= 2
                and str(r[0]).strip()
                and str(r[1]).strip().lower() in _VALID_SECTIONS)
    )
    if errors == 0:
        return f"All {len(safe)} bullets valid"
    return f"{errors} row(s) have invalid/missing section — valid: {', '.join(sorted(_VALID_SECTIONS))}"

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
        return {"error": "Please select a bullet file"}, "", "", "", "", "", [], [], [], "", "", [], {}, set(), "", [], "General", gr.Radio(choices=[]), gr.Radio(choices=[]), gr.Radio(choices=[]), error_status, "", _get_default_tools_text()

    # Call adapter (no try/except needed - adapter handles all exceptions)
    progress(0.2, desc="Calling resume engine...")
    result_obj = generate_resume_adapter(jd, job_title, company, info, bullet_file, job_change)

    # Check for failure
    if isinstance(result_obj, Failure):
        error_output = {"error": result_obj.error_message, "error_type": result_obj.error_type}
        error_status = gr.Markdown(value=f"❌ {result_obj.error_message}", visible=True)
        return error_output, "", "", "", "", "", [], [], [], "", "", [], {}, set(), "", [], "General", gr.Radio(choices=[]), gr.Radio(choices=[]), gr.Radio(choices=[]), error_status, "", _get_default_tools_text()

    # Extract result from Success
    progress(0.5, desc="Processing results...")
    result = result_obj.value

    # Extract section lists and intelligence metadata
    summary = result["summary"]
    spins_list = result["spins"]
    programmer_list = result["programmer"]
    analyst_list = result["analyst"]
    role = result.get("role", "General")
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
        role,                  # State: role
        gr.Radio(choices=spins_radio_choices, value=spins_radio_choices[0][1] if spins_radio_choices else None),  # spins_bullet_radio
        gr.Radio(choices=programmer_radio_choices, value=programmer_radio_choices[0][1] if programmer_radio_choices else None),  # programmer_bullet_radio
        gr.Radio(choices=analyst_radio_choices, value=analyst_radio_choices[0][1] if analyst_radio_choices else None),  # analyst_bullet_radio
        success_status,        # generate_status
        company,               # State: company_name
        _get_default_tools_text(),  # edit_tools
    )


def handle_preview_update(summary_text, state_canonical_bullets, role: str = "General", tools_text: str = ""):
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

    # Convert tools text to list (filter empty lines)
    tools_list = [l.strip() for l in tools_text.splitlines() if l.strip()]

    # Load template and substitute
    html = load_resume_html(summary_text, spins_html, programmer_html, analyst_html, role=role,
                            tools_override=tools_list or None)

    return html


def handle_pdf_generation(html_content):
    """Generate PDF from current preview."""
    try:
        pdf_path = generate_pdf_file(html_content)
        return pdf_path, f"PDF generated successfully: {Path(pdf_path).name}", pdf_path
    except Exception as e:
        return None, f"Error generating PDF: {str(e)}", None


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


def handle_cover_letter_tab_select(cover_letter_html):
    """Populate edit box and HTML preview when Tab 6 is selected."""
    if not cover_letter_html:
        placeholder = "<p>No cover letter generated yet. Generate a cover letter first.</p>"
        return "", placeholder
    text = cover_letter_html_to_text(cover_letter_html)
    full_html = load_cover_letter_html(cover_letter_html)
    return text, full_html


def handle_update_cover_preview(edited_text):
    """Convert edited text back to HTML body, update state and preview."""
    html_body = cover_letter_text_to_html(edited_text)
    full_html = load_cover_letter_html(html_body)
    return html_body, full_html  # → state_cover_letter_html, cover_preview_html


def handle_cover_letter_pdf_generation(cover_letter_html):
    """Generate PDF from cover letter HTML."""
    if not cover_letter_html:
        return None, "Please generate a cover letter first", None

    try:
        # Load full HTML template
        html = load_cover_letter_html(cover_letter_html)

        # Generate PDF
        pdf_path = generate_cover_letter_pdf_file(html)
        return pdf_path, f"PDF generated successfully: {Path(pdf_path).name}", pdf_path
    except Exception as e:
        return None, f"Error generating PDF: {str(e)}", None


def handle_gap_role_change(gap_file_path):
    """Load gap explanation text when user changes gap role dropdown."""
    gap_text = load_gap_explanation(gap_file_path)
    return gap_text


def handle_load_bullet_library(file_path):
    """Load bullet library from file."""
    if not file_path:
        return create_bullet_library_response(False, status="Please select a file")
    role, rows, status = load_bullet_library(file_path)
    if not role:
        return create_bullet_library_response(False, status=status)
    return create_bullet_library_response(
        True, role=role, rows=rows, status=status, file_path=file_path,
        validation=_validate_rows_summary(rows)
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
            [],  # original_bullets_text
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
            [],  # original_bullets_text
            "0 bullets",  # bullet_count_display
            "Ready",  # validation_display
            gr.update()  # new_role_name (don't clear on error)
        )

    # Success - show editor with empty bullets
    return (
        gr.update(value=role_name.strip()),  # role_editor
        gr.update(value=[]),  # bullets_editor (empty)
        gr.update(visible=True),  # editor_group
        status,  # editor_status
        file_path,  # current_bullet_file_path
        role_name.strip(),  # original_role
        [],  # original_bullets_text (empty)
        "0 bullets",  # bullet_count_display
        "Ready",  # validation_display
        gr.update(value="")  # new_role_name (clear on success)
    )


def handle_save_bullet_library(file_path, role, bullets_editor_value):
    """Save bullet library to file."""
    if not file_path:
        return ("Error: No file loaded", gr.update(), gr.update(), gr.update())
    success, status = save_bullet_library(file_path, role, bullets_editor_value)
    if success:
        return (status, role, bullets_editor_value, gr.update(choices=list_bullet_files()))
    return (status, gr.update(), gr.update(), gr.update())


def handle_discard_changes(original_role, original_bullets_text):
    """Discard changes and restore original values."""
    safe = original_bullets_text if original_bullets_text else []
    return (
        gr.update(value=original_role),
        gr.update(value=safe),
        rows_to_section_summary(safe),
        _validate_rows_summary(safe),
        "Changes discarded"
    )


def handle_refresh_from_file(file_path):
    """Reload bullet library from file, discarding unsaved changes."""
    if not file_path:
        return (gr.update(), gr.update(), "0 bullets", "Ready",
                "Error: No file loaded", "", [])
    role, rows, status = load_bullet_library(file_path)
    if not role:
        return (gr.update(), gr.update(), "0 bullets", "Ready", status, "", [])
    return (
        gr.update(value=role), gr.update(value=rows),
        rows_to_section_summary(rows), _validate_rows_summary(rows),
        status, role, rows
    )


def handle_bullets_change(bullets_editor_value):
    """Update displays when bullets dataframe changes."""
    safe = bullets_editor_value or []
    return rows_to_section_summary(safe), _validate_rows_summary(safe)


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


def _applications_to_dataframe_rows(apps: list[dict]) -> list[list]:
    rows = []
    for app in apps:
        rows.append([
            app["id"],
            app["applied_date"],
            app["company_name"],
            app["job_title"],
            app["status"],
            app["days_pending"],
            app.get("notes", "") or "",
        ])
    return rows


def handle_tracker_tab_select(company_name, job_title, job_description, resume_pdf_path, cover_letter_pdf_path):
    """Pre-fill the save form and load the applications dataframe."""
    today = date.today().strftime("%m-%d-%Y")
    apps = list_applications()
    rows = _applications_to_dataframe_rows(apps)
    return (
        today,
        company_name or "",
        job_title or "",
        job_description or "",
        resume_pdf_path or "",
        cover_letter_pdf_path or "",
        rows,
    )


def handle_save_application(applied_date, company_name, job_title, job_description, notes, resume_pdf_path, cover_letter_pdf_path):
    """Archive PDFs, insert DB row, refresh dataframe."""
    if not company_name or not company_name.strip():
        return "❌ Company name is required", gr.update()
    if not job_title or not job_title.strip():
        return "❌ Job title is required", gr.update()
    if not applied_date or not applied_date.strip():
        return "❌ Applied date is required", gr.update()

    app_id = save_application(
        applied_date=applied_date.strip(),
        company_name=company_name.strip(),
        job_title=job_title.strip(),
        job_description=job_description or None,
        notes=notes or None,
    )

    resume_archive, cover_archive = archive_pdfs(
        app_id, company_name, job_title, resume_pdf_path or None, cover_letter_pdf_path or None
    )

    if resume_archive or cover_archive:
        update_pdf_paths(app_id, resume_archive, cover_archive)

    apps = list_applications()
    rows = _applications_to_dataframe_rows(apps)
    return f"✓ Saved application #{app_id}", rows


def handle_refresh_applications():
    """Reload applications from DB."""
    apps = list_applications()
    return _applications_to_dataframe_rows(apps)


def handle_mark_rejected(app_id, rejection_date):
    """Mark an application as rejected and refresh the dataframe."""
    if not app_id:
        return "❌ Enter an application ID", gr.update()
    if not rejection_date or not rejection_date.strip():
        return "❌ Enter a rejection date", gr.update()
    try:
        update_rejection(int(app_id), rejection_date.strip())
        apps = list_applications()
        rows = _applications_to_dataframe_rows(apps)
        return f"✓ Marked application #{int(app_id)} as rejected", rows
    except Exception as e:
        return f"❌ Error: {str(e)}", gr.update()


def handle_mark_interview(app_id, interview_date):
    """Mark an application as having an interview and refresh the dataframe."""
    if not app_id:
        return "❌ Enter an application ID", gr.update()
    if not interview_date or not interview_date.strip():
        return "❌ Enter an interview date", gr.update()
    try:
        update_interview(int(app_id), interview_date.strip())
        apps = list_applications()
        rows = _applications_to_dataframe_rows(apps)
        return f"✓ Marked application #{int(app_id)} as interview scheduled", rows
    except Exception as e:
        return f"❌ Error: {str(e)}", gr.update()


def handle_reset():
    """Reset all session components and state variables to startup defaults."""
    return (
        # Tab 1 inputs (8)
        gr.update(value=""),    # jd
        gr.update(value=""),    # job_title
        gr.update(value=""),    # company
        gr.update(value=""),    # info
        gr.update(value=None),  # bullet_file
        gr.update(value=False), # job_change
        gr.update(value={}),    # output
        gr.update(value="", visible=False),  # generate_status
        # State variables (16)
        "",        # state_summary
        [],        # state_spins
        [],        # state_programmer
        [],        # state_analyst
        "",        # state_job_title
        "",        # state_cover_letter_html
        "",        # state_selected_bullet_file
        [],        # state_analyzed_bullets
        {},        # state_jd_analysis
        set(),     # state_used_bullet_ids
        "",        # state_job_description
        [],        # state_canonical_bullets
        "General", # state_role
        "",        # state_company_name
        None,      # state_resume_pdf_path
        None,      # state_cover_letter_pdf_path
        # Tab 2 Edit components (18)
        gr.update(value=""),    # edit_summary
        gr.update(value=""),    # edit_spins
        gr.update(value=""),    # edit_programmer
        gr.update(value=""),    # edit_analyst
        gr.update(value=_get_default_tools_text()),  # edit_tools
        gr.update(choices=[], value=None),  # spins_bullet_radio
        gr.update(choices=[], value=None),  # programmer_bullet_radio
        gr.update(choices=[], value=None),  # analyst_bullet_radio
        gr.update(value="", visible=False),  # spins_suggestion_status
        gr.update(value="", visible=False),  # programmer_suggestion_status
        gr.update(value="", visible=False),  # analyst_suggestion_status
        gr.update(value="", visible=False),  # removed_bullet_display
        gr.update(choices=[], value=None, visible=False),  # suggestions_radio
        gr.update(value="", visible=False),  # suggestion_explanation
        gr.update(value="", visible=False),  # coverage_warning
        gr.update(visible=False),  # confirm_replace_btn
        gr.update(visible=False),  # cancel_replace_btn
        gr.update(value="", visible=False),  # replacement_status
        # Tab 2 Edit internal states (3)
        "",  # replacement_target_section
        0,   # replacement_target_index
        {},  # replacement_removed_bullet
        # Tab 4 Preview (3)
        gr.update(value=""),    # preview_html
        gr.update(value=None),  # pdf_file_output
        gr.update(value=""),    # status_message
        # Tab 5 Cover Letter (8)
        gr.update(value=""),    # company_hook
        gr.update(value=""),    # personal_alignment
        gr.update(value=""),    # credibility_anchor
        gr.update(value=True),  # include_gap
        gr.update(value=None),  # gap_role_dropdown
        gr.update(value=""),    # gap_text
        gr.update(value={}),    # cover_output
        gr.update(value="", visible=False),  # cover_generation_status
        # Tab 6 Cover Letter Preview (4, was 3)
        gr.update(value=""),    # cover_letter_edit
        gr.update(value=""),    # cover_preview_html
        gr.update(value=None),  # cover_pdf_file_output
        gr.update(value=""),    # cover_status_message
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
        state_role = gr.State(value="General")             # Role for technical skills ordering

        # Job Tracker state
        state_company_name = gr.State(value="")
        state_resume_pdf_path = gr.State(value=None)
        state_cover_letter_pdf_path = gr.State(value=None)

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

            with gr.Row():
                run = gr.Button("Generate Resume", variant="primary")
                reset_btn = gr.Button("Reset", variant="secondary")
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

                    with gr.Accordion("Tools and Environments", open=True):
                        edit_tools = gr.Textbox(
                            label="Edit tools (one per line)",
                            lines=5,
                            interactive=True
                        )

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

                bullets_editor = gr.Dataframe(
                    label="Bullets",
                    headers=["Bullet Text", _SECTION_HEADER],
                    datatype=["str", "str"],
                    type="array",
                    col_count=(2, "fixed"),
                    interactive=True,
                    wrap=True,
                    value=[],
                )

                with gr.Row():
                    bullet_count_display = gr.Label(label="\nBullet Count", value="0 bullets")
                    validation_display = gr.Label(label="Section Validation", value="Ready")

                with gr.Row():
                    save_btn = gr.Button("Save Changes", variant="primary")
                    discard_btn = gr.Button("Discard Changes", variant="secondary")
                    refresh_btn = gr.Button("Refresh from File", variant="secondary")

            editor_status = gr.Textbox(label="Status", interactive=False, lines=2)

            # Hidden state variables
            current_bullet_file_path = gr.State(value="")
            original_role = gr.State(value="")
            original_bullets_text = gr.State(value=[])

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
            gr.Markdown("### Edit Cover Letter Text")
            gr.Markdown("Review and edit the paragraph text below, then click **Update Preview** to refresh.")
            cover_letter_edit = gr.Textbox(
                label="Cover Letter Body (editable)",
                lines=15,
                interactive=True
            )
            update_cover_preview_btn = gr.Button("Update Preview", variant="secondary")
            cover_preview_html = gr.HTML(label="Cover Letter Preview")
            generate_cover_pdf_btn = gr.Button("Generate PDF")
            cover_pdf_file_output = gr.File(label="Download Cover Letter PDF")
            cover_status_message = gr.Textbox(label="Status", interactive=False)

        # Tab 7: Job Tracker
        with gr.Tab("Job Tracker") as tracker_tab:
            with gr.Accordion("Save Current Application", open=True):
                tracker_applied_date = gr.Textbox(label="Applied Date (MM-DD-YYYY)", value="")
                tracker_company = gr.Textbox(label="Company")
                tracker_job_title_input = gr.Textbox(label="Job Title")
                tracker_job_description = gr.Textbox(label="Job Description", lines=4)
                tracker_notes = gr.Textbox(label="Notes (optional)", lines=2)
                tracker_resume_path_display = gr.Textbox(label="Resume PDF", interactive=False)
                tracker_cover_letter_path_display = gr.Textbox(label="Cover Letter PDF", interactive=False)
                save_application_btn = gr.Button("Save Application", variant="primary")
                save_status = gr.Markdown(value="")

            refresh_applications_btn = gr.Button("Refresh Applications")
            applications_df = gr.Dataframe(
                headers=["ID", "Date", "Company", "Title", "Status", "Days", "Notes"],
                datatype=["number", "str", "str", "str", "str", "number", "str"],
                label="Applications",
                wrap=True,
            )

            gr.Markdown("---\n### Update Application Status")
            with gr.Row():
                update_app_id = gr.Number(label="Application ID", precision=0)
                with gr.Column():
                    rejection_date_input = gr.Textbox(label="Rejection Date (MM-DD-YYYY)")
                    mark_rejected_btn = gr.Button("Mark Rejected")
                with gr.Column():
                    interview_date_input = gr.Textbox(label="Interview Date (MM-DD-YYYY)")
                    mark_interview_btn = gr.Button("Mark Interview Scheduled")
            update_status = gr.Markdown(value="")

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
                state_role,                  # State: role for technical skills ordering
                spins_bullet_radio,          # Radio: SPINS bullet selection
                programmer_bullet_radio,     # Radio: Programmer bullet selection
                analyst_bullet_radio,        # Radio: Analyst bullet selection
                generate_status,             # Status: Generation status message
                state_company_name,          # State: company name for Job Tracker
                edit_tools,                  # Tab 2: tools and environments textbox
            ]
        )

        reset_btn.click(
            fn=handle_reset,
            inputs=[],
            outputs=[
                jd, job_title, company, info, bullet_file, job_change, output, generate_status,
                state_summary, state_spins, state_programmer, state_analyst,
                state_job_title, state_cover_letter_html, state_selected_bullet_file,
                state_analyzed_bullets, state_jd_analysis, state_used_bullet_ids,
                state_job_description, state_canonical_bullets, state_role,
                state_company_name, state_resume_pdf_path, state_cover_letter_pdf_path,
                edit_summary, edit_spins, edit_programmer, edit_analyst, edit_tools,
                spins_bullet_radio, programmer_bullet_radio, analyst_bullet_radio,
                spins_suggestion_status, programmer_suggestion_status, analyst_suggestion_status,
                removed_bullet_display, suggestions_radio, suggestion_explanation,
                coverage_warning, confirm_replace_btn, cancel_replace_btn, replacement_status,
                replacement_target_section, replacement_target_index, replacement_removed_bullet,
                preview_html, pdf_file_output, status_message,
                company_hook, personal_alignment, credibility_anchor, include_gap,
                gap_role_dropdown, gap_text, cover_output, cover_generation_status,
                cover_letter_edit, cover_preview_html, cover_pdf_file_output, cover_status_message,
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
            inputs=[state_summary, state_canonical_bullets, state_role, edit_tools],
            outputs=preview_html
        )

        # Generate PDF
        generate_pdf_btn.click(
            fn=handle_pdf_generation,
            inputs=preview_html,
            outputs=[pdf_file_output, status_message, state_resume_pdf_path]
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
            fn=handle_cover_letter_tab_select,
            inputs=state_cover_letter_html,
            outputs=[cover_letter_edit, cover_preview_html]
        )

        # Update preview from edited text
        update_cover_preview_btn.click(
            fn=handle_update_cover_preview,
            inputs=cover_letter_edit,
            outputs=[state_cover_letter_html, cover_preview_html]
        )

        # Generate cover letter PDF
        generate_cover_pdf_btn.click(
            fn=handle_cover_letter_pdf_generation,
            inputs=state_cover_letter_html,
            outputs=[cover_pdf_file_output, cover_status_message, state_cover_letter_pdf_path]
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

        # ===== JOB TRACKER EVENT HANDLERS =====

        # Pre-fill form and load dataframe when Tab 7 is selected
        tracker_tab.select(
            fn=handle_tracker_tab_select,
            inputs=[
                state_company_name,
                state_job_title,
                state_job_description,
                state_resume_pdf_path,
                state_cover_letter_pdf_path,
            ],
            outputs=[
                tracker_applied_date,
                tracker_company,
                tracker_job_title_input,
                tracker_job_description,
                tracker_resume_path_display,
                tracker_cover_letter_path_display,
                applications_df,
            ]
        )

        # Save application
        save_application_btn.click(
            fn=handle_save_application,
            inputs=[
                tracker_applied_date,
                tracker_company,
                tracker_job_title_input,
                tracker_job_description,
                tracker_notes,
                state_resume_pdf_path,
                state_cover_letter_pdf_path,
            ],
            outputs=[save_status, applications_df]
        )

        # Refresh applications dataframe
        refresh_applications_btn.click(
            fn=handle_refresh_applications,
            inputs=[],
            outputs=[applications_df]
        )

        # Mark rejected
        mark_rejected_btn.click(
            fn=handle_mark_rejected,
            inputs=[update_app_id, rejection_date_input],
            outputs=[update_status, applications_df]
        )

        # Mark interview scheduled
        mark_interview_btn.click(
            fn=handle_mark_interview,
            inputs=[update_app_id, interview_date_input],
            outputs=[update_status, applications_df]
        )

    init_db()
    demo.launch(theme=gr.themes.Soft())


if __name__ == "__main__":
    launch_app()
