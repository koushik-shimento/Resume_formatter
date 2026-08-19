# Resume Parser

A desktop application that converts resumes into a standardized client format.

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
git clone https://github.com/Kollakoushik/Resume_parser.git
cd Resume_parser
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

The DOCX is still created.

Install one of:

- Microsoft Word
- LibreOffice

and try again.

## LLM is not used

Check:

- `RESUME_LLM_PROVIDER`
- API key
- Internet connectivity

---

# License

Internal recruiting tool.
