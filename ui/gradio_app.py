import gradio as gr
from app.resume_engine import generate_resume

def launch_app():
    with gr.Blocks() as demo:
        gr.Markdown("## Resume Forge")

        jd = gr.Textbox(label="Job Description", lines=10)
        company = gr.Textbox(label="Company Name")
        info = gr.Textbox(label="Company Info", lines=5)
        job_change = gr.Checkbox(label="Customer-facing role")

        output = gr.JSON()

        run = gr.Button("Generate Resume")
        run.click(
            fn=lambda jd, c, i, j: generate_resume(
                jd, c, i, j,
                {
                    "spins": "bullet_libs/spins.json",
                    "programmer": "bullet_libs/programmer.json",
                    "analyst": "bullet_libs/analyst.json"
                }
            ),
            inputs=[jd, company, info, job_change],
            outputs=output
        )

    demo.launch()
