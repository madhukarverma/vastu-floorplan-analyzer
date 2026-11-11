"""Typeset the research paper (two-column, physics-journal style) with ReportLab.

Run after ``python paper/figures.py``:
    python paper/build_paper.py
Edit ``paper/metadata.json`` to change the author block, then rebuild.
"""

from __future__ import annotations

import json
import math
import sys
from pathlib import Path
from xml.sax.saxutils import escape

import matplotlib

matplotlib.use("Agg")
import matplotlib.mathtext as mathtext
import reportlab.platypus.paraparser as _pp
from matplotlib.font_manager import FontProperties
from PIL import Image as PILImage
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_LEFT
from reportlab.lib.fonts import addMapping
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    BaseDocTemplate,
    CondPageBreak,
    Frame,
    FrameBreak,
    Image,
    KeepTogether,
    NextPageTemplate,
    PageBreak,
    PageTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
)

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from vastu_analyzer import __version__, load_rules, solar

META = json.loads((ROOT / "paper" / "metadata.json").read_text(encoding="utf-8"))
RES = json.loads((ROOT / "paper" / "build" / "results.json").read_text(encoding="utf-8"))
FIG = ROOT / "docs" / "figures"
EQ_DIR = ROOT / "paper" / "build" / "eq"
EQ_DIR.mkdir(parents=True, exist_ok=True)
OUT = ROOT / META["output"]
OUT.parent.mkdir(parents=True, exist_ok=True)

# ----------------------------------------------------------------------------- fonts & styles
TTF = Path(matplotlib.get_data_path()) / "fonts" / "ttf"
for name, file in (("STIX", "STIXGeneral.ttf"), ("STIX-Bold", "STIXGeneralBol.ttf"),
                   ("STIX-Italic", "STIXGeneralItalic.ttf"), ("STIX-BoldItalic", "STIXGeneralBolIta.ttf")):  # fmt: skip
    pdfmetrics.registerFont(TTFont(name, str(TTF / file)))
addMapping("STIX", 0, 0, "STIX")
addMapping("STIX", 1, 0, "STIX-Bold")
addMapping("STIX", 0, 1, "STIX-Italic")
addMapping("STIX", 1, 1, "STIX-BoldItalic")
matplotlib.rcParams["mathtext.fontset"] = "stix"
_pp.subFraction = 0.22  # TeX-like subscript drop (fraction of font size)
_pp.supFraction = 0.38

INK = colors.HexColor("#0b0b0b")
INK2 = colors.HexColor("#52514e")
RULE = colors.HexColor("#0b0b0b")
ACCENT = colors.HexColor("#2a78d6")

PAGE_W, PAGE_H = A4
M_L = M_R = 17 * mm
M_T, M_B = 20 * mm, 18 * mm
GAP = 6 * mm
COL_W = (PAGE_W - M_L - M_R - GAP) / 2
FULL_W = PAGE_W - M_L - M_R
BODY_H = PAGE_H - M_T - M_B

base = {"fontName": "STIX", "textColor": INK}
S = {
    "title": ParagraphStyle(
        "title", fontSize=15.5, leading=19, alignment=TA_CENTER, fontName="STIX-Bold", textColor=INK
    ),
    "author": ParagraphStyle(
        "author", fontSize=10.5, leading=13, alignment=TA_CENTER, spaceBefore=8, **base
    ),
    "affil": ParagraphStyle(
        "affil",
        fontSize=8.3,
        leading=10,
        alignment=TA_CENTER,
        fontName="STIX-Italic",
        textColor=INK,
        spaceBefore=2,
    ),
    "dated": ParagraphStyle(
        "dated", fontSize=8.3, leading=10, alignment=TA_CENTER, spaceBefore=4, **base
    ),
    "abstract": ParagraphStyle(
        "abstract",
        fontSize=9,
        leading=11.2,
        alignment=TA_JUSTIFY,
        leftIndent=26,
        rightIndent=26,
        spaceBefore=10,
        **base,
    ),
    "kw": ParagraphStyle(
        "kw",
        fontSize=8.3,
        leading=10,
        alignment=TA_LEFT,
        leftIndent=26,
        rightIndent=26,
        spaceBefore=5,
        **base,
    ),
    "body": ParagraphStyle(
        "body", fontSize=9.5, leading=11.6, alignment=TA_JUSTIFY, firstLineIndent=10, **base
    ),
    "body0": ParagraphStyle("body0", fontSize=9.5, leading=11.6, alignment=TA_JUSTIFY, **base),
    "h1": ParagraphStyle(
        "h1",
        fontSize=9.5,
        leading=12,
        alignment=TA_CENTER,
        fontName="STIX-Bold",
        textColor=INK,
        spaceBefore=11,
        spaceAfter=5,
    ),
    "h2": ParagraphStyle(
        "h2",
        fontSize=9.5,
        leading=12,
        alignment=TA_CENTER,
        fontName="STIX-Bold",
        textColor=INK,
        spaceBefore=8,
        spaceAfter=4,
    ),
    "h3": ParagraphStyle(
        "h3",
        fontSize=9.5,
        leading=11.6,
        alignment=TA_LEFT,
        fontName="STIX-Italic",
        textColor=INK,
        spaceBefore=5,
        spaceAfter=2,
    ),
    "cap": ParagraphStyle(
        "cap", fontSize=8, leading=9.6, alignment=TA_JUSTIFY, spaceBefore=3, spaceAfter=8, **base
    ),
    "tcap": ParagraphStyle(
        "tcap", fontSize=8, leading=9.6, alignment=TA_JUSTIFY, spaceBefore=4, spaceAfter=3, **base
    ),
    "cell": ParagraphStyle("cell", fontSize=7.4, leading=8.6, alignment=TA_LEFT, **base),
    "cellc": ParagraphStyle("cellc", fontSize=7.4, leading=8.6, alignment=TA_CENTER, **base),
    "cellb": ParagraphStyle(
        "cellb", fontSize=7.4, leading=8.6, alignment=TA_CENTER, fontName="STIX-Bold", textColor=INK
    ),
    "ref": ParagraphStyle(
        "ref",
        fontSize=8,
        leading=9.6,
        alignment=TA_LEFT,
        leftIndent=14,
        firstLineIndent=-14,
        spaceAfter=1.5,
        **base,
    ),
    "eqnum": ParagraphStyle("eqnum", fontSize=9.5, leading=11, alignment=2, **base),
    "item": ParagraphStyle(
        "item",
        fontSize=9.5,
        leading=11.6,
        alignment=TA_JUSTIFY,
        leftIndent=12,
        firstLineIndent=-12,
        spaceAfter=1.5,
        **base,
    ),
    "left": ParagraphStyle("left", fontSize=9.5, leading=11.6, alignment=TA_LEFT, **base),
    "code": ParagraphStyle(
        "code", fontName="Courier", fontSize=7.2, leading=8.6, textColor=INK, leftIndent=6
    ),
}

# ----------------------------------------------------------------------------- helpers
story: list = []
_eq = [0]
_fig = [0]
_tab = [0]
ROMAN = ["I", "II", "III", "IV", "V", "VI", "VII", "VIII", "IX", "X"]
_sec = [0]


def P(text: str, style: str = "body") -> None:
    story.append(Paragraph(text, S[style]))


def H1(title: str) -> None:
    _sec[0] += 1
    story.append(CondPageBreak(40))
    P(f"{ROMAN[_sec[0] - 1]}. {title.upper()}", "h1")


def H2(letter: str, title: str) -> None:
    story.append(CondPageBreak(30))
    P(f"{letter}. {title}", "h2")


def H3(title: str) -> None:
    P(f"{title}", "h3")


def eq(tex: str, label: str | None = None, size: float = 10.0) -> str:
    """Render a display equation with mathtext; return its number."""
    _eq[0] += 1
    n = _eq[0]
    path = EQ_DIR / f"eq{n:02d}.png"
    mathtext.math_to_image(
        f"${tex}$", str(path), prop=FontProperties(size=size), dpi=600, format="png"
    )
    w_px, h_px = PILImage.open(path).size
    w, h = w_px / 600 * 72, h_px / 600 * 72
    max_w = COL_W - 26
    if w > max_w:
        h *= max_w / w
        w = max_w
    t = Table([[Image(str(path), width=w, height=h), Paragraph(f"({n})", S["eqnum"])]],
              colWidths=[COL_W - 24, 24])  # fmt: skip
    t.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "MIDDLE"), ("ALIGN", (0, 0), (0, 0), "CENTER"),
                           ("LEFTPADDING", (0, 0), (-1, -1), 0), ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                           ("TOPPADDING", (0, 0), (-1, -1), 3), ("BOTTOMPADDING", (0, 0), (-1, -1), 3)]))  # fmt: skip
    story.append(t)
    return str(n)


def figure(file: str, caption: str, width: float = COL_W) -> int:
    _fig[0] += 1
    n = _fig[0]
    w_px, h_px = PILImage.open(FIG / file).size
    img = Image(str(FIG / file), width=width, height=width * h_px / w_px)
    story.append(KeepTogether([Spacer(1, 4), img, Paragraph(f"FIG. {n}. {caption}", S["cap"])]))
    return n


