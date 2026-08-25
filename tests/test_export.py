import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from core.export import PdfExportError, to_pdf


class ExportTests(unittest.TestCase):
    def test_replaces_stale_pdf_and_returns_verified_path(self):
        with tempfile.TemporaryDirectory() as directory:
            docx = Path(directory) / "resume.docx"
            pdf = docx.with_suffix(".pdf")
            docx.write_bytes(b"docx")
            pdf.write_bytes(b"stale")

            def convert(_docx, output):
                output.write_bytes(b"%PDF-1.4 fresh")

            with patch("core.export._available_converters",
                       return_value=[("test", convert, 2)]):
                result = to_pdf(docx)

            self.assertEqual(result, pdf)
            self.assertEqual(pdf.read_bytes(), b"%PDF-1.4 fresh")

    def test_reports_missing_converter_immediately(self):
        with tempfile.TemporaryDirectory() as directory:
            docx = Path(directory) / "resume.docx"
            docx.write_bytes(b"docx")
            with patch("core.export._available_converters", return_value=[]):
                with self.assertRaisesRegex(PdfExportError, "no PDF converter"):
                    to_pdf(docx)

    def test_rejects_zero_byte_pdf(self):
        with tempfile.TemporaryDirectory() as directory:
            docx = Path(directory) / "resume.docx"
            docx.write_bytes(b"docx")

            def convert(_docx, output):
                output.touch()

            with patch("core.export._available_converters",
                       return_value=[("test", convert, 2)]):
                with self.assertRaisesRegex(PdfExportError, "produced no file"):
                    to_pdf(docx)


if __name__ == "__main__":
    unittest.main()
