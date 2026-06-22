# ============================================================
# Word (.docx) export.
#
# Produces a clinician-ready, neuropsychological-report style document:
#   Page 1  title block, band legend, a compact percentile table (one
#           continuous table with shaded domain sections and domain-mean
#           rows) and the interpretive draft.
#   Page 2  the visual profile: every figure laid out on a single page.
#
# Arial throughout. Everything is built in memory and written only to the
# path the user picks. No template or patient data is persisted elsewhere.
# ============================================================

from __future__ import annotations

import io
from datetime import date
from typing import Optional

from docx import Document
from docx.enum.table import WD_ALIGN_VERTICAL, WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_TAB_ALIGNMENT
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Inches, Pt, RGBColor

from engine import ProfileResult, classify_band, format_percentile
from plots import (
    BAND_COLORS,
    band_index,
    close_fig,
    composite_figure,
    fig_to_png_bytes,
)

# --- 0. Palette and bilingual strings -------------------------

FONT = "Arial"
ACCENT_HEX = "2C7290"
ACCENT_DEEP = RGBColor(0x22, 0x5D, 0x77)
INK = RGBColor(0x1D, 0x2B, 0x33)
MUTED = RGBColor(0x6B, 0x77, 0x7E)
STRENGTH = RGBColor(0x1F, 0x7A, 0x63)
WEAKNESS = RGBColor(0x56, 0x58, 0xA6)
# Neutral grays for the table chrome (the band column is the only color).
HEADER_FILL = "E9ECEF"
DOMAIN_FILL = "F2F4F6"
MEAN_FILL = "F8F9FA"
RULE_FILL = "CED5DA"

_METRIC_LABEL = {
    "z": "z", "percentile": "%ile", "scaled": "scaled",
    "standard": "standard", "t": "T",
}

_MONTHS = {
    "fr": ["janvier", "février", "mars", "avril", "mai", "juin", "juillet",
           "août", "septembre", "octobre", "novembre", "décembre"],
    "en": ["January", "February", "March", "April", "May", "June", "July",
           "August", "September", "October", "November", "December"],
}

_STRINGS = {
    "fr": {
        "title": "PROFIL COGNITIF",
        "identifier": "Identifiant", "date": "Date",
        "personal_mean": "Moyenne propre (z)",
        "legend_title": "Bandes de classification",
        "table_title": "Tableau des percentiles",
        "figures_title": "Profil visuel",
        "draft_title": "Interprétation (brouillon)",
        "cols": ["Sous-fonction", "Score", "Percentile", "Bande", "Indicateur"],
        "domain_mean": "Moyenne du domaine",
        "strength": "▲ Force", "weakness": "▼ Faiblesse", "within": "–",
        "no_data": "Aucune mesure administrée.",
        "footer": ("Document généré localement. Brouillon à réviser et à valider "
                   "selon le jugement clinique."),
    },
    "en": {
        "title": "COGNITIVE PROFILE",
        "identifier": "Identifier", "date": "Date",
        "personal_mean": "Own average (z)",
        "legend_title": "Classification bands",
        "table_title": "Percentile table",
        "figures_title": "Visual profile",
        "draft_title": "Interpretation (draft)",
        "cols": ["Sub-function", "Score", "Percentile", "Band", "Indicator"],
        "domain_mean": "Domain mean",
        "strength": "▲ Strength", "weakness": "▼ Weakness", "within": "–",
        "no_data": "No measure administered.",
        "footer": ("Generated locally. Draft to be reviewed and validated with "
                   "clinical judgement."),
    },
}

# Column widths (sum ~6.9 inches inside 0.8 inch side margins on Letter).
_COLW = [Inches(2.7), Inches(1.05), Inches(0.95), Inches(1.5), Inches(0.7)]


def _today_str(lang: str) -> str:
    """Readable date without depending on the machine locale."""
    today = date.today()
    months = _MONTHS["fr"] if lang == "fr" else _MONTHS["en"]
    if lang == "fr":
        return f"{today.day} {months[today.month - 1]} {today.year}"
    return f"{months[today.month - 1]} {today.day}, {today.year}"


# --- 1. Low-level docx helpers --------------------------------

def _shade(cell, hex_color: str) -> None:
    """Apply a solid background fill to a table cell."""
    tc_pr = cell._tc.get_or_add_tcPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:color"), "auto")
    shd.set(qn("w:fill"), hex_color.lstrip("#"))
    tc_pr.append(shd)


