"""DOCX to PDF conversion using whatever the recruiter already has installed.

Drives Word over COM directly rather than via docx2pdf: that library writes a
progress bar to stdout, which is None in a windowed PyInstaller build.
"""

import os
import shutil
import subprocess
import tempfile
from pathlib import Path

WD_FORMAT_PDF = 17


class PdfExportError(Exception):
    pass


def to_pdf(docx_path: Path) -> Path:
    docx_path = Path(docx_path).resolve()
    pdf_path = docx_path.with_suffix(".pdf")

    if not docx_path.exists():
        raise PdfExportError(f"Word document not found: {docx_path}")

    # Never mistake a PDF from an older export for the result of this run.
    pdf_path.unlink(missing_ok=True)

    converters = _available_converters()
    if not converters:
        raise PdfExportError(
            "The Word document was created successfully, but no PDF converter "
            "was found. Install Microsoft Word (Windows) or LibreOffice, then retry."
        )

    errors = []
    for name, attempt, timeout in converters:
        try:
            _run_guarded(attempt, docx_path, pdf_path, timeout=timeout)
            if pdf_path.exists() and pdf_path.stat().st_size > 0:
                return pdf_path
            errors.append(f"{name}: produced no file")
        except Exception as exc:
            errors.append(f"{name}: {exc}")

    raise PdfExportError(
        "The Word document was created successfully, but PDF conversion failed.\n\n"
        "PDF export needs Microsoft Word (Windows) or LibreOffice installed.\n"
        "You can still open the .docx and use File > Save as PDF.\n\n"
        "Details:\n" + "\n".join(errors)
    )


def _available_converters():
    """Return only converters that can actually run on this computer.

    Skipping unavailable backends avoids waiting for imports/process startup that
    can never succeed. Word is preferred on Windows because it preserves the
    client's template most accurately.
    """
    converters = []
    if os.name == "nt":
        try:
            import pythoncom  # noqa: F401
            import win32com.client  # noqa: F401
        except ImportError:
            pass
        else:
            converters.append(("Microsoft Word", _via_word, 35))
    if _find_soffice():
        converters.append(("LibreOffice", _via_libreoffice, 60))
    return converters


def _run_guarded(fn, docx_path: Path, pdf_path: Path, timeout: int) -> None:
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
        doc.ExportAsFixedFormat(str(pdf_path), WD_FORMAT_PDF)
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


def _find_soffice() -> str | None:
    soffice = shutil.which("soffice") or shutil.which("soffice.exe")
    if not soffice:
        for candidate in (
            r"C:\Program Files\LibreOffice\program\soffice.exe",
            r"C:\Program Files (x86)\LibreOffice\program\soffice.exe",
        ):
            if Path(candidate).exists():
                soffice = candidate
                break
    return soffice


def _via_libreoffice(docx_path: Path, pdf_path: Path) -> None:
    soffice = _find_soffice()
    if not soffice:
        raise FileNotFoundError("LibreOffice not installed")

    # A private profile prevents an already-running LibreOffice instance from
    # swallowing the command or blocking on its user-profile lock.
    with tempfile.TemporaryDirectory(prefix="resume-pdf-") as profile:
        result = subprocess.run(
            [soffice, "--headless", f"-env:UserInstallation={Path(profile).as_uri()}",
             "--convert-to", "pdf", "--outdir", str(pdf_path.parent), str(docx_path)],
            check=True,
            capture_output=True,
            text=True,
            timeout=55,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
    if not pdf_path.exists():
        detail = (result.stderr or result.stdout).strip()
        raise RuntimeError(detail or "conversion completed without creating a PDF")
