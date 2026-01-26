import gradio as gr
from app.resume_engine import generate_resume
from pathlib import Path
from ui.resume_helpers import (
    build_html_bullets,
    bullets_to_text,
    text_to_bullets,
    load_resume_html,
    generate_pdf_file
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


def handle_generate(jd, company, info, bullet_file, job_change):
    """Generate resume and populate all tabs."""
    if not bullet_file:
        return {"error": "Please select a bullet file"}, "", "", "", "", "", [], [], []

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
        analyst_list          # State
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


def launch_app():
    with gr.Blocks() as demo:
        gr.Markdown("## Resume Forge")

        # State components
        state_summary = gr.State(value="")
        state_spins = gr.State(value=[])
        state_programmer = gr.State(value=[])
        state_analyst = gr.State(value=[])

        # Tab 1: Generate
        with gr.Tab("Generate"):
            jd = gr.Textbox(label="Job Description", lines=10)
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

        # Event handlers
        run.click(
            fn=handle_generate,
            inputs=[jd, company, info, bullet_file, job_change],
            outputs=[
                output,              # Tab 1: JSON
                edit_summary,        # Tab 2
                edit_spins,          # Tab 2
                edit_programmer,     # Tab 2
                edit_analyst,        # Tab 2
                state_summary,       # State
                state_spins,         # State
                state_programmer,    # State
                state_analyst        # State
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

    demo.launch(theme=gr.themes.Soft())
