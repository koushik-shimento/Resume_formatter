import tempfile
import unittest
import shutil
from pathlib import Path

from docx import Document

from core.model import Education, Job, ResumeData, SkillGroup
from core.export import to_pdf
from core.render_shimentox import render


class RenderTests(unittest.TestCase):
    def test_render_preserves_content_and_client_layout(self):
        data = ResumeData(
            name="Jane Doe",
            summary=["Delivers reliable software."],
            skills=[SkillGroup("Languages", "Python, SQL")],
            experience=[Job("Example Ltd", "2022 - Present", "Engineer", "Atlas",
                            ["Improved processing time."])],
            certifications=["Cloud Practitioner"],
            education=[Education("B.Tech", "Example University", "2022")],
        )
        with tempfile.TemporaryDirectory() as directory:
            output = render(data, Path(directory) / "resume.docx")
            document = Document(output)
            body = "\n".join(p.text for p in document.paragraphs)
            header = document.sections[0].header.paragraphs[0].text

        self.assertIn("Jane Doe", header)
        for expected in ("Summary:", "Technical Skills:", "Professional Experience:",
                         "Certifications:", "Education:", "Example Ltd", "2022 - Present"):
            self.assertIn(expected, body)
        self.assertTrue(all(p.paragraph_format.space_after.pt == 0
                            for p in document.paragraphs if p.paragraph_format.space_after))

    @unittest.skipUnless(shutil.which("soffice"), "LibreOffice is not installed")
    def test_end_to_end_docx_and_pdf_export(self):
        data = ResumeData(name="UAT Candidate", summary=["End-to-end export check."])
        with tempfile.TemporaryDirectory() as directory:
            docx = render(data, Path(directory) / "uat-resume.docx")
            pdf = to_pdf(docx)
            self.assertGreater(docx.stat().st_size, 0)
            self.assertGreater(pdf.stat().st_size, 0)
            self.assertEqual(pdf.read_bytes()[:4], b"%PDF")


if __name__ == "__main__":
    unittest.main()
