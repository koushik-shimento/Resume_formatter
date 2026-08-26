from io import BytesIO
from zipfile import ZipFile
import unittest

from web_app import bundle_outputs, parse_upload


class WebAppTests(unittest.TestCase):
    def test_parse_text_upload_retains_supported_sections(self):
        data = parse_upload(
            "Jane_Doe.txt",
            b"Jane Doe\nSummary\nReliable engineer\nSkills\nPython: FastAPI\nEducation\nBSc | Example University | 2022",
        )
        self.assertTrue(data.name)
        self.assertIn("Reliable engineer", data.summary)
        self.assertTrue(data.skills)
        self.assertTrue(data.education)

    def test_parse_upload_rejects_unsupported_files(self):
        with self.assertRaisesRegex(ValueError, "Unsupported file type"):
            parse_upload("resume.exe", b"data")

    def test_bundle_contains_both_exports(self):
        result = bundle_outputs("resume.docx", b"docx", "resume.pdf", b"pdf")
        with ZipFile(BytesIO(result)) as archive:
            self.assertEqual(archive.namelist(), ["resume.docx", "resume.pdf"])
            self.assertEqual(archive.read("resume.docx"), b"docx")
            self.assertEqual(archive.read("resume.pdf"), b"pdf")


if __name__ == "__main__":
    unittest.main()
