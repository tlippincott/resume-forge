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
from ui.bullet_editor_helpers import (
    load_bullet_library,
    save_bullet_library,
    create_new_bullet_library,
    count_bullets,
    get_validation_summary
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
        return {"error": "Please select a bullet file"}, "", "", "", "", "", [], [], [], "", "", [], {}, set(), ""

    # Call existing generate_resume()
    result = generate_resume(jd, company, info, bullet_file, job_change)

    # Extract plain lists (no parsing needed)
    summary = result["summary"]
    spins_list = result["spins"]
    programmer_list = result["programmer"]
    analyst_list = result["analyst"]

    # NEW: Extract intelligence metadata
    metadata = result.get("metadata", {})
    analyzed_bullets = metadata.get("analyzed_bullets", [])
    jd_analysis = metadata.get("jd_analysis", {})
    used_bullet_ids = metadata.get("used_bullet_ids", set())

    # Build bullet lookup map (text → full bullet data)
    bullet_map = {b["text"]: b for b in analyzed_bullets}

    # Enhance section lists with IDs for tracking
    def add_bullet_ids(text_list):
        return [bullet_map.get(text, {"text": text, "bullet_id": ""}) for text in text_list]

    spins_with_ids = add_bullet_ids(spins_list)
    programmer_with_ids = add_bullet_ids(programmer_list)
    analyst_with_ids = add_bullet_ids(analyst_list)

    # Convert to text for textboxes
    spins_text = bullets_to_text(spins_list)
    programmer_text = bullets_to_text(programmer_list)
    analyst_text = bullets_to_text(analyst_list)

    # Return includes new intelligence states
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
        analyzed_bullets,      # State: analyzed_bullets (NEW)
        jd_analysis,           # State: jd_analysis (NEW)
        used_bullet_ids,       # State: used_bullet_ids (NEW)
        jd                     # State: job_description (NEW)
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


def handle_load_bullet_library(file_path):
    """Load bullet library from file."""
    if not file_path:
        return (
            gr.update(),  # role_editor
            gr.update(),  # bullets_editor
            gr.update(visible=False),  # editor_group
            "Please select a file",  # editor_status
            "",  # current_bullet_file_path
            "",  # original_role
            "",  # original_bullets_text
            "0 bullets",  # bullet_count_display
            "Ready"  # validation_display
        )

    role, bullets_text, status = load_bullet_library(file_path)

    if not role:  # Error occurred
        return (
            gr.update(),  # role_editor
            gr.update(),  # bullets_editor
            gr.update(visible=False),  # editor_group
            status,  # editor_status
            "",  # current_bullet_file_path
            "",  # original_role
            "",  # original_bullets_text
            "0 bullets",  # bullet_count_display
            "Ready"  # validation_display
        )

    # Success
    bullet_count = count_bullets(bullets_text)
    validation = get_validation_summary(bullets_text)

    return (
        gr.update(value=role),  # role_editor
        gr.update(value=bullets_text),  # bullets_editor
        gr.update(visible=True),  # editor_group
        status,  # editor_status
        file_path,  # current_bullet_file_path
        role,  # original_role
        bullets_text,  # original_bullets_text
        f"{bullet_count} bullets",  # bullet_count_display
        validation  # validation_display
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
    Generate intelligent replacement suggestions.

    Returns:
        Tuple of UI component updates
    """
    from app.bullet_intelligence import suggest_replacements
    from ui.resume_helpers import extract_bullet_texts

    # Convert 1-based to 0-based
    index = int(bullet_index) - 1

    # Get active section
    if section_name == "SPINS":
        active_list = spins_list
    elif section_name == "Programmer":
        active_list = programmer_list
    else:  # Analyst
        active_list = analyst_list

    # Validate index
    if index < 0 or index >= len(active_list):
        error_msg = f"❌ Invalid bullet index: {bullet_index}. Section has {len(active_list)} bullets."
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
            gr.Markdown(value=error_msg, visible=True)
        )

    # Get removed bullet
    removed_bullet = active_list[index]
    removed_text = removed_bullet.get("text", str(removed_bullet))

    # Get top 5 suggestions
    suggestions = suggest_replacements(
        removed_bullet=removed_bullet,
        all_bullets=analyzed_bullets,
        active_bullet_ids=used_bullet_ids,
        active_bullets=active_list,
        jd_analysis=jd_analysis
    )

    # Format removed bullet display
    removed_display = f"""#### Replacing Bullet #{bullet_index}:
**Original:** {removed_text[:150]}{"..." if len(removed_text) > 150 else ""}

**Category:** {removed_bullet.get('category', 'unknown')} | **JD Score:** {removed_bullet.get('jd_score', 0)}
"""

    # Format suggestions for radio
    choices = []
    for i, sugg in enumerate(suggestions, 1):
        bullet = sugg["bullet"]
        score = sugg["score"]
        text = bullet["text"]

        # Truncate for display
        display_text = text[:100] + "..." if len(text) > 100 else text

        # Format: "⭐ 8.5 | [frontend] Bullet text..."
        choice_label = f"⭐ {score:.1f} | [{bullet['category']}] {display_text}"
        choices.append((choice_label, bullet["bullet_id"]))

    # Default explanation for first suggestion
    first_explanation = ""
    if suggestions:
        first_explanation = f"""#### Why This Suggestion?
{suggestions[0]['explanation']}

**Details:**
- **Category:** {suggestions[0]['bullet']['category']}
- **Keywords:** {', '.join(suggestions[0]['bullet']['keywords'][:5])}
- **Has Impact:** {'✓ Yes' if suggestions[0]['bullet']['has_impact'] else '✗ No'}
- **JD Score:** {suggestions[0]['bullet']['jd_score']}
"""

    # Skills coverage check
    coverage_msg = ""
    if suggestions:
        # Check if top suggestion has high skill overlap with active bullets
        top_bullet = suggestions[0]["bullet"]
        active_keywords = set()
        for b in active_list:
            active_keywords.update(b.get("keywords", []))

        top_keywords = set(top_bullet.get("keywords", []))
        overlap = top_keywords & active_keywords

        if len(overlap) >= 3:
            coverage_msg = f"""⚠️ **Skills Coverage Warning**
Top suggestion shares {len(overlap)} skills with existing bullets: {', '.join(list(overlap)[:4])}

Consider lower-ranked suggestions for better skill diversity.
"""

    return (
        gr.Markdown(value=removed_display, visible=True),
        gr.Radio(choices=choices, value=choices[0][1] if choices else None, visible=True),
        gr.Markdown(value=first_explanation, visible=True),
        gr.Markdown(value=coverage_msg, visible=True) if coverage_msg else gr.Markdown(value="", visible=False),
        section_name,
        index,
        removed_bullet,
        gr.Button(visible=True),
        gr.Button(visible=True),
        gr.Markdown(value="", visible=False)
    )


def handle_suggestion_selected(
    selected_bullet_id: str,
    analyzed_bullets: list,
    jd_analysis: dict
):
    """Update explanation when user selects a different suggestion."""
    from app.bullet_intelligence import generate_explanation

    # Find selected bullet
    selected = None
    for bullet in analyzed_bullets:
        if bullet["bullet_id"] == selected_bullet_id:
            selected = bullet
            break

    if not selected:
        return ""

    explanation = f"""#### Why This Suggestion?
{generate_explanation(selected, {}, jd_analysis)}

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
    Execute the intelligent bullet replacement.

    Returns updated state and UI elements.
    """
    from ui.resume_helpers import replace_bullet_in_list, extract_bullet_texts

    # Find replacement bullet by ID
    replacement_bullet = None
    for bullet in analyzed_bullets:
        if bullet["bullet_id"] == selected_bullet_id:
            replacement_bullet = bullet
            break

    if not replacement_bullet:
        error_msg = "❌ Error: Could not find selected bullet."
        return tuple([gr.Markdown(value=error_msg, visible=True)] + [gr.update()] * 13)

    # Update appropriate section
    if target_section == "SPINS":
        old_bullet = spins_list[target_index]
        spins_list = replace_bullet_in_list(spins_list.copy(), target_index, replacement_bullet)
        updated_spins = spins_list
        updated_programmer = programmer_list
        updated_analyst = analyst_list
    elif target_section == "Programmer":
        old_bullet = programmer_list[target_index]
        programmer_list = replace_bullet_in_list(programmer_list.copy(), target_index, replacement_bullet)
        updated_spins = spins_list
        updated_programmer = programmer_list
        updated_analyst = analyst_list
    else:  # Analyst
        old_bullet = analyst_list[target_index]
        analyst_list = replace_bullet_in_list(analyst_list.copy(), target_index, replacement_bullet)
        updated_spins = spins_list
        updated_programmer = programmer_list
        updated_analyst = analyst_list

    # Update used bullet IDs
    used_bullet_ids = used_bullet_ids.copy()
    used_bullet_ids.discard(old_bullet.get("bullet_id", ""))
    used_bullet_ids.add(replacement_bullet["bullet_id"])

    # Convert to text
    spins_text = bullets_to_text(extract_bullet_texts(updated_spins))
    programmer_text = bullets_to_text(extract_bullet_texts(updated_programmer))
    analyst_text = bullets_to_text(extract_bullet_texts(updated_analyst))

    success_msg = f"""✓ **Replacement Complete!**
Bullet #{target_index + 1} in {target_section} updated.

**New bullet:** {replacement_bullet['text'][:100]}...
"""

    return (
        gr.Markdown(value=success_msg, visible=True),
        spins_text,
        programmer_text,
        analyst_text,
        updated_spins,
        updated_programmer,
        updated_analyst,
        used_bullet_ids,
        gr.Markdown(value="", visible=False),
        gr.Radio(choices=[], visible=False),
        gr.Markdown(value="", visible=False),
        gr.Markdown(value="", visible=False),
        gr.Button(visible=False),
        gr.Button(visible=False)
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
                        with gr.Row():
                            spins_bullet_index = gr.Number(
                                label="Bullet # to replace",
                                value=1,
                                precision=0,
                                minimum=1
                            )
                            open_replacement_spins = gr.Button("Get Suggestions", size="sm", variant="primary")

                    with gr.Accordion("Programmer Bullets (Technical Implementation)", open=True):
                        edit_programmer = gr.Textbox(
                            label="Edit bullets (one per line)",
                            lines=12,
                            interactive=True
                        )
                        with gr.Row():
                            programmer_bullet_index = gr.Number(
                                label="Bullet # to replace",
                                value=1,
                                precision=0,
                                minimum=1
                            )
                            open_replacement_programmer = gr.Button("Get Suggestions", size="sm", variant="primary")

                    with gr.Accordion("Analyst Bullets (Analysis & Documentation)", open=True):
                        edit_analyst = gr.Textbox(
                            label="Edit bullets (one per line)",
                            lines=12,
                            interactive=True
                        )
                        with gr.Row():
                            analyst_bullet_index = gr.Number(
                                label="Bullet # to replace",
                                value=1,
                                precision=0,
                                minimum=1
                            )
                            open_replacement_analyst = gr.Button("Get Suggestions", size="sm", variant="primary")

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
                state_job_description        # NEW: Preserve JD for suggestions
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

        # ===== INTELLIGENT REPLACEMENT EVENT HANDLERS =====

        # SPINS section - Get suggestions
        open_replacement_spins.click(
            fn=handle_get_suggestions,
            inputs=[
                gr.State(value="SPINS"),
                spins_bullet_index,
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
                programmer_bullet_index,
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
                analyst_bullet_index,
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
                cancel_replace_btn
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

    demo.launch(theme=gr.themes.Soft())


if __name__ == "__main__":
    launch_app()