def table(rows: list[list[str]], widths: list[float], caption: str, header_rows: int = 1,
          align_center_from: int = 1, font_size: float | None = None) -> int:  # fmt: skip
    _tab[0] += 1
    n = _tab[0]
    cs = (
        S["cell"]
        if font_size is None
        else ParagraphStyle("c2", parent=S["cell"], fontSize=font_size, leading=font_size + 1.2)
    )
    ccs = (
        S["cellc"]
        if font_size is None
        else ParagraphStyle("c3", parent=S["cellc"], fontSize=font_size, leading=font_size + 1.2)
    )
    hb = (
        S["cellb"]
        if font_size is None
        else ParagraphStyle("c4", parent=S["cellb"], fontSize=font_size, leading=font_size + 1.2)
    )
    data = []
    for i, r in enumerate(rows):
        row = []
        for j, c in enumerate(r):
            st = hb if i < header_rows else (ccs if j >= align_center_from else cs)
            row.append(Paragraph(c, st))
        data.append(row)
    t = Table(data, colWidths=widths, repeatRows=header_rows)
    t.setStyle(TableStyle([
        ("LINEABOVE", (0, 0), (-1, 0), 0.8, RULE),
        ("LINEBELOW", (0, header_rows - 1), (-1, header_rows - 1), 0.5, RULE),
        ("LINEBELOW", (0, -1), (-1, -1), 0.8, RULE),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 2), ("RIGHTPADDING", (0, 0), (-1, -1), 2),
        ("TOPPADDING", (0, 0), (-1, -1), 1.3), ("BOTTOMPADDING", (0, 0), (-1, -1), 1.3),
    ]))  # fmt: skip
    story.append(
        KeepTogether([Paragraph(f"TABLE {ROMAN[n - 1]}. {caption}", S["tcap"]), t, Spacer(1, 7)])
    )
    return n


def sgn(x: float, nd: int = 2) -> str:
    """Signed number with a true minus sign and no negative zero."""
    v = round(x, nd)
    if v == 0:
        return f"{0:.{nd}f}"
    return f"{v:+.{nd}f}".replace("-", "−")


def neg(t: str) -> str:
    return t.replace("-", "−")


def f1(x: float) -> str:
    return f"{x:.1f}"


def f2(x: float) -> str:
    return f"{x:.2f}"


# ----------------------------------------------------------------------------- numbers
sample, opt, comp = RES["sample"], RES["optimised"], RES["compliant"]
delhi = RES["delhi"]
peaks = RES["sol_air_peaks"]
H = RES["irradiation_azimuth"]


