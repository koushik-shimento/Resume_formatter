import shutil
import tempfile
import unittest
from pathlib import Path

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from PIL import Image

from core.model import Education, ExtraSection, Job, ResumeData, SkillGroup
from core.export import to_pdf
from core.render_shimentox import render


class RenderTests(unittest.TestCase):
    def test_additional_sections_are_rendered_without_loss(self):
        data = ResumeData(
            name="Jane Doe",
            summary=["Engineer"],
            additional_sections=[ExtraSection("Languages", ["English, Hindi"])],
        )
        with tempfile.TemporaryDirectory() as directory:
            output = render(data, Path(directory) / "resume.docx")
            document = Document(output)
        body = "\n".join(paragraph.text for paragraph in document.paragraphs)
        self.assertIn("Languages:", body)
        self.assertIn("English, Hindi", body)

    def test_approved_logo_asset_has_white_background_and_exact_ratio(self):
        asset = Path(__file__).parents[1] / "assets" / "shimento_logo.png"
        with Image.open(asset) as image:
            self.assertEqual(image.size, (938, 163))
            corner = image.convert("RGB").getpixel((0, 0))
        self.assertTrue(all(channel >= 245 for channel in corner))

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
            header = " ".join(
                paragraph.text
                for paragraph in document.sections[0].header.paragraphs
            )

        self.assertIn("Jane Doe", header)
        for expected in ("Summary:", "Technical Skills:", "Professional Experience:",
                         "Certifications:", "Education:", "Example Ltd", "2022 - Present"):
            self.assertIn(expected, body)
        self.assertTrue(all(p.paragraph_format.space_after.pt == 0
                            for p in document.paragraphs if p.paragraph_format.space_after))
        section = document.sections[0]
        self.assertAlmostEqual(section.page_width / 914400, 8.5, places=2)
        self.assertAlmostEqual(section.page_height / 914400, 11, places=2)
        self.assertGreaterEqual(section.top_margin / 914400, 0.8)
        self.assertLessEqual(section.header_distance / 914400, 0.25)

    def test_section_headings_are_times_new_roman_bold_italic(self):
        data = ResumeData(
            name="Jane Doe",
            summary=["Summary item"],
            skills=[SkillGroup("Languages", "Python")],
            experience=[Job(company="Example Ltd")],
            certifications=["Cloud Practitioner"],
            education=[Education("B.Tech", "Example University", "2022")],
        )
        with tempfile.TemporaryDirectory() as directory:
            output = render(data, Path(directory) / "resume.docx")
            document = Document(output)

        expected = {
            "Summary:", "Technical Skills:", "Professional Experience:",
            "Certifications:", "Education:",
        }
        headings = {paragraph.text: paragraph.runs[0] for paragraph in document.paragraphs
                    if paragraph.text in expected}
        self.assertEqual(set(headings), expected)
        for run in headings.values():
            self.assertTrue(run.bold)
            self.assertTrue(run.italic)
            self.assertEqual(run.font.name, "Times New Roman")

    def test_repeated_render_keeps_all_supported_resume_data(self):
        for iteration in range(1, 21):
            data = ResumeData(
                name=f"Candidate {iteration}",
                summary=[f"Summary {iteration}-{index}" for index in range(1, 6)],
                skills=[SkillGroup(f"Skill group {index}", f"Value {iteration}-{index}")
                        for index in range(1, 5)],
                experience=[Job(f"Company {index}", f"202{index} - Present",
                                f"Role {index}", f"Project {index}",
                                [f"Responsibility {iteration}-{index}-{bullet}"
                                 for bullet in range(1, 4)])
                            for index in range(1, 4)],
                certifications=[f"Certification {iteration}-{index}" for index in range(1, 3)],
                education=[Education(f"Degree {index}", f"University {index}", f"202{index}")
                           for index in range(1, 3)],
            )
            with tempfile.TemporaryDirectory() as directory:
                output = render(data, Path(directory) / "resume.docx")
                document = Document(output)
                text = "\n".join(paragraph.text for paragraph in document.paragraphs)

            expected = [*data.summary, *(group.values for group in data.skills),
                        *(job.company for job in data.experience),
                        *(bullet for job in data.experience for bullet in job.bullets),
                        *data.certifications, *(education.degree for education in data.education)]
            for value in expected:
                self.assertIn(value, text, f"iteration {iteration} lost {value!r}")

    def test_logo_is_right_aligned_in_every_generated_header(self):
        with tempfile.TemporaryDirectory() as directory:
            output = render(ResumeData(name="Header Check"), Path(directory) / "resume.docx")
            document = Document(output)
            section = document.sections[0]
            self.assertFalse(document.settings.odd_and_even_pages_header_footer)
            self.assertFalse(section.different_first_page_header_footer)
            header = section.header
            self.assertIn("Header Check", " ".join(p.text for p in header.paragraphs))
            picture_paragraphs = [p for p in header.paragraphs
                                  if p._p.xpath(".//a:blip")]
            self.assertEqual(len(picture_paragraphs), 1)
            self.assertEqual(picture_paragraphs[0].alignment,
                             WD_ALIGN_PARAGRAPH.LEFT)
            extent = picture_paragraphs[0]._p.xpath(".//wp:extent")[0]
            self.assertAlmostEqual(int(extent.get("cx")) / 914400, 1.56, places=2)

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
