# Resume Forge

Resume Forge is a personal résumé and cover letter generation tool designed
to optimize relevance without sacrificing truth.

This is not a “write me a résumé” app.
It is a system for **re-expressing real experience** in ways that align
with specific job descriptions.

## Philosophy

### Truth first, expression second
All experience originates from curated bullet libraries written by the user.
The system never invents experience. It only selects and rewrites what already exists.

### Structure beats cleverness
The application uses structured JSON input and output rather than free-form text.
This reduces ambiguity, parsing errors, and accidental fabrication.

### Human in the loop
Generated output is meant to be reviewed, edited, and approved.
Automation assists thinking; it does not replace judgment.

### Modular over magical
There are no agents, chains, or hidden frameworks.
Each step is explicit:
1. Select relevant bullets
2. Rewrite for relevance
3. Assemble into documents

### Calm tooling
The stack prioritizes predictability and debuggability over trendiness.
This tool should feel boring to maintain and reliable to use.

## What this app does

- Takes a job description and company information
- Selects relevant experience from predefined bullet libraries
- Rewrites selected bullets for alignment
- Generates a tailored résumé and cover letter
- Outputs clean HTML and PDFs

## What this app does not do

- Invent experience
- Inflate accomplishments
- Optimize for keyword stuffing alone
- Attempt autonomous decision-making

## Tech stack

- Python for orchestration
- OpenAI API for controlled text transformation
- Gradio for a simple UI
- HTML/CSS for deterministic layout
- WeasyPrint for PDF generation

## Intended use

This tool is intended for personal or small-team use by someone who:
- Understands their own experience
- Wants control over representation
- Values honesty over exaggeration

If you don’t trust the output, don’t use it.
That’s a feature, not a bug.
