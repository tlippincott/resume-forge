import gradio as gr
from app.resume_engine import generate_resume
from pathlib import Path

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

def launch_app():
    with gr.Blocks() as demo:
        gr.Markdown("## Resume Forge")

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
        run.click(
            fn=lambda jd, c, i, bf, j,: generate_resume(
                jd, c, i, bf, j,
            ) if bf else {"error": "Please select a bullet file"},
            inputs=[jd, company, info, bullet_file, job_change],
            outputs=output
        )

    demo.launch()
