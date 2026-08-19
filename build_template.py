"""Regenerates templates/shimentox.docx from the client's sample resume.

Run only when the client changes their format. The generated file is the
formatting donor: styles, numbering, page setup, header and logo are reused
verbatim so output is byte-level faithful to what the client signed off on.
"""

import shutil
from pathlib import Path

from docx import Document
from docx.enum.text import WD_TAB_ALIGNMENT
from docx.oxml import parse_xml
from docx.oxml.ns import nsdecls, qn
from docx.shared import Twips

ROOT = Path(__file__).parent
SAMPLE = Path(r"C:\Users\jaanu\Downloads\Formatted Resume OG 1.docx")
OUT = ROOT / "templates" / "shimentox.docx"

# A4 (11906tw) minus 0.5in margins each side.
RIGHT_TAB_TWIPS = 10466


def main() -> None:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(SAMPLE, OUT)
    doc = Document(str(OUT))

    _rebuild_header(doc)
    _empty_body(doc)

    doc.save(str(OUT))
    print(f"wrote {OUT}")


def _rebuild_header(doc: Document) -> None:
    """Name on the left, logo hard against the right margin.

    The sample positioned the logo with a run of literal spaces, which drifts
    as soon as the candidate's name is a different length. A right-aligned tab
    pins it correctly for any name.
    """
    para = doc.sections[0].header.paragraphs[0]
    p = para._p

    drawing = p.find(".//" + qn("w:drawing"))
    if drawing is None:
        raise RuntimeError("logo drawing not found in sample header")

    # The sample's blip carries both an embedded copy and an external mail-cid
    # link; the external one resolves to nothing outside the original mailbox.
    blip = drawing.find(".//" + qn("a:blip"))
    if blip is not None and blip.get(qn("r:link")):
        del blip.attrib[qn("r:link")]

    for run in p.findall(qn("w:r")):
        p.remove(run)
    for pr in p.findall(qn("w:proofErr")):
        p.remove(pr)

    # Must go through python-docx's API rather than appending raw XML: OOXML
    # requires w:tabs to precede w:rPr inside w:pPr, and Word silently ignores
    # a misordered tab stop.
    tab_stops = para.paragraph_format.tab_stops
    tab_stops.clear_all()
    tab_stops.add_tab_stop(Twips(RIGHT_TAB_TWIPS), WD_TAB_ALIGNMENT.RIGHT)

    name_run = parse_xml(
        f'<w:r {nsdecls("w")}><w:rPr>'
        '<w:rFonts w:ascii="Times New Roman" w:hAnsi="Times New Roman" w:cs="Times New Roman"/>'
        '<w:b/><w:sz w:val="28"/><w:szCs w:val="28"/></w:rPr>'
        '<w:t xml:space="preserve"></w:t></w:r>'
    )
    tab_run = parse_xml(f'<w:r {nsdecls("w")}><w:tab/></w:r>')
    logo_run = parse_xml(f'<w:r {nsdecls("w")}><w:rPr><w:noProof/></w:rPr></w:r>')
    logo_run.append(drawing)

    p.append(name_run)
    p.append(tab_run)
    p.append(logo_run)


def _empty_body(doc: Document) -> None:
    body = doc.element.body
    for child in list(body):
        if child.tag != qn("w:sectPr"):
            body.remove(child)


if __name__ == "__main__":
    main()
