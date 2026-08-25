"""Browser interface for the Resume Formatter."""

from __future__ import annotations

import tempfile
import zipfile
from io import BytesIO
from pathlib import Path

import streamlit as st

from core import extract, llm_normalizer, parser
from core.export import PdfExportError, to_pdf
from core.model import Education, Job, ResumeData, SkillGroup
from core.render_shimentox import render


SUPPORTED_TYPES = ["pdf", "docx", "rtf", "txt"]


def parse_upload(name: str, content: bytes) -> ResumeData:
    """Parse an uploaded resume in an isolated temporary directory."""
    suffix = Path(name).suffix.lower()
    if suffix not in {f".{item}" for item in SUPPORTED_TYPES}:
        raise ValueError(f"Unsupported file type: {suffix or 'unknown'}")
    with tempfile.TemporaryDirectory(prefix="resume-upload-") as directory:
        path = Path(directory) / f"source{suffix}"
        path.write_bytes(content)
        lines = extract.extract(str(path))
    fallback = Path(name).stem.replace("_", " ").replace("-", " ")
    parsed = parser.parse(lines, fallback_name=fallback)
    if llm_normalizer.configured():
        raw_text = "\n".join(line.text for line in lines)
        return llm_normalizer.normalize(raw_text, fallback=parsed)
    return parsed


def build_outputs(data: ResumeData) -> tuple[str, bytes, str, bytes]:
    """Render DOCX and PDF and return stable download payloads."""
    safe_stem = "".join(c for c in data.name if c.isalnum() or c in " -_").strip()
    safe_stem = safe_stem.replace(" ", "_") or "formatted_resume"
    with tempfile.TemporaryDirectory(prefix="resume-export-") as directory:
        docx_path = render(data, Path(directory) / f"{safe_stem}.docx")
        pdf_path = to_pdf(docx_path)
        return docx_path.name, docx_path.read_bytes(), pdf_path.name, pdf_path.read_bytes()


def bundle_outputs(docx_name: str, docx: bytes, pdf_name: str, pdf: bytes) -> bytes:
    buffer = BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr(docx_name, docx)
        archive.writestr(pdf_name, pdf)
    return buffer.getvalue()


def _load_editor(data: ResumeData) -> None:
    st.session_state.resume_data = data
    st.session_state.name = data.name
    st.session_state.summary = "\n".join(data.summary)
    st.session_state.skills = "\n".join(
        f"{group.category}: {group.values}" if group.category else group.values
        for group in data.skills
    )
    st.session_state.experience = "\n\n".join(
        " | ".join((job.company, job.title, job.dates, job.project))
        + "\n" + "\n".join(f"- {bullet}" for bullet in job.bullets)
        for job in data.experience
    )
    st.session_state.certifications = "\n".join(data.certifications)
    st.session_state.education = "\n".join(
        " | ".join((edu.degree, edu.institution, edu.year)) for edu in data.education
    )
    st.session_state.pop("outputs", None)


def _collect_editor() -> ResumeData:
    skills = []
    for line in st.session_state.skills.splitlines():
        line = line.strip()
        if not line:
            continue
        category, separator, values = line.partition(":")
        skills.append(SkillGroup(category.strip() if separator else "", values.strip() if separator else category.strip()))

    jobs = []
    for block in st.session_state.experience.split("\n\n"):
        lines = [line.strip() for line in block.splitlines() if line.strip()]
        if not lines:
            continue
        fields = [field.strip() for field in lines[0].split("|")]
        fields.extend([""] * (4 - len(fields)))
        bullets = [line.lstrip("-• ").strip() for line in lines[1:] if line.lstrip("-• ").strip()]
        jobs.append(Job(company=fields[0], title=fields[1], dates=fields[2], project=fields[3], bullets=bullets))

    education = []
    for line in st.session_state.education.splitlines():
        fields = [field.strip() for field in line.split("|")]
        if any(fields):
            fields.extend([""] * (3 - len(fields)))
            education.append(Education(degree=fields[0], institution=fields[1], year=fields[2]))

    return ResumeData(
        name=st.session_state.name.strip(),
        summary=[line.strip().lstrip("-• ") for line in st.session_state.summary.splitlines() if line.strip()],
        skills=skills,
        experience=jobs,
        certifications=[line.strip().lstrip("-• ") for line in st.session_state.certifications.splitlines() if line.strip()],
        education=education,
    )


def main() -> None:
    st.set_page_config(page_title="ShimentoX Resume Formatter", page_icon="📄", layout="wide")
    st.title("ShimentoX Resume Formatter")
    st.caption("Upload, review, and export a resume in the approved ShimentoX format.")

    upload = st.file_uploader("Upload resume", type=SUPPORTED_TYPES)
    if upload is not None:
        identity = (upload.name, upload.size)
        if st.session_state.get("upload_identity") != identity:
            with st.spinner("Reading resume…"):
                try:
                    _load_editor(parse_upload(upload.name, upload.getvalue()))
                    st.session_state.upload_identity = identity
                except Exception as exc:
                    st.error(f"Could not read this resume: {exc}")
                    return

    if "resume_data" not in st.session_state:
        st.info("Upload a PDF, DOCX, RTF, or TXT resume to begin.")
        return

    st.subheader("Review extracted content")
    st.text_input("Candidate name", key="name")
    left, right = st.columns(2)
    with left:
        st.text_area("Summary — one item per line", key="summary", height=180)
        st.text_area("Skills — Category: values", key="skills", height=180)
        st.text_area("Certifications — one per line", key="certifications", height=130)
    with right:
        st.text_area(
            "Experience — first line: Company | Title | Dates | Project; bullets below; blank line between roles",
            key="experience", height=360,
        )
        st.text_area("Education — Degree | Institution | Year", key="education", height=130)

    if st.button("Generate DOCX + PDF", type="primary", use_container_width=True):
        with st.spinner("Applying the template and creating downloads…"):
            try:
                st.session_state.outputs = build_outputs(_collect_editor())
            except PdfExportError as exc:
                st.error(str(exc))
            except Exception as exc:
                st.error(f"Export failed: {exc}")

    if "outputs" in st.session_state:
        docx_name, docx, pdf_name, pdf = st.session_state.outputs
        st.success("Resume generated successfully.")
        one, two, three = st.columns(3)
        one.download_button("Download DOCX", docx, docx_name, "application/vnd.openxmlformats-officedocument.wordprocessingml.document", use_container_width=True)
        two.download_button("Download PDF", pdf, pdf_name, "application/pdf", use_container_width=True)
        three.download_button("Download both (ZIP)", bundle_outputs(docx_name, docx, pdf_name, pdf), f"{Path(docx_name).stem}.zip", "application/zip", use_container_width=True)


if __name__ == "__main__":
    main()
