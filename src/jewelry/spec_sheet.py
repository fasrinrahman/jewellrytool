"""One-page jeweler spec sheet (FR-10, NFR-03, NFR-04)."""
import datetime
from pathlib import Path
from xml.sax.saxutils import escape
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import KeepInFrame, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
from .engine import seat_depth_mm
from .numbers import DesignNumbers
from .params import RingParams
from .report import Report
from .sizes import ring_sizes

STATUS_TEXT = {"pass": "PASS", "warn": "WARN", "fail": "FAIL", "unverified": "NOT CHECKED"}


def _name(metal: str) -> str:
    return metal.replace("_", " ")


def spec_sheet_data(p: RingParams, report: Report, n: DesignNumbers, rules: dict,
                    today: datetime.date = None) -> dict:
    today = today or datetime.date.today()
    try:
        s = ring_sizes(p.ring_size_mm)
        size_rows = [("Inner diameter", f"{s['mm']:g} mm"), ("US size", f"{s['us']:g}"),
                     ("UK size (approximate)", s["uk"]), ("EU size", f"{s['eu']}")]
    except ValueError:
        size_rows = [("Inner diameter", f"{p.ring_size_mm:g} mm"),
                     ("US, UK and EU sizes", "outside the supported conversion range")]
    outer = p.ring_size_mm + 2 * p.band_thickness_mm
    return {
        "date": today.isoformat(),
        "exportable": report.exportable,
        "Ring": [("Type", "Solitaire ring"), ("Metal", _name(p.metal)), ("Finish", p.finish)],
        "Ring size": size_rows,
        "Dimensions": [
            ("Outer diameter", f"{outer:g} mm"),
            ("Band width", f"{p.band_width_mm:g} mm"),
            ("Band thickness", f"{p.band_thickness_mm:g} mm"),
            ("Stone", f"{p.stone_shape}, {p.stone_size_mm:g} mm"),
            ("Seat depth", f"{seat_depth_mm(p.stone_shape, p.stone_size_mm):.2f} mm (from the stone)"),
            ("Prongs", f"{p.prong_count} prongs, {p.prong_diameter_mm:g} mm thick"),
        ],
        "Weight and cost": [
            ("Metal weight", f"{n.weight_g:.2f} g"),
            ("Metal cost range", n.cost_text()),
        ],
        "validation": [(STATUS_TEXT[r.status], r.message) for r in report.results],
        "assumptions": [
            f"Weight uses a density of {n.density_g_cm3:g} g/cm3 for {_name(p.metal)}.",
            f"Prices: {n.price_source}, as of {n.price_as_of}."
            + ("" if n.prices_verified else " These prices have not been verified."),
            "Design rules reviewed by a jeweler: " + ("yes." if rules.get("verified_by_jeweler") else "no."),
            "This sheet supports the jeweler's decision. It does not replace a human check before casting.",
        ],
    }


def build_spec_sheet(p: RingParams, report: Report, n: DesignNumbers, rules: dict,
                     path, today: datetime.date = None) -> Path:
    d = spec_sheet_data(p, report, n, rules, today)
    base = getSampleStyleSheet()
    body = ParagraphStyle("body", parent=base["Normal"], fontName="Helvetica", fontSize=9, leading=11)
    head = ParagraphStyle("head", parent=base["Normal"], fontName="Helvetica-Bold", fontSize=11,
                          leading=13, spaceBefore=8, spaceAfter=3)
    title = ParagraphStyle("title", parent=base["Normal"], fontName="Helvetica-Bold", fontSize=17, leading=20)
    small = ParagraphStyle("small", parent=body, fontSize=8, leading=10, textColor=colors.HexColor("#444444"))
    grid = TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"),
                       ("LINEBELOW", (0, 0), (-1, -1), 0.25, colors.HexColor("#CCCCCC")),
                       ("TOPPADDING", (0, 0), (-1, -1), 2), ("BOTTOMPADDING", (0, 0), (-1, -1), 2)])

    story = [Paragraph("Ring spec sheet", title),
             Paragraph(f"Generated {d['date']}", small)]
    for section in ("Ring", "Ring size", "Dimensions", "Weight and cost"):
        story.append(Paragraph(section, head))
        rows = [[Paragraph(f"<b>{escape(k)}</b>", body), Paragraph(escape(v), body)] for k, v in d[section]]
        t = Table(rows, colWidths=[44 * mm, 130 * mm])
        t.setStyle(grid)
        story.append(t)
    story.append(Paragraph("Validation results", head))
    rows = [[Paragraph(f"<b>{s}</b>", body), Paragraph(escape(m), body)] for s, m in d["validation"]]
    t = Table(rows, colWidths=[24 * mm, 150 * mm])
    t.setStyle(grid)
    story.append(t)
    story.append(Paragraph("Assumptions", head))
    for line in d["assumptions"]:
        story.append(Paragraph(escape(line), small))
        story.append(Spacer(1, 1.5))

    doc = SimpleDocTemplate(str(path), pagesize=A4, leftMargin=15 * mm, rightMargin=15 * mm,
                            topMargin=13 * mm, bottomMargin=13 * mm, title="Ring spec sheet")
    # Shrink to fit so the sheet is always exactly one page, even with a long report (FR-10).
    one_page = KeepInFrame(doc.width - 12, doc.height - 12, story, mode="shrink")
    doc.build([one_page])
    return Path(path)