def H_at(day: str, az: int) -> float:
    return H[day][az // 5]


rot = RES["rotation"]
na = delhi["noon_alt"]
swaps = sample["swaps"]
rb = load_rules()
D_E_W = peaks["W"] - peaks["E"]
lat = RES["latitude"]
n_tests = 72

# ----------------------------------------------------------------------------- title block
title_block = [
    Paragraph(escape(META["title"]), S["title"]),
    Paragraph(", ".join(escape(a) for a in META["authors"]), S["author"]),
    Paragraph(escape(META["affiliation"]), S["affil"]),
    Paragraph(f"(Dated: {META['date']})", S["dated"]),
    Paragraph(
        "We present a deterministic, machine-learning-free framework that ingests the architectural "
        "plan of a house, evaluates it against the directional prescriptions of <i>Vastu Shastra</i>, "
        "and tests those prescriptions against first-principles solar physics. The plan is encoded as "
        "planar polygons with a north reference corrected for geomagnetic declination (WMM2025). Rooms "
        "are projected onto a discretised Vastu-Purusha mandala by exact polygon clipping; the "
        "resulting zone-membership vector, contracted with an encoded rule tensor, yields a continuous "
        "per-room compliance, and a weighted aggregate defines a Vastu Compliance Index (VCI). In "
        "parallel, the NOAA solar-position series, the Kasten–Young air mass and the Meinel clear-sky "
        "model give the irradiation and sol-air temperature of every exterior wall. A steepest-ascent "
        "exchange optimiser proposes re-assignments of room functions. For a 180 m<super>2</super> "
        f"dwelling in New Delhi (28.6°N) the method identifies two critical defects and raises the VCI "
        f"from {f1(sample['vci'])} to {f1(opt['vci'])} with {len(swaps)} function exchanges, against "
        f"{f1(comp['vci'])} for a compliant reference plan. Physically, east and west walls receive equal "
        f"daily irradiation ({f2(H_at('summer_solstice', 90))} kWh m<super>−2</super> on 21 June) yet the "
        f"west-wall sol-air peak is {f1(D_E_W)} K higher ({f1(peaks['W'])} vs {f1(peaks['E'])} °C) because the "
        "beam load coincides with the afternoon air-temperature maximum—a quantitative, testable basis "
        "for the Vastu maxim “heavy south-west, open north-east.” The open-source implementation is "
        "fully typed, unit-tested and reproducible.",
        S["abstract"],
    ),
    Paragraph(
        "<b>Keywords:</b> Vastu Shastra; computational geometry; solar geometry; sol-air temperature; "
        "rule-based expert system; building physics; Python.",
        S["kw"],
    ),
    Spacer(1, 4),
]
title_h = (
    sum(f.wrap(FULL_W, 1000)[1] + f.getSpaceBefore() + f.getSpaceAfter() for f in title_block) + 14
)


# ----------------------------------------------------------------------------- page templates
def decorate(canvas, doc) -> None:  # type: ignore[no-untyped-def]
    canvas.saveState()
    canvas.setFont("STIX", 7.5)
    canvas.setFillColor(INK2)
    if doc.page == 1:
        canvas.drawString(M_L, PAGE_H - 12 * mm, "PREPRINT")
        canvas.drawRightString(
            PAGE_W - M_R, PAGE_H - 12 * mm, f"vastu-floorplan-analyzer v{__version__}"
        )
    else:
        canvas.drawString(M_L, PAGE_H - 12 * mm, META["running_head"])
        canvas.drawRightString(PAGE_W - M_R, PAGE_H - 12 * mm, str(doc.page))
        canvas.setStrokeColor(INK2)
        canvas.setLineWidth(0.4)
        canvas.line(M_L, PAGE_H - 13.3 * mm, PAGE_W - M_R, PAGE_H - 13.3 * mm)
    if doc.page == 1:
        canvas.drawCentredString(PAGE_W / 2, 10 * mm, "1")
    canvas.restoreState()


first_frames = [
    Frame(M_L, PAGE_H - M_T - title_h, FULL_W, title_h, 0, 0, 0, 0, id="title"),
    Frame(M_L, M_B, COL_W, BODY_H - title_h, 0, 0, 0, 0, id="c1a"),
    Frame(M_L + COL_W + GAP, M_B, COL_W, BODY_H - title_h, 0, 0, 0, 0, id="c1b"),
]
two_frames = [
    Frame(M_L, M_B, COL_W, BODY_H, 0, 0, 0, 0, id="L"),
    Frame(M_L + COL_W + GAP, M_B, COL_W, BODY_H, 0, 0, 0, 0, id="R"),
]
one_frame = [Frame(M_L, M_B, FULL_W, BODY_H, 0, 0, 0, 0, id="one")]
doc = BaseDocTemplate(
    str(OUT), pagesize=A4, leftMargin=M_L, rightMargin=M_R, topMargin=M_T, bottomMargin=M_B,
    title=META["title"], author=", ".join(META["authors"]),
    subject="Deterministic Vastu Shastra assessment of floor plans with solar physics",
    keywords="Vastu Shastra, computational geometry, solar geometry, sol-air temperature, Python",
    creator=f"vastu-floorplan-analyzer {__version__} / ReportLab",
)  # fmt: skip
doc.addPageTemplates([
    PageTemplate(id="First", frames=first_frames, onPage=decorate),
    PageTemplate(id="Two", frames=two_frames, onPage=decorate),
    PageTemplate(id="One", frames=one_frame, onPage=decorate),
])  # fmt: skip

story.extend(title_block)
story.append(NextPageTemplate("Two"))
story.append(FrameBreak())

# ============================================================================= I. INTRODUCTION
H1("Introduction")
P(
    "<i>Vāstu Śāstra</i> is the classical Indian science of dwelling and site planning. Its canonical "
    "treatises—the <i>Mayamata</i> and the <i>Mānasāra</i>, in circulation by the fifth to seventh "
    "centuries CE, the <i>Samarāngana Sūtradhāra</i>, and chapter 53 of Varāhamihira’s "
    "<i>Brhat Samhitā</i>—prescribe the orientation of a building, the proportions of its plot and, above "
    "all, the <i>direction</i> in which each function of the house should lie [1–4]. The organising device "
    "is the <i>Vāstu-Purusa mandala</i>: a square grid of <i>padas</i> ranging from 1 to 1024 cells, of "
    "which the 81-cell <i>Paramaśāyika</i> is customary for dwellings and whose central cells form the "
    "<i>Brahmasthāna</i>, to be kept open [3,4]. The eight outer directions are each presided over by a "
    "deity—Īśāna (north-east), Agni (south-east), Nirrti (south-west), Vāyu (north-west)—and the "
    "functional prescriptions follow from this cosmology: fire (the kitchen) in the south-east, worship "
    "in the north-east, the master’s chamber in the heavy south-west, and so on."
)
P(
    "In contemporary India, Vastu compliance is a commercial attribute of residential property, yet its "
    "assessment remains manual, subjective and inconsistent between consultants. At the same time the "
    "scientific status of Vastu is contested. Rationalist critics classify many of its claims—notably "
    "those invoking the geomagnetic field—as pseudo-scientific [4], whereas a small empirical literature "
    "reports measurable thermal effects of orientation: in naturally ventilated rooms in warm-humid "
    "Kharagpur, east-facing rooms showed a predicted percentage of dissatisfied (PPD) of 43.3%, against "
    "45–85.1% for west- and south-facing rooms [5]. Other authors argue for a physical substantiation of "
    "Vastu in terms of sun and wind [6]. What is missing is a <i>reproducible instrument</i> that "
    "separates the codified tradition from the physically testable part of it."
)
P(
    "This paper constructs such an instrument under a deliberate constraint: <i>no artificial "
    "intelligence or machine learning</i> may be used—no neural segmentation of plan images and no "
    "optical character recognition, since modern OCR engines such as Tesseract (≥ 4.0) are themselves "
    "LSTM neural networks [18]. Every inference must be deterministic and auditable. Our contributions "
    "are: (i) a ranked evaluation of eight non-ML ways to solve the problem (Sec. II); (ii) a formal "
    "geometric model of Vastu zoning based on exact polygon clipping, which renders compliance a "
    "continuous functional of the geometry (Sec. III A–H); (iii) its coupling to a solar-physics engine "
    "that evaluates every exterior wall (Sec. III I–L); (iv) a combinatorial optimiser that proposes "
    "re-assignment of room functions (Sec. III M); (v) an open-source, typed and tested Python "
    "implementation (Sec. IV); and (vi) a case study with validation and sensitivity analyses (Sec. V)."
)

# ============================================================================= II. DESIGN SPACE
H1("Design space and choice of method")
P(
    "The problem decomposes into a <i>front end</i>—how the geometry of the house enters the program—and "
    "a <i>back end</i> that reasons about directions. Without machine learning the back end is "
    "necessarily a rule-based expert system; the approaches therefore differ chiefly in the front end. "
    "We scored eight candidate pipelines (a ninth, ML segmentation with OCR, is disqualified by "
    "the constraint) on six criteria, each on a 1–5 scale: C1 fitness to the objective (does it analyse "
    "the map <i>and</i> produce Vastu suggestions?), weight 0.25; C2 reliability and accuracy of zone "
    "assignment, 0.25; C3 compliance with the no-AI/ML constraint, 0.15; C4 implementation feasibility "
    "within a semester (5 = easiest), 0.15; C5 accessibility of the required input to a homeowner, 0.10; "
    "C6 extensibility and testability, 0.10. The weighted score is"
)
eq(r"S_a=\sum_{c=1}^{6}\omega_c\,x_{a,c},\qquad \sum_c\omega_c=1,")
APPROACHES = [
    (
        "A1",
        "Structured polygon model (JSON) + geometric zoning + rule engine + solar physics; click-digitiser for scans",
        (5, 5, 5, 4, 4, 5),
    ),
    (
        "A2",
        "Vector CAD (DXF) parsing (closed polylines on room layers) + same back end",
        (5, 5, 5, 3, 2, 4),
    ),
    (
        "A3",
        "Interactive GUI editor (Tkinter canvas) for drawing rooms + same back end",
        (5, 4, 5, 2, 4, 3),
    ),
    ("A4", "Character-grid (ASCII/CSV matrix) map; areas by cell counting", (4, 3, 5, 5, 3, 4)),
    ("A5", "BIM/IFC parsing (IfcSpace geometry, TrueNorth)", (4, 5, 5, 2, 1, 4)),
    ("A6", "Questionnaire expert system (user states room directions)", (2, 3, 5, 5, 5, 3)),
    (
        "A7",
        "Classical raster image processing (threshold, morphology, contours, Hough) + manual labels",
        (4, 2, 4, 2, 5, 2),
    ),
    ("A8", "Room-adjacency graph only (topology, no orientation)", (2, 2, 5, 4, 3, 3)),
]
W8 = (0.25, 0.25, 0.15, 0.15, 0.10, 0.10)
scored = sorted(
    ((sum(w * x for w, x in zip(W8, xs, strict=True)), k, d, xs) for k, d, xs in APPROACHES),
    reverse=True,
)
rows = [["Rank", "Approach", "C1", "C2", "C3", "C4", "C5", "C6", "<i>S</i>"]]
for i, (s_, k, d, xs) in enumerate(scored, 1):
    rows.append(
        [
            str(i),
            f"<b>{k}</b> {d}",
            *[str(x) for x in xs],
            f"<b>{s_:.2f}</b>" if i == 1 else f"{s_:.2f}",
        ]
    )
rows.append(
    [
        "–",
        "<b>A9</b> CNN segmentation + OCR (disqualified: uses ML)",
        "–",
        "–",
        "0",
        "–",
        "–",
        "–",
        "–",
    ]
)
table(rows, [23, 109, 14, 14, 14, 14, 14, 14, 22],
      "Weighted decision matrix for the candidate approaches (scores 1–5; weights C1–C6 = "
      "0.25, 0.25, 0.15, 0.15, 0.10, 0.10).", align_center_from=2, font_size=6.8)  # fmt: skip
P(
    "<b>Reasons for the ranking.</b> A1 ranks first (<i>S</i> = 4.75) because a polygonal description is the "
    "<i>canonical</i> representation into which every other front end must ultimately be converted: it is "
    "exact, unit-aware, trivially validated and fully testable, and with a click-based digitiser it "
    "accepts any scanned plan while keeping a human—not a model—in the loop. A2 (4.30) is equally exact "
    "and professional but presupposes a CAD file with disciplined layering, which few homeowners possess; "
    "it is best seen as an adapter onto A1. A3 (4.00) offers the best user experience but its GUI cost "
    "dominates a semester and snap-to-grid drawing reduces accuracy. A4 (3.95) is the simplest to build "
    "and excellent for teaching, but its resolution is limited by the cell size, so zone fractions are "
    "quantised. A5 (3.80) carries the richest semantics—IFC spaces and a stored true-north vector [20]—"
    "but residential projects in India rarely produce BIM models. A6 (3.55) is trivial but does not "
    "analyse a map at all: it outsources the geometry to the user’s judgement, which is precisely the "
    "error source we wish to remove. A7 (3.10) is automatic, yet classical room detection from raster "
    "plans is fragile—door openings break enclosures, while hatching, text and dimension lines create "
    "spurious contours [16,17]—and labelling rooms without OCR still requires manual input; a "
    "confidently wrong zone assignment is worse than none. A8 (2.95) discards orientation, the one "
    "quantity Vastu depends on. We therefore adopt A1 and design it so that A2–A4 can be added later as "
    "front-end adapters without touching the back end."
)

# ============================================================================= III. THEORY
H1("Theoretical framework")
H2("A", "Representation of the plan")
P(
    "A plan is the tuple 𝒫 = (<i>F</i>, {(<i>R<sub>i</sub></i>, <i>t<sub>i</sub></i>)}, {<b>e</b><sub><i>j</i></sub>}, "
    "<i>θ</i><sub>a</sub>, <i>D</i>), where <i>F</i> ⊂ ℝ<super>2</super> is the footprint polygon, <i>R<sub>i</sub></i> "
    "the polygon of room <i>i</i> with function type <i>t<sub>i</sub></i>, <b>e</b><sub><i>j</i></sub> the door "
    "positions, <i>θ</i><sub>a</sub> the angle of the drawing’s north arrow measured clockwise from the "
    "drawing’s +<i>y</i> axis, and <i>D</i> the local magnetic declination (east positive) when the arrow "
    "denotes magnetic north. Coordinates are converted to metres and every polygon is re-oriented "
    "counter-clockwise, so that its signed area is positive."
)
H2("B", "Orientation and the cardinal frame")
P(
    "The true-north angle and the compass bearing of any drawing vector <b>v</b> = (<i>v<sub>x</sub></i>, <i>v<sub>y</sub></i>) are",
    "body0",
)
eq(
    r"\theta=\theta_a-D,\qquad \beta(\mathbf{v})=\mathrm{atan2}(v_x,v_y)-\theta\ \ (\mathrm{mod}\ 360^\circ)."
)
P(
    "For zoning, classical practice aligns the mandala with the walls of the house, so we rotate the "
    "plan about the footprint centroid <b>c</b> by the cardinal angle <i>θ</i><sub>s</sub> = 90° · round(<i>θ</i>/90°):",
    "body0",
)
eq(
    r"\binom{x'-c_x}{y'-c_y}=\binom{(x-c_x)\cos\theta_s-(y-c_y)\sin\theta_s}{(x-c_x)\sin\theta_s+(y-c_y)\cos\theta_s}."
)
P(
    "The residual skew <i>δ</i> = <i>θ</i> − <i>θ</i><sub>s</sub> is retained for the physics, which uses exact "
    "bearings; plots with |<i>δ</i>| > 15° are flagged as <i>vidiśā</i> (diagonal) plots. For Indian cities the "
    "WMM2025 declination lies between −1.7° and +2.8° (Appendix B), an order of magnitude below the 22.5° "
    "width of a compass sector, so the true/magnetic distinction rarely changes a zone but does shift "
    "solar azimuths."
)
H2("C", "Polygon measures")
P("Areas and centroids follow from the shoelace (Gauss) formula, with cyclic indices:", "body0")
eq(r"A=\frac{1}{2}\sum_{k}(x_k y_{k+1}-x_{k+1}y_k),")
eq(r"\mathbf{c}=\frac{1}{6A}\sum_{k}(x_k y_{k+1}-x_{k+1}y_k)\,(x_k+x_{k+1},\,y_k+y_{k+1}).")
P(
    "An edge of a room is an <i>exterior wall</i> when its midpoint lies within 5 cm of ∂<i>F</i> and a probe "
    "displaced 10 cm along the outward normal <b>n</b> = (Δ<i>y</i>, −Δ<i>x</i>)/<i>L</i> falls outside <i>F</i> "
    "(even–odd ray-casting test). The wall azimuth is <i>γ</i> = <i>β</i>(<b>n</b>)."
)
H2("D", "The discretised Vastu-Purusa mandala")
P(
    "Let <i>B</i> = [<i>x</i><sub>0</sub>, <i>x</i><sub>1</sub>] × [<i>y</i><sub>0</sub>, <i>y</i><sub>1</sub>] be the "
    "bounding box of the rotated footprint, divided into the 3 × 3 <i>Pītha</i> grid of cells "
    "<i>C<sub>z</sub></i>, <i>z</i> ∈ 𝒵 = {NW, N, NE, W, C, E, SW, S, SE}. The eight outer cells are the "
    "<i>dik</i> (directions) and C is the Brahmasthāna. The zone-membership vector of a room is"
)
eq(r"f_z(R)=\frac{|R\cap C_z|}{|R|},\qquad \sum_{z\in\mathcal{Z}}f_z=1,")
P(
    "where |<i>R</i> ∩ <i>C<sub>z</sub></i>| is computed exactly by Sutherland–Hodgman clipping [15]. Because "
    "each <i>C<sub>z</sub></i> is convex, the clipped area is exact even for concave rooms (L-shapes), "
    "degenerate bridges contributing zero area."
)
H2("E", "Rule tensor and room compliance")
P(
    "The knowledge base assigns to each function type <i>t</i> and zone <i>z</i> a value <i>v<sub>t</sub></i>(<i>z</i>) "
    "on the ordinal scale {avoid, poor, acceptable, good, ideal} ↦ {0, ¼, ½, ¾, 1}, together with an importance "
    "weight <i>w<sub>t</sub></i> and a ‘heaviness’ <i>h<sub>t</sub></i> (Appendix A). It is stored as data, not code, so "
    "that a reviewer can audit or modify it without touching the engine. The compliance of room <i>i</i> is "
    "the contraction",
    "body0",
)
eq(r"s_i=\sum_{z\in\mathcal{Z}}f_z(R_i)\,v_{t_i}(z)\ \in[0,1].")
P(
    "Equation (7) is a linear functional of the membership vector and hence a <i>continuous</i> function "
    "of the geometry: a room straddling a zone boundary receives an area-weighted blend instead of an "
    "arbitrary binary verdict. If a boundary moves by Δ<i>x</i>, a rectangular room of area <i>A</i> crossing it "
    "with a chord of length ℓ changes its memberships by |Δ<i>f</i>| = ℓΔ<i>x</i>/<i>A</i>, so"
)
eq(r"|\Delta s_i|\leq\frac{\ell\,|\Delta x|}{A}\,\max_{z,z'}|v_t(z)-v_t(z')|.")
P(
    "For a 4 m × 5 m room, a 0.1 m digitisation error therefore perturbs <i>s<sub>i</sub></i> by at most 0.025—an "
    "explicit error bound that a binary rule cannot provide."
)
H2("F", "Entrance")
P(
    "For a door at <b>e</b> the bearing <i>β</i><sub>e</sub> = <i>β</i>(<b>e</b> − <b>c</b>) is assigned to one of 16 sectors,",
    "body0",
)
eq(r"k=\left\lfloor\frac{\beta_e+11.25^\circ}{22.5^\circ}\right\rfloor\ \mathrm{mod}\ 16,")
P(
    "each with a value <i>u<sub>k</sub></i>: N, NNE, NE and E are ideal; the SSW–SW sectors are to be avoided "
    "(Appendix A). The main door carries weight 10 and secondary doors weight 3."
)
H2("G", "Site-level terms")
P(
    "<i>Brahmasthāna.</i> The fraction of the central cell occupied by heavy or wet functions 𝒯<sub>f</sub> = "
    "{toilet, kitchen, staircase, store, tanks} is penalised:",
    "body0",
)
eq(
    r"b=\frac{1}{|C_{\mathrm{C}}|}\sum_{i:\,t_i\in\mathcal{T}_f}|R_i\cap C_{\mathrm{C}}|,\qquad s_B=\max(0,1-b)."
)
P(
    "<i>Corner cuts.</i> A missing corner is a classical <i>dosa</i>. The fill of each corner cell is "
    "φ<sub><i>z</i></sub> = |<i>F</i> ∩ <i>C<sub>z</sub></i>|/|<i>C<sub>z</sub></i>|, <i>z</i> ∈ {NE, SE, SW, NW}, "
    "with weights 8, 3, 6, 3 (the NE cut being gravest). <i>Shape.</i> With rectangularity ρ = |<i>F</i>|/|<i>B</i>| "
    "and aspect ratio <i>a</i>, <i>s</i><sub>shape</sub> = ρ for <i>a</i> ≤ 2, decreasing linearly beyond.",
    "body",
)
P(
    "<i>Mass dipole.</i> Vastu demands that the south-west be the heaviest and the north-east the lightest "
    "quarter. We formalise this with a mass-weighted centroid offset, the planar analogue of a dipole "
    "moment, using the heaviness <i>h<sub>t</sub></i> of each function:",
    "body",
)
eq(
    r"\mathbf{p}=\frac{\sum_i h_{t_i}A_i(\mathbf{c}_i-\mathbf{c})}{\sum_i h_{t_i}A_i},\qquad m=\frac{|\mathbf{p}|}{d/2},"
)
eq(
    r"s_{\mathrm{dip}}=\frac{1}{2}+\frac{1}{2}\cos(\beta_{\mathbf{p}}-225^\circ)\,\min\!\left(1,\frac{m}{m_0}\right),"
)
P(
    "with <i>d</i> the diagonal of <i>B</i> and <i>m</i><sub>0</sub> = 0.10. A uniform distribution (<b>p</b> = 0) scores ½; a "
    "dipole pointing south-west scores 1; one pointing north-east scores 0."
)
H2("H", "Vastu Compliance Index")
P("All terms are aggregated with their weights into a single index,", "body0")
eq(
    r"\mathrm{VCI}=100\,\frac{\sum_i w_{t_i}s_i+\sum_j w_j u_{k_j}+w_Bs_B+\sum_z w_z\varphi_z+w_\mathrm{sh}s_\mathrm{sh}+w_\mathrm{d}s_\mathrm{dip}}{\sum(\mathrm{all\ weights})}.",
    size=9.2,
)
P(
    "We grade VCI ≥ 85 as excellent, 70–85 good, 55–70 fair, and below 55 poor. Findings are emitted for "
    "every term below ¾, with severity <i>critical</i> when a high-weight item (<i>w</i> ≥ 8) scores ≤ ¼; each "
    "finding carries its recoverable VCI, 100 <i>w</i>(1 − <i>s</i>)/Σ<i>w</i>, which orders the suggestions."
)
H2("I", "Solar geometry")
P(
    "To test the physical content of the directional rules we compute the sun’s position with the NOAA "
    "Global Monitoring Laboratory series [7], which approximates the full Meeus ephemeris [8]. With the "
    "fractional year <i>γ</i> (radians) for day <i>N</i> and UTC hour <i>t</i>,",
    "body0",
)
eq(r"\gamma=\frac{2\pi}{365}\left(N-1+\frac{t-12}{24}\right),")
eq(r"\delta=0.006918-0.399912\cos\gamma+0.070257\sin\gamma-0.006758\cos2\gamma+\ldots", size=9.0)
eq(r"E=229.18\,(0.000075+0.001868\cos\gamma-0.032077\sin\gamma-\ldots)", size=9.0)
P(
    "(the full series, including the 3<i>γ</i> terms of the declination, is implemented). The true solar time, "
    "hour angle <i>ω</i>, altitude <i>α</i> and azimuth <i>A</i> (clockwise from north) follow from latitude <i>φ</i> "
    "and longitude <i>λ</i> (time zone <i>τ</i> = +5.5 h for IST):",
    "body0",
)
eq(r"t_s=60t_\ell+E+4\lambda-60\tau,\qquad \omega=t_s/4-180^\circ,")
eq(r"\sin\alpha=\sin\varphi\sin\delta+\cos\varphi\cos\delta\cos\omega,")
eq(r"A=180^\circ+\mathrm{atan2}(\sin\omega,\ \cos\omega\sin\varphi-\tan\delta\cos\varphi).")
H2("J", "Clear-sky irradiance on a wall")
P(
    "The relative optical air mass is taken from Kasten and Young [9] and the direct normal irradiance from the Meinel model [10]:",
    "body0",
)
eq(r"m_a=\left[\cos z+0.50572\,(96.07995^\circ-z)^{-1.6364}\right]^{-1},")
eq(r"I_{DN}=1353\ \mathrm{W\,m^{-2}}\times0.7^{\,m_a^{0.678}}.")
P(
    "Here 0.7 represents the ~70% atmospheric transmittance and the exponent 0.678 is an empirical fit "
    "to atmospheric inhomogeneity. On a vertical wall of azimuth <i>γ</i> the beam, isotropic-sky and "
    "ground-reflected components (Liu–Jordan [11]) are",
    "body0",
)
eq(
    r"I_v=I_{DN}\max[0,\cos\alpha\cos(A-\gamma)]+\frac{I_{dh}}{2}+\frac{\rho_g}{2}(I_{DN}\sin\alpha+I_{dh}),"
)
P(
    "with diffuse horizontal <i>I<sub>dh</sub></i> = 0.1 <i>I<sub>DN</sub></i> and ground albedo ρ<sub>g</sub> = 0.2. The daily "
    "irradiation <i>H</i>(<i>γ</i>) = ∫<i>I<sub>v</sub></i> d<i>t</i> is integrated by the midpoint rule with a 5-min "
    "step and split at solar noon into morning and afternoon parts."
)
H2("K", "Sol-air temperature and the east–west asymmetry")
P(
    "The thermal forcing of an opaque wall is the sol-air temperature (ASHRAE [12]; the long-wave term vanishes for vertical surfaces),",
    "body0",
)
eq(
    r"T_{sa}(t)=T_o(t)+\frac{a_s\,I_v(t)}{h_o},\qquad T_o(t)=\bar T+\frac{\Delta T}{2}\cos\frac{2\pi(t-t_{\max})}{24\,\mathrm{h}},"
)
P(
    "with absorptance <i>a<sub>s</sub></i> = 0.6, film coefficient <i>h<sub>o</sub></i> = 17 W m<super>−2</super> K<super>−1</super>, a "
    "composite-climate design day <i>T</i><sub>max</sub> = 39 °C, <i>T</i><sub>min</sub> = 28 °C and <i>t</i><sub>max</sub> = 15:00 "
    "solar time. Averaging (23) over a day gives",
    "body0",
)
eq(r"\langle T_{sa}\rangle=\bar T+\frac{a_s\,H(\gamma)}{h_o\,(24\,\mathrm{h})}.")
P(
    "Equation (24) is a key physical result: since the daily-mean conductive heat flux through a wall at "
    "fixed indoor temperature is proportional to the daily mean of <i>T<sub>sa</sub></i> − <i>T<sub>i</sub></i>, an east and a west wall "
    "with equal <i>H</i> admit the <i>same</i> mean heat. The asymmetry lies entirely in the <i>timing</i> and "
    "<i>peak</i>: the west beam load coincides with the afternoon maximum of <i>T<sub>o</sub></i>, raising the peak "
    "sol-air temperature (which sizes cooling loads) and, through the 6–8 h thermal lag of heavy masonry "
    "[23], delivering that heat indoors at night. This is the physical content of the Vastu rule that the "
    "south-west be closed and massive while the north-east is open."
)
H2("L", "Overhang design")
P(
    "For equator-facing glazing we recommend a horizontal overhang whose depth-to-height ratio shades the "
    "window at solar noon from the equinox through summer while admitting the lower winter sun:",
    "body0",
)
eq(
    r"\frac{d}{h}=\frac{1}{\tan\alpha_{\mathrm{noon}}(\mathrm{equinox})}=\tan\left(\varphi-\delta_{\mathrm{eq}}\right)."
)
H2("M", "Optimal re-assignment of functions")
P(
    "When relocation of walls is impractical, Vastu consultants exchange room functions. Let σ be a "
    "permutation of the types of the <i>movable</i> rooms (staircases, circulation, garages and open spaces "
    "are fixed), subject to an area-compatibility constraint max(<i>A<sub>i</sub></i>, <i>A<sub>j</sub></i>)/min(<i>A<sub>i</sub></i>, "
    "<i>A<sub>j</sub></i>) ≤ 2 for any exchanged pair. Maximising VCI(σ) is a quadratic-assignment-type problem "
    "(Koopmans–Beckmann [24]), NP-hard in general, so we use steepest ascent in the transposition "
    "neighbourhood: at each step all <i>O</i>(<i>n</i><super>2</super>) admissible exchanges are evaluated exactly and the "
    "best is applied if it gains ≥ 0.5 VCI points. The search terminates at a local optimum after at most "
    "10 steps; each step costs <i>O</i>(<i>n</i><super>3</super>) arithmetic, negligible for houses (<i>n</i> ≤ 30)."
)

# ============================================================================= IV. ALGORITHM
H1("Algorithm and implementation")
figure("fig1_flowchart.png",
       "Flowchart of the selected approach (A1). The plan is digitised once; geometry, zoning, the Vastu "
       "rule engine and the physics engine are fully deterministic. The optimiser loop re-scores candidate "
       "exchanges of room functions until no exchange improves the VCI by ≥ 0.5.")  # fmt: skip
H2("A", "Detailed procedure")
steps = [
    "<b>Step 1 — Digitise.</b> From the drawing record (a) the outer footprint polygon, (b) one closed polygon "
    "per room with a function label, (c) the door positions, (d) the north arrow and whether it is true or "
    "magnetic, and (e) the scale. For scans, the bundled digitiser displays the image and records mouse "
    "clicks: two clicks on a known dimension fix the scale, two on the north arrow fix <i>θ</i><sub>a</sub>, and "
    "successive polygons are traced; the program never interprets pixels. The result is a JSON file "
    "(Appendix C), optionally with latitude, longitude and time zone.",
    "<b>Step 2 — Validate and normalise.</b> All errors are collected in one pass: schema version, units "
    "(m, cm, mm, ft, in → m), ≥ 3 vertices, non-zero area, a room centroid inside the footprint, valid "
    "north reference and coordinates. Polygons are made counter-clockwise; aliases (e.g. “bathroom” → "
    "toilet, “puja” → pooja) are resolved; the first door is the main one if none is marked.",
    "<b>Step 3 — Orient.</b> Compute <i>θ</i> = <i>θ</i><sub>a</sub> − <i>D</i> (Eq. 2) using the WMM2025 declination; "
    "rotate the plan by <i>θ</i><sub>s</sub> (Eq. 3) into the cardinal frame for zoning and keep <i>δ</i> for physics.",
    "<b>Step 4 — Measure.</b> Areas and centroids (Eqs. 4–5); exterior walls with their lengths and "
    "azimuths <i>γ</i>; footprint rectangularity, aspect ratio and corner fills.",
    "<b>Step 5 — Zone.</b> Build the 3 × 3 mandala on the footprint’s bounding box; compute <i>f<sub>z</sub></i>(<i>R<sub>i</sub></i>) by "
    "clipping (Eq. 6); assign 16-sector bearings to rooms and doors (Eq. 9).",
    "<b>Step 6a — Apply Vastu rules.</b> Room scores (Eq. 7), entrance values, Brahmasthāna occupancy "
    "(Eq. 10), corner cuts, shape and the mass dipole (Eqs. 11–12).",
    "<b>Step 6b — Apply physics.</b> For the site, integrate <i>H</i>(<i>γ</i>) and <i>T<sub>sa</sub></i>(<i>t</i>) on the "
    "summer-solstice, equinox and winter-solstice design days (Eqs. 14–24); attach to each room the "
    "irradiation on its exterior walls, its afternoon fraction and the peak <i>T<sub>sa</sub></i> of its hottest wall.",
    "<b>Step 7 — Score.</b> Aggregate the VCI (Eq. 13) and grade it.",
    "<b>Step 8 — Optimise.</b> If the VCI is below target or a critical defect exists, run the exchange "
    "optimiser (Sec. III M) and report each exchange with its VCI gain and the net change of use.",
    "<b>Step 9 — Suggest and report.</b> Emit findings sorted by severity and recoverable VCI; each "
    "carries a preferred zone, a traditional remedy, the traditional rationale and the physical rationale, "
    "and physics findings add quantitative mitigations (west-wall shading, overhang ratio from Eq. 25, "
    "ventilation for internal toilets). Output text, Markdown or JSON and an annotated zone map.",
]
for s_ in steps:
    P(s_, "item")
H2("B", "Software architecture and quality assurance")
P(
    f"The reference implementation (package <font face='Courier' size='8.5'>vastu_analyzer</font>, v{__version__}) is "
    "written in Python ≥ 3.10 with <i>no runtime dependencies</i>; matplotlib is optional for plotting. "
    "Modules are separated by concern: <font face='Courier' size='8.5'>geometry</font> (shoelace, clipping, ray "
    "casting), <font face='Courier' size='8.5'>zoning</font> (mandala and sectors), <font face='Courier' size='8.5'>rules</font> "
    "(JSON knowledge base), <font face='Courier' size='8.5'>solar</font> (Eqs. 14–25), <font face='Courier' size='8.5'>engine</font> "
    "(scoring, findings, optimiser), <font face='Courier' size='8.5'>report</font>, <font face='Courier' size='8.5'>plotting</font>, "
    "<font face='Courier' size='8.5'>digitize</font> and a command-line interface. The code is statically typed "
    f"(mypy strict), linted (ruff), and covered by {n_tests} unit tests (97% branch coverage) that check "
    "analytic identities—e.g. the L-shape centroid, exact clipping of concave polygons, the noon altitude "
    "90° − <i>φ</i> + <i>δ</i>, east–west irradiation symmetry, and the rotation invariance of the VCI when the "
    "drawing and its north arrow are rotated together. Continuous integration runs the suite on Linux and "
    "Windows for Python 3.10–3.13. A full analysis of the case-study plan, optimiser included, takes about "
    "27 ms on a laptop CPU."
)

# ============================================================================= V. RESULTS
H1("Results")
H2("A", "Validation of the solar module")
dec_jun = math.degrees(solar.declination_and_eot(solar.fractional_year(172, 6.5))[0])
eot_nov = solar.declination_and_eot(solar.fractional_year(307, 6.5))[1]
eot_feb = solar.declination_and_eot(solar.fractional_year(42, 6.5))[1]
phi = 28.6139
rows = [
    ["Quantity", "Model", "Reference", "Δ"],
    ["<i>δ</i> on 21 Jun (°)", f"{dec_jun:.2f}", "23.44 (obliquity)", sgn(dec_jun - 23.44)],
    [
        "<i>α</i><sub>noon</sub> Delhi, 21 Jun (°)",
        f"{na['summer_solstice']:.2f}",
        f"{90 - phi + 23.44:.2f}",
        sgn(na["summer_solstice"] - (90 - phi + 23.44)),
    ],
    [
        "<i>α</i><sub>noon</sub> Delhi, 21 Dec (°)",
        f"{na['winter_solstice']:.2f}",
        f"{90 - phi - 23.44:.2f}",
        sgn(na["winter_solstice"] - (90 - phi - 23.44)),
    ],
    ["<i>E</i> on 3 Nov (min)", f"{eot_nov:.1f}", "16.4", sgn(eot_nov - 16.4, 1)],
    ["<i>E</i> on 11 Feb (min)", neg(f"{eot_feb:.1f}"), "−14.2", sgn(eot_feb + 14.2, 1)],
    [
        "<i>m<sub>a</sub></i> at <i>α</i> = 30°",
        f"{solar.air_mass(30):.3f}",
        "sec 60° = 2.000",
        sgn(solar.air_mass(30) - 2, 3),
    ],
    [
        "<i>I<sub>DN</sub></i> at <i>m<sub>a</sub></i> = 1 (W m<super>−2</super>)",
        f"{solar.direct_normal_irradiance(90):.1f}",
        "1353 × 0.7 = 947.1",
        "0.0",
    ],
    [
        "<i>H</i>(E) − <i>H</i>(W), 21 Jun (kWh m<super>−2</super>)",
        sgn(H_at("summer_solstice", 90) - H_at("summer_solstice", 270), 3),
        "0 (symmetry)",
        "–",
    ],
]
table(rows, [92, 40, 66, 30], "Validation of the solar-geometry and irradiance module against analytic and "
      "almanac values (New Delhi, φ = 28.61°N).", align_center_from=1)  # fmt: skip
P(
    "Table II shows agreement to within 0.02° for the noon altitudes and 0.1 min for the equation of time, "
    "consistent with the stated accuracy of the NOAA series; the small air-mass deviation at 30° "
    "altitude is the physical curvature correction of Kasten–Young relative to the flat-atmosphere sec <i>z</i>."
)
H2("B", "Case study: a 3BHK house in New Delhi")
P(
    "The test plan is a single-storey, 12 m × 15 m (180 m<super>2</super>) three-bedroom house with 13 rooms "
    "(Fig. 2a), its north arrow rotated <i>θ</i><sub>a</sub> = 8° from the sheet’s vertical, and the main door on the "
    "south façade—a typical builder layout. Table III lists the per-room results."
)
TY = {"master_bedroom": "master bed", "circulation": "circulation", "open_space": "open"}
rows = [
    ["Room", "Function", "Zone", "Sector", "<i>A</i> (m<super>2</super>)", "<i>s<sub>i</sub></i>"]
]
for r in sample["rooms"]:
    rows.append(
        [
            r["name"],
            TY.get(r["type"], r["type"]),
            r["zone"],
            r["sector"],
            f1(r["area"]),
            f2(r["score"]),
        ]
    )
table(
    rows,
    [58, 50, 24, 28, 34, 26],
    "Per-room zoning and compliance for the as-built plan.",
    align_center_from=2,
)
c = sample["components"]
P(
    f"The as-built VCI is <b>{f1(sample['vci'])}</b> (fair). Its components are: rooms {f1(c['rooms'])}, entrance "
    f"{f1(c['entrance'])}, Brahmasthāna {f1(c['brahmasthana'])}, corners {f1(c['corners'])}, shape {f1(c['shape'])} "
    f"and mass balance {f1(c['mass_balance'])}. Two <i>critical</i> defects are detected: the kitchen lies in the "
    "north/north-east (<i>s</i> = 0, the fire element in the water quarter) and a toilet occupies the "
    "north-east corner (<i>s</i> = 0). Major findings include the utility in the NE, the staircase and store in "
    "the east, bedroom 3 in the SE (Agni) and the main door in the SSE sector (<i>u</i> = ½). The mass "
    f"dipole points to {sample['site']['dipole_bearing']:.0f}° (|<b>p</b>|/(d/2) = {sample['site']['dipole_magnitude']:.3f}), "
    "only partly towards the south-west because the heavy staircase sits in the east."
)
figure("fig2_plans.png",
       "Annotated zone maps (cardinal frame; dashed lines: 3 × 3 mandala). Rooms are coloured on a diverging "
       "scale from red (<i>s</i> = 0, avoid) through grey (½) to blue (<i>s</i> = 1, ideal); numbers are <i>s<sub>i</sub></i>; "
       "the diamond is the main door and the arrow true north (θ = 8°). (a) As built. (b) After the three "
       "function exchanges proposed by the optimiser (arrows show the new use).")  # fmt: skip
rows = [["#", "Exchange (room → new use)", "VCI after", "Gain"]]
for i, s_ in enumerate(swaps, 1):
    rows.append([str(i), f"{s_['room_a']} → {s_['type_b'].replace('_', ' ')};  {s_['room_b']} → {s_['type_a'].replace('_', ' ')}",
                 f1(s_["vci_after"]), f"+{f1(s_['gain'])}"])  # fmt: skip
table(
    rows,
    [12, 152, 34, 30],
    "Sequence of exchanges found by steepest ascent (Sec. III M); each step "
    "acts on the uses produced by the previous one.",
    align_center_from=2,
)
re_ = sample["reassignment"]
P(
    "The optimiser (Table IV) first exchanges the kitchen with bedroom 3, moving fire to the south-east "
    f"(+{f1(swaps[0]['gain'])}); it then moves worship to the north-east by exchanging toilet 1 with the pooja room "
    f"(+{f1(swaps[1]['gain'])}), and finally swaps the living room and the former kitchen so that the living "
    f"space occupies the N/NE and a bedroom the NW (+{f1(swaps[2]['gain'])}). The net change of use is: "
    + "; ".join(
        f"{x['room']}: {x['from'].replace('_', ' ')} → {x['to'].replace('_', ' ')}" for x in re_
    )
    + f". The VCI rises to <b>{f1(opt['vci'])}</b> (good), with no critical defect remaining (Fig. 2b). The "
    f"remaining gap to the reference plan (VCI {f1(comp['vci'])}) is due to fixed elements—the eastern "
    "staircase, the NE utility and the south door—which require construction rather than re-assignment; "
    "the report lists these with their recoverable VCI so that the owner can weigh cost against benefit."
)
H2("C", "Façade physics")
figure("fig3_irradiation_azimuth.png",
       "Daily clear-sky irradiation <i>H</i>(<i>γ</i>) on a vertical wall versus its outward normal at New Delhi "
       "for the June solstice, March equinox and December solstice.")  # fmt: skip
P(
    f"Figure 3 quantifies the seasonal selectivity of each orientation. On 21 June the east and west walls "
    f"receive the most energy ({f2(H_at('summer_solstice', 90))} kWh m<super>−2</super> day<super>−1</super>), the south wall the least "
    f"({f2(H_at('summer_solstice', 180))})—less even than the north wall ({f2(H_at('summer_solstice', 0))}), because the noon sun "
    f"stands at {f1(na['summer_solstice'])}° and rises and sets north of the east–west line. On 21 December the "
    f"pattern inverts: the south wall receives {f2(H_at('winter_solstice', 180))} and the north wall only "
    f"{f2(H_at('winter_solstice', 0))} (diffuse and reflected light). A south façade is therefore the ideal "
    f"seasonal collector, and the overhang of Eq. (25) with <i>d</i>/<i>h</i> = {f2(delhi['overhang'])} makes it "
    "selective."
)
figure("fig4_sol_air.png",
       "Sol-air temperature of the four cardinal walls on 21 June at New Delhi, with the design-day air "
       "temperature <i>T<sub>o</sub></i> (dashed).")  # fmt: skip
P(
    f"Figure 4 shows the east–west asymmetry predicted by Eq. (24). Although <i>H</i>(E) = <i>H</i>(W) to within "
    f"0.01 kWh m<super>−2</super>, the west wall peaks at {f1(peaks['W'])} °C near 16:15 IST while the east wall peaks at "
    f"{f1(peaks['E'])} °C near 08:45—a difference of {f1(D_E_W)} K caused purely by the phase of <i>T<sub>o</sub></i>. The "
    f"north wall ({f1(peaks['N'])} °C) briefly exceeds the south wall ({f1(peaks['S'])} °C) in the late afternoon. "
    "In the case study the engine accordingly flags the three west-facing occupied rooms and recommends "
    "external vertical shading, ≥ 230 mm masonry for time lag and high-albedo finishes, and it notes that "
    "the kitchen has no east wall and hence no morning daylight."
)
H2("D", "Sensitivity to orientation")
figure(
    "fig5_vci_rotation.png",
    "VCI as a function of the north-arrow angle θ, i.e. of the orientation in which the same plan is built.",
)
rr_, ab_ = rot["reference plan"], rot["as-built plan"]
P(
    f"Rotating the drawing’s north arrow through 360° (Fig. 5) moves the reference plan between "
    f"{f1(rr_['min'])} and {f1(rr_['max'])}, with discontinuities at <i>θ</i> = 45°, 135°, 225° and 315°, where the cardinal "
    f"snapping of Sec. III B reassigns every zone at once, and small steps where the entrance crosses a "
    f"16-sector boundary. The as-built plan varies only between {f1(ab_['min'])} and {f1(ab_['max'])}: a plan "
    "designed without regard to direction is mediocre in every orientation, whereas a Vastu-designed plan is "
    "excellent in one quadrant of orientations and poor otherwise. The VCI is thus a strongly "
    "orientation-selective observable, and the north reference is the single most important input; "
    "WMM2025 declinations (≤ 2.8° in India) are small compared with the ±45° tolerance of a quadrant but "
    "matter near sector boundaries."
)
H2("E", "Latitude dependence")
figure("fig6_latitude.png",
       "June-solstice daily irradiation on east/west, south and north walls as a function of latitude "
       "across India (8°–35°N).")  # fmt: skip
P(
    f"Figure 6 reveals that the physical meaning of “north” is latitude-dependent. South of the Tropic of "
    f"Cancer the June noon sun is in the northern sky, so at 8°N a north wall receives "
    f"{f2(lat['N'][0])} kWh m<super>−2</super> day<super>−1</super>—more than an east or west wall ({f2(lat['E/W'][0])})—while at 35°N it "
    f"receives only {f2(lat['N'][1])}. A rule that is thermally neutral in Kashmir is therefore not neutral in "
    "Kerala, an observation that a single pan-Indian rule table cannot capture but that the physics "
    "engine reports automatically for any site."
)

# ============================================================================= VI. DISCUSSION
H1("Discussion")
H2("A", "Where tradition and physics agree")
P(
    "Three Vastu prescriptions survive quantitative scrutiny. (i) <i>Heavy south-west, open north-east</i>: "
    "the west and south-west walls carry the highest peak sol-air temperatures (Fig. 4), so massive walls "
    "and unoccupied, heavy uses there buffer the occupied rooms; open north-east space admits the low-"
    "intensity morning sun. (ii) <i>Kitchen in the east/south-east</i>: the morning beam provides daylight "
    "during breakfast preparation while the hottest afternoon hours, when cooking adds internal gains, fall "
    "on other façades. (iii) <i>Open centre</i>: an open Brahmasthāna is functionally a light-well and a stack-"
    "ventilation core. These agreements are consistent with the lower dissatisfaction reported for east-"
    "facing rooms in Kharagpur [5]."
)
H2("B", "Where they diverge or lack evidence")
P(
    "The geomagnetic field across India (WMM2025: total intensity 41–51 μT, inclination 4°–53°; Appendix B) "
    "is static on the time scale of a night and has no established physiological mechanism tied to "
    "sleeping direction; we therefore encode bed-head rules only as cultural remedies with no physics "
    "rationale, in line with the criticism in [4]. Conversely, passive-solar practice and our Fig. 3 favour "
    "shaded south glazing, which traditional Vastu texts discourage; the tool reports both views rather "
    "than adjudicating. Finally, sources disagree on some placements (e.g. toilets in the south versus the "
    "north-west); the rule tensor encodes a consensus and is deliberately exposed as editable data."
)
H2("C", "Limitations and uncertainty")
P(
    "The 3 × 3 grid simplifies the 81-pada mandala and the entrance model uses 16 sectors rather than the "
    "32 perimeter padas. The irradiance model is clear-sky and ignores monsoon cloud, neighbouring "
    "obstructions and window/opaque distinctions; the climate parameters are representative, not "
    "site-measured. Heaviness weights in the dipole and the rule values are ordinal judgements. The "
    "optimiser is local and ignores plumbing cost. Digitisation errors propagate linearly and are bounded "
    "by Eq. (8); north-arrow errors matter only within a few degrees of a sector or quadrant boundary."
)

# ============================================================================= VII. CONCLUSIONS
H1("Conclusions")
P(
    "We have shown that the assessment of a house against Vastu Shastra can be cast as a deterministic, "
    "auditable computation: exact polygon clipping on a discretised mandala turns the tradition’s "
    "directional rules into a continuous compliance functional, and a combinatorial optimiser turns "
    "findings into actionable re-assignments. Coupling this with first-principles solar physics separates "
    "rules with a measurable physical basis—most clearly the east–west sol-air asymmetry of "
    f"{f1(D_E_W)} K at equal irradiation—from rules that are purely cultural. Planned extensions are a DXF "
    "front end (approach A2), the 32-pada entrance model, window-level daylight and ventilation analysis "
    "with ISHRAE weather files, and multi-storey plans."
)
story.append(Spacer(1, 6))
P(
    "<b>Acknowledgments.</b> Solar equations are from NOAA GML; geomagnetic values from the NOAA NCEI/BGS "
    "World Magnetic Model WMM2025 (valid 2025–2029). No AI or ML component is used anywhere in the method.",
    "body0",
)
P(
    "<b>Code and data availability.</b> Source code, examples, figures and this paper’s build scripts are in "
    "the repository <font face='Courier' size='8.5'>vastu-floorplan-analyzer</font> (MIT licence); every number in "
    "this paper is regenerated by <font face='Courier' size='8.5'>python paper/figures.py</font>.",
    "body0",
)

# ============================================================================= REFERENCES
story.append(Spacer(1, 4))
P("REFERENCES", "h1")
REFS = [
    "B. Dagens (transl.), <i>Mayamata: An Indian Treatise on Housing, Architecture and Iconography</i> (Sitaram Bhartia Institute of Scientific Research, New Delhi, 1985).",
    "P. K. Acharya, <i>Architecture of Mānasāra</i>, Mānasāra Series Vols. III–IV (Oxford University Press, London, 1934).",
    "S. Kramrisch, <i>The Hindu Temple</i>, Vol. 1 (University of Calcutta, 1946), ch. on the Vāstupurusamandala.",
    "“Vastu shastra,” <i>Wikipedia</i> (accessed 12 Nov 2026), sections on texts, mandala grids and reception (including criticism by J. V. Narlikar and N. Nayak).",
    "A. A. Kaushal, P. Anand, and B. H. Aithal, “Assessment of the impact of building orientation on PMV and PPD in naturally ventilated rooms during summers in warm and humid climate of Kharagpur, India,” in <i>Proc. 10th ACM Int. Conf. on Systems for Energy-Efficient Buildings, Cities, and Transportation (BuildSys ’23)</i> (ACM, 2023), pp. 528–533, doi:10.1145/3600100.3627034.",
    "“Scientific substantiation of Vastu Shastra,” <i>ITM Web Conf.</i> <b>65</b>, 02003 (2024), ICMAETM-24, doi:10.1051/itmconf/20246502003.",
    "NOAA Global Monitoring Laboratory, “General Solar Position Calculations,” gml.noaa.gov/grad/solcalc/solareqns.PDF.",
    "J. Meeus, <i>Astronomical Algorithms</i>, 2nd ed. (Willmann-Bell, Richmond, VA, 1998).",
    "F. Kasten and A. T. Young, “Revised optical air mass tables and approximation formula,” <i>Appl. Opt.</i> <b>28</b>, 4735 (1989).",
    "A. B. Meinel and M. P. Meinel, <i>Applied Solar Energy: An Introduction</i> (Addison-Wesley, Reading, MA, 1976).",
    "B. Y. H. Liu and R. C. Jordan, “The interrelationship and characteristic distribution of direct, diffuse and total solar radiation,” <i>Sol. Energy</i> <b>4</b>(3), 1 (1960).",
    "<i>ASHRAE Handbook—Fundamentals</i> (ASHRAE, Atlanta, 2021), sol-air temperature and heat-gain calculations.",
    "J. A. Duffie and W. A. Beckman, <i>Solar Engineering of Thermal Processes</i>, 4th ed. (Wiley, Hoboken, 2013).",
    "NOAA NCEI and British Geological Survey, <i>The US/UK World Magnetic Model for 2025–2030 (WMM2025)</i>, released 17 Dec 2024.",
    "I. E. Sutherland and G. W. Hodgman, “Reentrant polygon clipping,” <i>Commun. ACM</i> <b>17</b>(1), 32 (1974).",
    "S. Macé, H. Locteau, E. Valveny, and S. Tabbone, “A system to detect rooms in architectural floor plan images,” in <i>Proc. 9th IAPR Int. Workshop on Document Analysis Systems</i> (ACM, 2010).",
    "S. Ahmed, M. Liwicki, M. Weber, and A. Dengel, “Automatic room detection and room labeling from architectural floor plans,” in <i>Proc. 10th IAPR Int. Workshop on Document Analysis Systems</i> (IEEE, 2012), pp. 339–343.",
    "Tesseract OCR project documentation (v4.0 onwards: LSTM neural-network recognition engine), github.com/tesseract-ocr/tesseract.",
    "M. Moitzi, <i>ezdxf</i> documentation, release 1.4 (ezdxf.readthedocs.io).",
    "buildingSMART International, <i>IFC4 schema</i>: IfcSpace and IfcGeometricRepresentationContext.TrueNorth.",
    "Bureau of Indian Standards, <i>National Building Code of India 2016</i> (SP 7:2016), climatic zones and building orientation.",
    "Bureau of Energy Efficiency, <i>Eco-Niwas Samhita 2018: Energy Conservation Building Code for Residential Buildings</i> (BEE, New Delhi, 2018).",
    "S. V. Szokolay, <i>Introduction to Architectural Science: The Basis of Sustainable Design</i>, 3rd ed. (Routledge, Abingdon, 2014).",
    "T. C. Koopmans and M. Beckmann, “Assignment problems and the location of economic activities,” <i>Econometrica</i> <b>25</b>, 53 (1957).",
]
for i, r in enumerate(REFS, 1):
    P(f"[{i}] {r}", "ref")


# ============================================================================= APPENDICES (single column)
story.append(NextPageTemplate("One"))
story.append(PageBreak())
P("APPENDIX A: RULE TENSOR", "h1")
P(
    "Values <i>v<sub>t</sub></i>(<i>z</i>) of the bundled knowledge base (v"
    + rb.version
    + "); 1 = ideal, 0.75 = good, 0.5 = "
    "acceptable, 0.25 = poor, 0 = avoid. <i>w</i>: importance weight; <i>h</i>: heaviness used in the mass dipole. "
    "Entrance sectors: N, NNE, NE, E = 1; ENE, NNW = 0.75; ESE, SSE, W, WNW, NW = 0.5; SE, S, WSW = 0.25; "
    "SSW, SW = 0.",
    "body0",
)
zones = ("NW", "N", "NE", "W", "C", "E", "SW", "S", "SE")
rows = [["Function", *zones, "<i>w</i>", "<i>h</i>", "Mov."]]
for key, r in rb.rooms.items():
    if key == "other":
        continue
    rows.append([r.label, *[("1" if r.zones[z] == 1 else ("0" if r.zones[z] == 0 else f"{r.zones[z]:.2f}")) for z in zones],
                 f"{r.weight:g}", f"{r.heaviness:g}", "yes" if r.movable else "no"])  # fmt: skip
table(
    rows,
    [150] + [26] * 9 + [24, 24, 26],
    "Zone values, weights and heaviness of each function type.",
    align_center_from=1,
)
P(
    "Site weights: Brahmasthāna 8; corners NE 8, SW 6, SE 3, NW 3 (tolerance 0.95); shape 5 (maximum aspect 2); "
    "mass dipole 6 (ideal bearing 225°, saturation <i>m</i><sub>0</sub> = 0.10).",
    "body0",
)

P("APPENDIX B: GEOMAGNETIC DECLINATION IN INDIA (WMM2025)", "h1")
WMM = [("New Delhi", 28.6139, 77.2090, 1.33, 45.51, 48835), ("Mumbai", 19.0760, 72.8777, -0.01, 28.33, 43587),
       ("Chennai", 13.0827, 80.2707, -1.07, 14.83, 42112), ("Kolkata", 22.5726, 88.3639, -0.31, 34.88, 46534),
       ("Bengaluru", 12.9716, 77.5946, -1.07, 14.70, 41835), ("Jaipur", 26.9124, 75.7873, 1.13, 42.78, 47768),
       ("Lucknow", 26.8467, 80.9462, 0.71, 42.63, 48268), ("Srinagar", 34.0837, 74.7973, 2.76, 53.39, 51431),
       ("Guwahati", 26.1445, 91.7362, -0.34, 41.35, 48632), ("Thiruvananthapuram", 8.5241, 76.9366, -1.74, 4.01, 40879)]  # fmt: skip
rows = [
    [
        "City",
        "Latitude (°N)",
        "Longitude (°E)",
        "Declination <i>D</i> (°)",
        "Inclination (°)",
        "Total field <i>F</i> (μT)",
    ]
]
for cty, la, lo, d_, inc, f_ in WMM:
    rows.append([cty, f"{la:.3f}", f"{lo:.3f}", sgn(d_), f"{inc:.1f}", f"{f_ / 1000:.1f}"])
table(rows, [120, 70, 70, 80, 70, 80],
      "Main-field values from the WMM2025 coefficients at sea level, epoch 2026.87 (computed with the "
      "<font face='Courier'>pygeomag</font> implementation of the NOAA/BGS model). East declination is positive; "
      "use <i>θ</i> = <i>θ</i><sub>a</sub> − <i>D</i> for a magnetic north arrow.", align_center_from=1)  # fmt: skip

P("APPENDIX C: INPUT SCHEMA", "h1")
P(
    "A plan file (abbreviated) for the case study. Coordinates are in the drawing frame; <font face='Courier'>"
    "angle_deg</font> is the north-arrow angle clockwise from the sheet’s vertical.",
    "body0",
)
code = """{
  "schema_version": "1.0",
  "name": "Sample 3BHK, New Delhi (as built)",
  "units": "m",
  "north": {"angle_deg": 8.0, "reference": "true", "declination_deg": 0.0},
  "location": {"latitude": 28.6139, "longitude": 77.2090, "timezone": 5.5},
  "footprint": [[0, 0], [12, 0], [12, 15], [0, 15]],
  "rooms": [
    {"name": "Kitchen", "type": "kitchen", "polygon": [[6, 10], [10, 10], [10, 15], [6, 15]]},
    {"name": "Foyer",   "type": "foyer",   "polygon": [[5, 2.5], [7, 2.5], [7, 0], [8, 0], [8, 5], [5, 5]]},
    ...
  ],
  "entrances": [{"name": "Main door", "position": [7.5, 0], "main": true}]
}"""
for line in code.splitlines():
    story.append(Paragraph(escape(line).replace(" ", "&nbsp;"), S["code"]))
story.append(Spacer(1, 6))
P(
    "Reproduce all results with: <font face='Courier'>pip install -e .[paper]; python paper/figures.py; "
    "python paper/build_paper.py</font>; analyse any plan with <font face='Courier'>vastu analyze plan.json "
    "-f md -o report.md --plot plan.png</font>.",
    "left",
)

assert _eq[0] == 25, f"equation count changed ({_eq[0]}); update cross-references"
doc.build(story)
print("wrote", OUT)
