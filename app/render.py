from weasyprint import HTML

def render_html_to_pdf(html_content, output_path):
    HTML(string=html_content).write_pdf(output_path)