def _run(paragraph, text, *, bold=False, size=10.0, color=None, italic=False):
    """Add a styled Arial run."""
    r = paragraph.add_run(text)
    r.font.name = FONT
    r.font.size = Pt(size)
    r.bold = bold
    r.italic = italic
    if color is not None:
        r.font.color.rgb = color
    return r


def _cell(cell, text, *, bold=False, size=9.0, color=INK, align="left",
          fill=None, valign="center") -> None:
    """Replace a cell's content with one styled run, tightly spaced."""
    cell.text = ""
    cell.vertical_alignment = {
        "center": WD_ALIGN_VERTICAL.CENTER, "top": WD_ALIGN_VERTICAL.TOP,
    }[valign]
    para = cell.paragraphs[0]
    para.alignment = {
        "left": WD_ALIGN_PARAGRAPH.LEFT, "center": WD_ALIGN_PARAGRAPH.CENTER,
        "right": WD_ALIGN_PARAGRAPH.RIGHT,
    }[align]
    para.paragraph_format.space_before = Pt(1)
    para.paragraph_format.space_after = Pt(1)
    _run(para, text, bold=bold, size=size, color=color)
    if fill:
        _shade(cell, fill)


def _compact_cell_margins(table, top=22, bottom=22, left=70, right=70) -> None:
    """Tighten table cell margins (twips) so rows stay compact."""
    tbl_pr = table._tbl.tblPr
    mar = OxmlElement("w:tblCellMar")
    for side, val in (("top", top), ("bottom", bottom),
                      ("left", left), ("right", right)):
        node = OxmlElement(f"w:{side}")
        node.set(qn("w:w"), str(val))
        node.set(qn("w:type"), "dxa")
        mar.append(node)
    tbl_pr.append(mar)


def _set_borders(table, color=RULE_FILL, size=4) -> None:
    """Give the table thin, light horizontal-and-vertical borders."""
    tbl_pr = table._tbl.tblPr
    borders = OxmlElement("w:tblBorders")
    for edge in ("top", "left", "bottom", "right", "insideH", "insideV"):
        node = OxmlElement(f"w:{edge}")
        node.set(qn("w:val"), "single")
        node.set(qn("w:sz"), str(size))
        node.set(qn("w:space"), "0")
        node.set(qn("w:color"), color)
        borders.append(node)
    tbl_pr.append(borders)


def _rule(paragraph, color=ACCENT_HEX, size=14) -> None:
    """Add a colored bottom border (a horizontal rule) to a paragraph."""
    p_pr = paragraph._p.get_or_add_pPr()
    borders = OxmlElement("w:pBdr")
    bottom = OxmlElement("w:bottom")
    bottom.set(qn("w:val"), "single")
    bottom.set(qn("w:sz"), str(size))
    bottom.set(qn("w:space"), "4")
    bottom.set(qn("w:color"), color)
    borders.append(bottom)
    p_pr.append(borders)


def _page_field(paragraph) -> None:
    """Insert a live PAGE number field."""
    run = paragraph.add_run()
    for kind, txt in (("begin", None), (None, "PAGE"), ("end", None)):
        if kind:
            fld = OxmlElement("w:fldChar")
            fld.set(qn("w:fldCharType"), kind)
            run._r.append(fld)
        else:
            instr = OxmlElement("w:instrText")
            instr.set(qn("xml:space"), "preserve")
            instr.text = txt
            run._r.append(instr)


def _heading(doc, text, *, size=12.5, rule=False, space_before=10) -> None:
    """A styled section heading in the accent color."""
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(space_before)
    p.paragraph_format.space_after = Pt(4)
    _run(p, text, bold=True, size=size, color=ACCENT_DEEP)
    if rule:
        _rule(p, color=ACCENT_HEX, size=8)


def _add_centered_image(doc, png_bytes, width_in) -> None:
    para = doc.add_paragraph()
    para.alignment = WD_ALIGN_PARAGRAPH.CENTER
    para.paragraph_format.space_before = Pt(2)
    para.paragraph_format.space_after = Pt(2)
    para.add_run().add_picture(io.BytesIO(png_bytes), width=Inches(width_in))


# --- 2. Page sections -----------------------------------------

