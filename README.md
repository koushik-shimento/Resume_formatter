# Resume Parser

A desktop and browser application that converts resumes into a standardized client format.

## Release status

The current `main` release is UAT-ready. It includes non-blocking resume parsing,
verified DOCX and PDF export, a high-resolution ShimentoX logo fixed to the
top-right header, and regression coverage for supported resume sections.

Validation completed before release:

- 11 automated tests
- 20 repeated parser iterations for summary and skill retention
- 20 repeated render iterations covering summary, skills, experience,
  responsibilities, certifications, and education
- End-to-end DOCX-to-PDF conversion with LibreOffice
- GitHub Actions CI

## Features

- Supports PDF, DOCX, DOC, RTF and TXT resumes
- Extracts resume content
- Organizes information into:
  - Summary
  - Technical Skills
  - Professional Experience
  - Certifications
  - Education
- Exports professionally formatted DOCX
- Converts DOCX to PDF (Microsoft Word or LibreOffice required)
- Optional LLM normalization (when configured)

---

# Requirements

- Python 3.11+
- Windows 10/11 (recommended)
- Microsoft Word or LibreOffice (for PDF export)

---

# Installation

Clone the repository:

```bash
git clone https://github.com/koushik-shimento/Resume_formatter.git
cd Resume_formatter
```

Create a virtual environment:

```bash
python -m venv .venv
```

Activate it:

Windows

```bash
.venv\Scripts\activate
```

Linux/macOS

```bash
source .venv/bin/activate
```

Install dependencies:

```bash
pip install -r requirements.txt
```

---

# Running the application

Run:

```bash
python app.py
```

The GUI will open.

## Browser version

Run locally:

```bash
streamlit run web_app.py
```

The browser version accepts PDF, DOCX, RTF, and TXT uploads, provides a review
screen for every supported section, and generates DOCX and PDF downloads. The
Docker image includes LibreOffice, so hosted PDF conversion does not depend on
software installed on the user's computer.

### Render deployment

The included `render.yaml` and `Dockerfile` define the complete web service.
Connect this repository as a Render Blueprint to deploy it. Render redeploys
the service automatically whenever `main` changes.

Opening and parsing runs in a background worker so large resumes do not freeze
the interface. Export also runs in the background.

---

# Using the application

1. Click **Open Resume**
2. Select a PDF, DOCX, DOC, RTF or TXT resume.
3. Review the extracted information.
4. Select the client template.
5. Click **Export DOCX + PDF**.
6. The formatted resume will be saved.

---

# Optional LLM Normalization

The application can optionally use an LLM to normalize difficult resumes.

Configure:

```text
RESUME_LLM_PROVIDER=openai
OPENAI_API_KEY=your_api_key
```

or

```text
RESUME_LLM_PROVIDER=anthropic
ANTHROPIC_API_KEY=your_api_key
```

If no provider is configured, the application uses the built-in parser.

---

# Project Structure

```
app.py
core/
    extract.py
    parser.py
    llm_normalizer.py
    model.py
    export.py
    render_shimentox.py
templates/
```

---

# Supported Resume Formats

- PDF
- DOCX
- DOC
- TXT
- RTF

---

# Output

Every resume is formatted into the company's standard template containing:

- Summary
- Technical Skills
- Professional Experience
- Certifications
- Education

---

# Troubleshooting

## PDF export fails

The DOCX is still created. PDF conversion now checks only converters that are
actually available, uses an isolated LibreOffice process to avoid profile-lock
delays, and reports a clear error when neither converter is installed.

Install one of:

- Microsoft Word
- LibreOffice

and try again.

The generated `.docx` and `.pdf` are saved together in the folder selected in
the Save dialog. The application opens that folder after export and lists both
exact filenames in the completion message.

---

# UAT verification

Run the automated regression suite before starting UAT:

```bash
python -m unittest discover -s tests -v
```

For PDF UAT, run on a Windows machine with Microsoft Word installed or on a
machine with LibreOffice. Verify that both output files open and that the PDF
matches the DOCX pagination.

The ShimentoX logo is embedded in the Word template at high resolution with a
locked aspect ratio. To replace it later, run `scripts/update_template_logo.py`
with the new PNG and commit both the source asset and updated template.

## LLM is not used

Check:

- `RESUME_LLM_PROVIDER`
- API key
- Internet connectivity

---

# License

Internal recruiting tool.
