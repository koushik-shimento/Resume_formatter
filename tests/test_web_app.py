from io import BytesIO
from zipfile import ZipFile

import pytest

from core.model import ResumeData
from web_app import bundle_outputs, parse_upload


def test_parse_text_upload_retains_supported_sections():
    data = parse_upload(
        "Jane_Doe.txt",
        b"Jane Doe\nSummary\nReliable engineer\nSkills\nPython: FastAPI\nEducation\nBSc | Example University | 2022",
    )
    assert data.name
    assert "Reliable engineer" in data.summary
    assert data.skills
    assert data.education


def test_parse_upload_rejects_unsupported_files():
    with pytest.raises(ValueError, match="Unsupported file type"):
        parse_upload("resume.exe", b"data")


def test_bundle_contains_both_exports():
    result = bundle_outputs("resume.docx", b"docx", "resume.pdf", b"pdf")
    with ZipFile(BytesIO(result)) as archive:
        assert archive.namelist() == ["resume.docx", "resume.pdf"]
        assert archive.read("resume.docx") == b"docx"
        assert archive.read("resume.pdf") == b"pdf"