def _title_block(doc, s, patient_id, lang) -> None:
    title = doc.add_paragraph()
    title.paragraph_format.space_after = Pt(2)
    _run(title, s["title"], bold=True, size=20, color=ACCENT_DEEP)
    _rule(title, color=ACCENT_HEX, size=18)

    info = doc.add_paragraph()
    info.paragraph_format.space_before = Pt(4)
    info.paragraph_format.space_after = Pt(6)
    _run(info, f"{s['identifier']} ", bold=True, size=10, color=MUTED)
    _run(info, f"{patient_id or '-'}  ", size=10, color=INK)
    _run(info, f"{s['date']} ", bold=True, size=10, color=MUTED)
    _run(info, f"{_today_str(lang)}", size=10, color=INK)


def _legend(doc, s, lang) -> None:
    _heading(doc, s["legend_title"], size=10.5, space_before=2)
    labels_fr = ["Extr. bas", "Limite", "Moy. inf.", "Moyenne",
                 "Moy. sup.", "Supérieur", "Très sup."]
    labels_en = ["Extr. low", "Borderline", "Low avg", "Average",
                 "High avg", "Superior", "Very sup."]
    labels = labels_fr if lang == "fr" else labels_en
    table = doc.add_table(rows=1, cols=7)
    table.alignment = WD_TABLE_ALIGNMENT.LEFT
    _compact_cell_margins(table, top=14, bottom=14, left=40, right=40)
    for i, cell in enumerate(table.rows[0].cells):
        _cell(cell, labels[i], size=7, align="center", fill=BAND_COLORS[i])
        cell.width = Inches(0.98)


def _table(doc, s, profile, inputs, lang) -> None:
    _heading(doc, s["table_title"], size=12, rule=True)
    table = doc.add_table(rows=1, cols=5)
    table.alignment = WD_TABLE_ALIGNMENT.LEFT
    table.autofit = False
    _set_borders(table)
    _compact_cell_margins(table)

    # Header row (neutral gray, dark text).
    for i, label in enumerate(s["cols"]):
        align = "left" if i == 0 else "center"
        _cell(table.rows[0].cells[i], label, bold=True, size=8.5, color=INK,
              align=align, fill=HEADER_FILL)
        table.rows[0].cells[i].width = _COLW[i]

    any_data = False
    for di, dom in enumerate(profile.domains):
        if not dom.measures:
            continue
        any_data = True

        # Domain section row (merged, neutral gray).
        drow = table.add_row()
        merged = drow.cells[0].merge(drow.cells[4])
        _cell(merged, dom.name(lang), bold=True, size=9, color=INK,
              fill=DOMAIN_FILL)

        for mi, m in enumerate(dom.measures):
            cells = table.add_row().cells
            entered = ""
            if di < len(inputs) and mi < len(inputs[di]):
                raw = inputs[di][mi]
                metric = _METRIC_LABEL.get(str(raw.get("metric", "")).lower(),
                                           str(raw.get("metric", "")))
                entered = f"{raw.get('value', '')} ({metric})".strip()
            _cell(cells[0], m.name(lang), size=9)
            _cell(cells[1], entered, size=9, align="center")
            _cell(cells[2], m.percentile_display, size=9, align="center", bold=True)
            _cell(cells[3], m.band(lang), size=8.5,
                  fill=BAND_COLORS[band_index(m.percentile)])
            marker = {"strength": s["strength"], "weakness": s["weakness"],
                      "within": s["within"]}[m.flag]
            mcolor = {"strength": STRENGTH, "weakness": WEAKNESS,
                      "within": MUTED}[m.flag]
            _cell(cells[4], marker, size=8, align="center", color=mcolor)
            for i in range(5):
                cells[i].width = _COLW[i]

        # Domain-mean row.
        if dom.mean_percentile is not None:
            cells = table.add_row().cells
            _cell(cells[0], s["domain_mean"], bold=True, size=8.5, fill=MEAN_FILL)
            _cell(cells[1], "", size=8.5, fill=MEAN_FILL)
            _cell(cells[2], format_percentile(dom.mean_percentile), bold=True,
                  size=8.5, align="center", fill=MEAN_FILL)
            band_fr, band_en = classify_band(dom.mean_percentile)
            _cell(cells[3], band_fr if lang == "fr" else band_en, bold=True,
                  size=8.5, fill=BAND_COLORS[band_index(dom.mean_percentile)])
            _cell(cells[4], "", size=8.5, fill=MEAN_FILL)
            for i in range(5):
                cells[i].width = _COLW[i]

    if not any_data:
        doc.add_paragraph(s["no_data"])


