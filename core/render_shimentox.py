"""Renders ResumeData into the ShimentoX client format.

All formatting (page size, styles, bullet numbering, header logo) is inherited
from templates/shimentox.docx, which is the client's own sample with its body
emptied. This module only lays out content.
"""

import shutil
from pathlib import Path

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_LINE_SPACING, WD_TAB_ALIGNMENT
from docx.oxml import parse_xml
from docx.oxml.ns import nsdecls, qn
from docx.shared import Emu, Pt, Twips

from .model import ResumeData

FONT = "Times New Roman"
SIZE = Pt(10)
BULLET_NUM_ID = 4  # the Symbol-bullet list defined in the donor template
BULLET_INDENT_TWIPS = 144

DISPLAY_NAME = "ShimentoX"


def template_path() -> Path:
    from .paths import resource

    return resource("templates/shimentox.docx")


def render(data: ResumeData, out_path: Path) -> Path:
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(template_path(), out_path)

    doc = Document(str(out_path))
    _set_header_name(doc, data.name)

    if data.summary:
        _heading(doc, "Summary:")
        for item in data.summary:
            _run(_para(doc, bullet=True), item)
        _blank(doc)

    if data.skills:
        _heading(doc, "Technical Skills:")
        for group in data.skills:
            p = _para(doc, bullet=True)
            if group.category:
                _run(p, f"{group.category}:", bold=True)
                _run(p, f" {group.values}")
            else:
                _run(p, group.values)
        _blank(doc)

    if data.experience:
        _heading(doc, "Professional Experience:")
        for job in data.experience:
            p = _para(doc, right_tab=True, keep_with_next=True)
            _run(p, job.company, bold=True)
            if job.dates:
                _run(p, "\t", bold=True)
                _run(p, job.dates, bold=True, italic=True)
            if job.title:
                _run(_para(doc), job.title, bold=True, italic=True)
            if job.project:
                pp = _para(doc)
                _run(pp, "Project: ", bold=True, italic=True)
                _run(pp, job.project, italic=True)
            if job.bullets:
                _run(_para(doc), "Responsibilities:", bold=True, italic=True)
                for bullet in job.bullets:
                    _run(_para(doc, bullet=True), bullet)
            _blank(doc)

    if data.certifications:
        _heading(doc, "Certifications:")
        for cert in data.certifications:
            _run(_para(doc, bullet=True), cert)
        _blank(doc)

    if data.education:
        _heading(doc, "Education:")
        for edu in data.education:
            p = _para(doc, right_tab=True)
            label = ", ".join(x for x in (edu.degree, edu.institution) if x)
            _run(p, label)
            if edu.year:
                _run(p, "\t")
                _run(p, edu.year, bold=True, italic=True)

    doc.save(str(out_path))
    return out_path


def _set_header_name(doc: Document, name: str) -> None:
    para = doc.sections[0].header.paragraphs[0]
    runs = para._p.findall(qn("w:r"))
    if not runs:
        return
    t = runs[0].find(qn("w:t"))
    if t is None:
        t = parse_xml(f'<w:t {nsdecls("w")} xml:space="preserve"></w:t>')
        runs[0].append(t)
    t.text = name
    t.set(qn("xml:space"), "preserve")


def _para(
    doc: Document,
    bullet: bool = False,
    right_tab: bool = False,
    keep_with_next: bool = False,
):
    p = doc.add_paragraph(style="No Spacing")
    # Full justification creates visibly stretched headings and short bullets.
    # The client sample uses a clean left-aligned resume body.
    p.alignment = WD_ALIGN_PARAGRAPH.LEFT
    p.paragraph_format.space_before = Pt(0)
    p.paragraph_format.space_after = Pt(0)
    p.paragraph_format.line_spacing_rule = WD_LINE_SPACING.SINGLE
    p.paragraph_format.keep_with_next = keep_with_next
    p.paragraph_format.widow_control = True
    if bullet:
        pPr = p._p.get_or_add_pPr()
        pPr.append(parse_xml(
            f'<w:numPr {nsdecls("w")}><w:ilvl w:val="0"/>'
            f'<w:numId w:val="{BULLET_NUM_ID}"/></w:numPr>'
        ))
        p.paragraph_format.left_indent = Twips(BULLET_INDENT_TWIPS)
    if right_tab:
        section = doc.sections[-1]
        right_edge = section.page_width - section.left_margin - section.right_margin
        p.paragraph_format.tab_stops.add_tab_stop(
            Emu(right_edge), WD_TAB_ALIGNMENT.RIGHT
        )
    return p


def _blank(doc: Document) -> None:
    _para(doc)


def _heading(doc: Document, text: str) -> None:
    _run(_para(doc, keep_with_next=True), text, bold=True)


def _run(p, text: str, bold: bool = False, italic: bool = False):
    r = p.add_run(text)
    r.font.name = FONT
    r.font.size = SIZE
    r.bold = bold
    r.italic = italic
    # python-docx sets ascii/hAnsi only; complex-script needs setting by hand or
    # Word falls back to the theme font for any non-Latin character.
    rPr = r._r.get_or_add_rPr()
    rFonts = rPr.find(qn("w:rFonts"))
    if rFonts is None:
        rFonts = parse_xml(f'<w:rFonts {nsdecls("w")}/>')
        rPr.insert(0, rFonts)
    rFonts.set(qn("w:cs"), FONT)
    return r
