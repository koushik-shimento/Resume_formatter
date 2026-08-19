"""DOCX to PDF conversion using whatever the recruiter already has installed.

Drives Word over COM directly rather than via docx2pdf: that library writes a
progress bar to stdout, which is None in a windowed PyInstaller build.
"""

import shutil
import subprocess
from pathlib import Path

WD_FORMAT_PDF = 17


class PdfExportError(Exception):
    pass


def to_pdf(docx_path: Path) -> Path:
    docx_path = Path(docx_path).resolve()
    pdf_path = docx_path.with_suffix(".pdf")

    errors = []
    for attempt in (_via_word, _via_libreoffice):
        try:
            _run_guarded(attempt, docx_path, pdf_path)
            if pdf_path.exists():
                return pdf_path
            errors.append(f"{attempt.__name__.lstrip('_')}: produced no file")
        except Exception as exc:
            errors.append(f"{attempt.__name__.lstrip('_')}: {exc}")

    raise PdfExportError(
        "The Word document was created successfully, but PDF conversion failed.\n\n"
        "PDF export needs Microsoft Word or LibreOffice installed.\n"
        "You can still open the .docx and use File > Save as PDF.\n\n"
        "Details:\n" + "\n".join(errors)
    )


def _run_guarded(fn, docx_path: Path, pdf_path: Path, timeout: int = 120) -> None:
    """Office automation can block forever on an invisible modal dialog, so
    never let a stuck converter freeze the app."""
    import threading

    result: list = []

    def target() -> None:
        try:
            fn(docx_path, pdf_path)
            result.append(None)
        except Exception as exc:
            result.append(exc)

    thread = threading.Thread(target=target, daemon=True)
    thread.start()
    thread.join(timeout)
    if thread.is_alive():
        raise TimeoutError(
            f"timed out after {timeout}s (Word may be showing a dialog; "
            "close any open Word windows and retry)"
        )
    if result and isinstance(result[0], Exception):
        raise result[0]


def _via_word(docx_path: Path, pdf_path: Path) -> None:
    import pythoncom
    import win32com.client

    pythoncom.CoInitialize()
    word = None
    doc = None
    try:
        # DispatchEx gets a private instance so we never disturb, or get blocked
        # by, a document the recruiter already has open.
        word = win32com.client.DispatchEx("Word.Application")
        word.Visible = False
        word.DisplayAlerts = 0
        doc = word.Documents.Open(
            str(docx_path), ReadOnly=True, AddToRecentFiles=False, Visible=False
        )
        doc.SaveAs(str(pdf_path), FileFormat=WD_FORMAT_PDF)
    finally:
        if doc is not None:
            try:
                doc.Close(False)
            except Exception:
                pass
        if word is not None:
            try:
                word.Quit()
            except Exception:
                pass
        pythoncom.CoUninitialize()


def _via_libreoffice(docx_path: Path, pdf_path: Path) -> None:
    soffice = shutil.which("soffice") or shutil.which("soffice.exe")
    if not soffice:
        for candidate in (
            r"C:\Program Files\LibreOffice\program\soffice.exe",
            r"C:\Program Files (x86)\LibreOffice\program\soffice.exe",
        ):
            if Path(candidate).exists():
                soffice = candidate
                break
    if not soffice:
        raise FileNotFoundError("LibreOffice not installed")

    subprocess.run(
        [soffice, "--headless", "--convert-to", "pdf", "--outdir",
         str(pdf_path.parent), str(docx_path)],
        check=True,
        capture_output=True,
        timeout=180,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    )
