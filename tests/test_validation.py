import unittest

from core.extract import Line
from core.model import Job, ResumeData
from core.validation import validate


class ValidationTests(unittest.TestCase):
    def test_accepts_complete_title_company_headers(self):
        source = [Line("AI Developer | LinkedERP Jun 2026 - Present"), Line("Built the platform", is_bullet=True)]
        data = ResumeData(name="Candidate", summary=["Engineer"], experience=[Job("LinkedERP", "Jun 2026 - Present", "AI Developer", bullets=["Built the platform"])])
        self.assertEqual(validate(data, source)[0], [])

    def test_blocks_unsplit_or_incomplete_roles(self):
        data = ResumeData(name="Candidate", summary=["Engineer"], experience=[Job("", "2022 - Present", "Engineer | Example Ltd", bullets=["Built APIs"])])
        errors, _ = validate(data)
        self.assertTrue(any("unsplit" in error for error in errors))
        self.assertTrue(any("no company" in error for error in errors))

    def test_blocks_large_source_text_loss(self):
        source = [Line("Critical architecture migration delivery outcome " * 8)]
        data = ResumeData(name="Candidate", summary=["Engineer"])
        errors, _ = validate(data, source)
        self.assertTrue(any("source text" in error for error in errors))


if __name__ == "__main__":
    unittest.main()