def _interpretation(doc, s, draft_text, lang) -> None:
    _heading(doc, s["draft_title"], size=12, rule=True)
    lines = [ln for ln in (draft_text or "").split("\n")]
    first = True
    for line in lines:
        if line.strip() == "":
            continue
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
        p.paragraph_format.space_after = Pt(5)
        if first:
            _run(p, line, size=9, italic=True, color=MUTED)
            first = False
        else:
            _run(p, line, size=10.5, color=INK)


def _footer(doc, s) -> None:
    footer = doc.sections[0].footer
    p = footer.paragraphs[0]
    p.text = ""
    p.paragraph_format.tab_stops.add_tab_stop(Inches(6.9), WD_TAB_ALIGNMENT.RIGHT)
    _run(p, s["footer"], italic=True, size=7.5, color=MUTED)
    _run(p, "\t", size=7.5)
    _page_field(p)


# --- 3. Document assembly -------------------------------------

def build_document(profile: ProfileResult,
                   inputs: list[list[dict]],
                   draft_text: str,
                   patient_id: str,
                   lang: str = "fr",
                   options: Optional[dict] = None) -> Document:
    """Build and return the full report as a python-docx Document."""
    options = options or {}
    radial_mode = options.get("radial_mode", "z")
    show_summary = options.get("show_summary", True)
    s = _STRINGS["fr"] if lang == "fr" else _STRINGS["en"]

    doc = Document()
    normal = doc.styles["Normal"]
    normal.font.name = FONT
    normal.font.size = Pt(10.5)
    normal.font.color.rgb = INK

    sec = doc.sections[0]
    sec.page_height = Inches(11)
    sec.page_width = Inches(8.5)
    sec.top_margin = Inches(0.7)
    sec.bottom_margin = Inches(0.65)
    sec.left_margin = Inches(0.8)
    sec.right_margin = Inches(0.8)

    # --- Page 1: clinical content ---
    _title_block(doc, s, patient_id, lang)
    _legend(doc, s, lang)
    _table(doc, s, profile, inputs, lang)
    _interpretation(doc, s, draft_text, lang)
    _footer(doc, s)

    # --- Page 2: visual profile (every figure on one page) ---
    any_data = any(d.measures for d in profile.domains)
    if any_data:
        doc.add_page_break()
        _heading(doc, s["figures_title"], size=13, rule=True, space_before=0)
        fig = composite_figure(profile, lang, radial_mode, show_summary)
        fig_w, fig_h = fig.get_size_inches()
        # Keep the whole grid on one page: never taller than the usable area.
        width_in = min(6.7, 8.6 * fig_w / fig_h)
        _add_centered_image(doc, fig_to_png_bytes(fig, dpi=300), width_in)
        close_fig(fig)

    return doc


def export_report(path: str,
                  profile: ProfileResult,
                  inputs: list[list[dict]],
                  draft_text: str,
                  patient_id: str,
                  lang: str = "fr",
                  options: Optional[dict] = None) -> str:
    """Build the document and save it to path. Returns the path."""
    doc = build_document(profile, inputs, draft_text, patient_id, lang, options)
    doc.save(path)
    return path


# --- 4. Manual smoke test ------------------------------------

if __name__ == "__main__":
    import tempfile
    from engine import (DomainInput, MeasureInput, generate_report_text,
                        process_profile)

    demo = [
        DomainInput("Attention / Vitesse", "Attention / Speed", [
            MeasureInput("Soutenue", "Sustained", 8, "scaled"),
            MeasureInput("Sélective", "Selective", 50, "t"),
            MeasureInput("Divisée", "Divided", 5, "percentile"),
            MeasureInput("Vigilance", "Vigilance", -0.5, "z"),
        ]),
        DomainInput("Mémoire", "Memory", [
            MeasureInput("À court terme", "Short-term", 25, "percentile"),
            MeasureInput("À long terme", "Long-term", 1.5, "z"),
        ]),
    ]
    profile = process_profile(demo, "DEMO-01", 1.0)
    inputs = [
        [{"value": "8", "metric": "scaled"}, {"value": "50", "metric": "t"},
         {"value": "5", "metric": "percentile"}, {"value": "-0.5", "metric": "z"}],
        [{"value": "25", "metric": "percentile"}, {"value": "1.5", "metric": "z"}],
    ]
    draft = generate_report_text(profile, "fr")
    out = export_report(tempfile.mktemp(suffix=".docx"), profile, inputs,
                        draft, "DEMO-01", "fr", {"radial_mode": "z"})
    print("Wrote", out)
