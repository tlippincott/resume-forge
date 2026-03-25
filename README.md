# Resume Forge

Resume Forge is a local, Gradio-based tool for generating tailored résumés and cover letters. It
takes a job description, selects and rewrites bullets from your personal experience libraries using
an LLM, and outputs clean PDFs — without inventing anything that isn't already in your library.

This is not a "write me a résumé" app. It is a system for **re-expressing real experience** in ways
that align with specific job descriptions.

## Philosophy

### Truth first, expression second
All experience originates from curated bullet libraries written by the user. The system never
invents experience. It only selects and rewrites what already exists.

### Structure beats cleverness
The application uses structured JSON input and output rather than free-form text. This reduces
ambiguity, parsing errors, and accidental fabrication.

### Human in the loop
Generated output is meant to be reviewed, edited, and approved. Automation assists thinking; it does
not replace judgment.

### Modular over magical
There are no agents, chains, or hidden frameworks. Each step is explicit:
1. Score bullets against the job description
2. Select the top candidates per section
3. Rewrite for alignment
4. Assemble into documents

### Calm tooling
The stack prioritizes predictability and debuggability over trendiness. This tool should feel boring
to maintain and reliable to use.

## What this app does

### Resume generation
- Analyzes the job description to extract required and preferred skills
- Scores all bullets in the selected library against the JD
- Selects the top bullets per section: 12 spins + 12 programmer + 10 analyst = 34 total
- Rewrites selected bullets for alignment with the JD
- Generates a professional summary via a two-step pipeline (competency extraction, then summary
  generation)
- Outputs HTML and PDF

### Cover letter generation
Generates a structured cover letter in one of four variants depending on what optional inputs are
provided:
- Base only (4 paragraphs)
- Base + company motivation (5 paragraphs)
- Base + skill gap explanation (5 paragraphs)
- Base + company motivation + gap explanation (6 paragraphs)

### Bullet replacement
After resume generation, the user can select any bullet and request ranked replacement suggestions.
Each suggestion includes a score and explanation of why it was recommended (category match, skill
overlap, JD alignment, impact metrics).

### Job application tracker
A dedicated tab for tracking job applications backed by a local SQLite database. Records
applied date, company, job title, job description, interview/rejection dates, notes, and paths to
archived PDFs. Status is computed at query time. PDFs are archived to
`applications/{id}_{company}_{title}/` when an application is saved.

## What this app does not do

- Invent experience
- Inflate accomplishments
- Optimize for keyword stuffing alone
- Attempt autonomous decision-making

## Bullet libraries

Bullets are stored in `bullet_libs/*.json`. Each bullet has a text and a section designation:

```json
{"text": "Built REST API for user authentication using OAuth2...", "section": "programmer"}
```

**Sections:**
- `spins` — end-user interaction, communication, and soft-skill impact
- `programmer` — technical implementation and engineering work
- `analyst` — analysis, documentation, and requirements work

**Minimum per library:** 12 spins + 12 programmer + 10 analyst

**Included libraries:**
- `help_desk.json`
- `software_developer.json`
- `software_analyst.json`
- `sales_engineer.json`

## Tech stack

- **Python** — orchestration and business logic
- **OpenAI API** — bullet scoring, rewriting, summary generation, cover letter generation
- **Gradio** — local web UI
- **WeasyPrint** — HTML-to-PDF generation
- **gradio-pdf** — in-UI PDF viewer (displays the generated PDFs inline)
- **SQLite** — job application tracking database

## Setup

```bash
cp .env.example .env
# Edit .env and set API_KEY to your OpenAI API key
pip install -r requirements.txt
python run.py
```

The app opens at `http://localhost:7860`.

## Configuration

All configuration is done through environment variables in `.env`. See `.env.example` for the full
list with descriptions and defaults. Key settings:

| Category | Variable | Default | Notes |
|---|---|---|---|
| API | `API_KEY` | *(required)* | OpenAI API key |
| API | `MODEL_NAME` | `gpt-4o-mini` | Model to use |
| API | `DEFAULT_TIMEOUT` | `60` | Request timeout in seconds |
| LLM | `LLM_TEMPERATURE_DETERMINISTIC` | `0.0` | Used for scoring and analysis |
| LLM | `LLM_TEMPERATURE_CREATIVE` | `0.7` | Used for rewriting and cover letters |
| Business | `BUSINESS_SPINS_MIN` / `_MAX` | `12` | Bullet count for spins section |
| Business | `BUSINESS_PROGRAMMER_MIN` / `_MAX` | `12` | Bullet count for programmer section |
| Business | `BUSINESS_ANALYST_MIN` / `_MAX` | `10` | Bullet count for analyst section |
| Scoring | `SCORING_REQUIRED_SKILL_WEIGHT` | `3` | Weight for required skill matches |
| Scoring | `SCORING_PREFERRED_SKILL_WEIGHT` | `1` | Weight for preferred skill matches |
| Output | `OUTPUT_PDF_COPY_DIR` | *(optional)* | External directory to copy PDFs to |
| Logging | `LOG_LEVEL` | `INFO` | Root log level |

## Testing

```bash
pytest                           # all tests
pytest -m unit                   # unit tests only
pytest -m integration            # integration tests (makes real API calls, ~2 min)
pytest --ignore=tests/integration/test_openai_client.py  # skip pre-existing broken test
```

## Intended use

This tool is intended for personal or small-team use by someone who:
- Understands their own experience
- Wants control over representation
- Values honesty over exaggeration

If you don't trust the output, don't use it. That's a feature, not a bug.
