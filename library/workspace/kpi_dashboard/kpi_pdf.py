from datetime import datetime
from io import BytesIO

from reportlab.graphics.charts.barcharts import HorizontalBarChart
from reportlab.graphics.charts.legends import Legend
from reportlab.graphics.shapes import Drawing
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas
from reportlab.platypus import (
    KeepTogether, PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle,
)

BRAND = colors.HexColor("#A50034")
BRAND_DARK = colors.HexColor("#700023")
HEADER_BG = colors.HexColor("#F4E4E9")
STRIPE_BG = colors.HexColor("#F8F9FB")
GRID = colors.HexColor("#D9DDE3")
TEXT = colors.HexColor("#1D2939")
MUTED = colors.HexColor("#667085")

TONE = {  # (background, text)
    "blue": (colors.HexColor("#D9E8FF"), colors.HexColor("#1849A9")),
    "green": (colors.HexColor("#D1FADF"), colors.HexColor("#05603A")),
    "yellow": (colors.HexColor("#FEF0C7"), colors.HexColor("#93370D")),
    "red": (colors.HexColor("#FDE2E1"), colors.HexColor("#B42318")),
    "brand": (HEADER_BG, BRAND_DARK),
}

GOOD_COMPLETION = 0.8
OK_COMPLETION = 0.5

PAGE = landscape(A4)
MARGIN = 14 * mm
CONTENT_WIDTH = PAGE[0] - 2 * MARGIN

S_CELL = ParagraphStyle("cell", fontName="Helvetica", fontSize=9.5, leading=12, textColor=TEXT, alignment=TA_LEFT)
S_NOTE = ParagraphStyle("note", fontName="Helvetica-Oblique", fontSize=8, leading=10.5, textColor=MUTED)
S_H2 = ParagraphStyle("h2", fontName="Helvetica-Bold", fontSize=12.5, leading=16, textColor=BRAND_DARK, spaceAfter=4, keepWithNext=1)


# ---------------------------------------------------------------- helpers
def _completion(emp):
    return (emp["completed"] / emp["totalAssigned"]) if emp["totalAssigned"] else None


def _completion_text(value):
    return "-" if value is None else f"{round(value * 100)}%"


def _completion_tone(value):
    if value is None:
        return None
    if value >= GOOD_COMPLETION:
        return "green"
    if value >= OK_COMPLETION:
        return "yellow"
    return "red"


def _subtitle(period_label, count):
    return (
        f"Period: {period_label} (last 30 days)   |   "
        f"Generated: {datetime.now().strftime('%d-%m-%Y %H:%M')}   |   "
        f"{count} employee{'s' if count != 1 else ''}"
    )


def _title_bar(title, subtitle):
    bar = Table(
        [[Paragraph(f'<font color="white" size="16"><b>{title}</b></font>', S_CELL)]],
        colWidths=[CONTENT_WIDTH],
        rowHeights=[11 * mm],
    )
    bar.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), BRAND),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
    ]))
    return [bar, Spacer(1, 2 * mm), Paragraph(subtitle, S_NOTE), Spacer(1, 4 * mm)]


class _NumberedCanvas(canvas.Canvas):
    """Footer on every page: 'RnD Portal | Page x of y | date'."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_pages = []

    def showPage(self):
        self._saved_pages.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        total = len(self._saved_pages)
        for state in self._saved_pages:
            self.__dict__.update(state)
            self._draw_footer(total)
            super().showPage()
        super().save()

    def _draw_footer(self, total):
        self.setFont("Helvetica", 8)
        self.setFillColor(MUTED)
        y = 8 * mm
        self.drawString(MARGIN, y, "RnD Portal")
        self.drawCentredString(PAGE[0] / 2, y, f"Page {self._pageNumber} of {total}")
        self.drawRightString(PAGE[0] - MARGIN, y, datetime.now().strftime("%d-%m-%Y"))
        self.setStrokeColor(GRID)
        self.line(MARGIN, y + 4 * mm, PAGE[0] - MARGIN, y + 4 * mm)


def _render(story, title):
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=PAGE, leftMargin=MARGIN, rightMargin=MARGIN,
        topMargin=12 * mm, bottomMargin=16 * mm, title=title, author="RnD Portal",
    )
    doc.build(story, canvasmaker=_NumberedCanvas)
    buffer.seek(0)
    return buffer


# ---------------------------------------------------------------- tables
def _employee_table(employees):
    head1 = ["No", "Name", "Role", "Total\nAssigned", "Completed", "Pending", "Overdue", "Completion", "Avg. Resolution Time", ""]
    head2 = ["", "", "", "", "", "", "", "", "Days", "Hours"]
    data = [head1, head2]

    for i, emp in enumerate(employees, start=1):
        avg_days = emp["avgResolutionDays"] or 0
        data.append([
            str(i), emp["name"], emp["role"], emp["totalAssigned"], emp["completed"],
            emp["pending"], emp["overdue"], _completion_text(_completion(emp)),
            f"{avg_days:.1f}", f"{avg_days * 24:.1f}",
        ])

    total_assigned = sum(e["totalAssigned"] for e in employees)
    completed = sum(e["completed"] for e in employees)
    rate = (completed / total_assigned) if total_assigned else None
    data.append([
        "", "TOTAL", "", total_assigned, completed, sum(e["pending"] for e in employees),
        sum(e["overdue"] for e in employees), _completion_text(rate), "", "",
    ])

    widths = [11, 55, 36, 26, 26, 22, 22, 28, 24, 24]
    scale = CONTENT_WIDTH / (sum(widths) * mm)
    table = Table(data, colWidths=[w * mm * scale for w in widths], repeatRows=2)

    last = len(data) - 1
    style = [
        ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
        ("FONTSIZE", (0, 0), (-1, -1), 9.5),
        ("TEXTCOLOR", (0, 0), (-1, -1), TEXT),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ALIGN", (1, 0), (2, -1), "LEFT"),
        ("LEFTPADDING", (1, 0), (2, -1), 8),
        ("TOPPADDING", (0, 2), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 2), (-1, -1), 5),
        ("GRID", (0, 0), (-1, -1), 0.5, GRID),
        # header (two rows)
        ("BACKGROUND", (0, 0), (-1, 1), HEADER_BG),
        ("TEXTCOLOR", (0, 0), (-1, 1), BRAND_DARK),
        ("FONTNAME", (0, 0), (-1, 1), "Helvetica-Bold"),
        ("LINEBELOW", (0, 1), (-1, 1), 1.4, BRAND),
        ("SPAN", (8, 0), (9, 0)),
        *[("SPAN", (c, 0), (c, 1)) for c in range(0, 8)],
        # names in bold
        ("FONTNAME", (1, 2), (1, last - 1), "Helvetica-Bold"),
        # total row
        ("BACKGROUND", (0, last), (-1, last), HEADER_BG),
        ("FONTNAME", (0, last), (-1, last), "Helvetica-Bold"),
        ("TEXTCOLOR", (0, last), (-1, last), BRAND_DARK),
        ("LINEABOVE", (0, last), (-1, last), 1.4, BRAND),
    ]
    for r in range(2, last):
        if (r - 2) % 2 == 1:
            style.append(("BACKGROUND", (0, r), (-1, r), STRIPE_BG))

        emp = employees[r - 2]
        tone = _completion_tone(_completion(emp))
        if tone:
            bg, fg = TONE[tone]
            style += [("BACKGROUND", (7, r), (7, r), bg), ("TEXTCOLOR", (7, r), (7, r), fg), ("FONTNAME", (7, r), (7, r), "Helvetica-Bold")]
        if emp["overdue"] > 0:
            bg, fg = TONE["red"]
            style += [("BACKGROUND", (6, r), (6, r), bg), ("TEXTCOLOR", (6, r), (6, r), fg), ("FONTNAME", (6, r), (6, r), "Helvetica-Bold")]

    table.setStyle(TableStyle(style))
    return table


def _legend_note():
    return Paragraph(
        "<b>How to read this:</b> Completion = Completed / Total Assigned "
        f"(green &ge; {int(GOOD_COMPLETION * 100)}%, yellow {int(OK_COMPLETION * 100)}-{int(GOOD_COMPLETION * 100) - 1}%, "
        f"red &lt; {int(OK_COMPLETION * 100)}%). Overdue above 0 is highlighted in red. "
        "Avg. Resolution Time = average time to close an issue. \"-\" = nothing assigned in this period.",
        S_NOTE,
    )


def _empty_notice():
    return Paragraph("No employee data for this period.", ParagraphStyle("e", parent=S_NOTE, fontSize=11, spaceBefore=12))


# ---------------------------------------------------------------- Individual
def build_individual_pdf(employees, period_label):
    story = _title_bar("KPI DASHBOARD  -  Individual Performance", _subtitle(period_label, len(employees)))
    if employees:
        story += [_employee_table(employees), Spacer(1, 4 * mm), _legend_note()]
    else:
        story.append(_empty_notice())
    return _render(story, "KPI Dashboard - Individual Performance")


# ---------------------------------------------------------------- Team
def _stat_cards(employees):
    total_assigned = sum(e["totalAssigned"] for e in employees)
    completed = sum(e["completed"] for e in employees)
    rate = (completed / total_assigned) if total_assigned else None
    cards = [
        ("TOTAL ASSIGNED", total_assigned, "blue"),
        ("COMPLETED", completed, "green"),
        ("PENDING", sum(e["pending"] for e in employees), "yellow"),
        ("OVERDUE", sum(e["overdue"] for e in employees), "red"),
        ("TEAM COMPLETION RATE", _completion_text(rate), "brand"),
    ]

    labels, values, style = [], [], [
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("ROWBACKGROUNDS", (0, 0), (-1, -1), [None]),
    ]
    for i, (label, value, tone) in enumerate(cards):
        bg, fg = TONE[tone]
        labels.append(Paragraph(f'<font size="7.5" color="{fg.hexval()}"><b>{label}</b></font>', S_CELL))
        values.append(Paragraph(f'<font size="22" color="{fg.hexval()}"><b>{value}</b></font>', S_CELL))
        style += [
            ("BACKGROUND", (i, 0), (i, 1), bg),
            ("LINEBEFORE", (i, 0), (i, 1), 3, fg),
            ("LEFTPADDING", (i, 0), (i, 1), 9),
        ]

    # small gaps between the cards are made by white vertical lines
    gap = 2.5
    style += [("LINEAFTER", (i, 0), (i, 1), gap, colors.white) for i in range(len(cards) - 1)]
    table = Table([labels, values], colWidths=[CONTENT_WIDTH / len(cards)] * len(cards), rowHeights=[8 * mm, 14 * mm])
    table.setStyle(TableStyle(style))
    return table


def _leaderboard(employees):
    ranked = sorted(
        employees,
        key=lambda e: ((_completion(e) or 0), e["completed"]),
        reverse=True,
    )
    data = [["Rank", "Name", "Role", "Completed / Assigned", "Completion"]]
    for i, emp in enumerate(ranked, start=1):
        data.append([str(i), emp["name"], emp["role"], f"{emp['completed']} / {emp['totalAssigned']}", _completion_text(_completion(emp))])

    widths = [18, 70, 45, 55, 40]
    scale = CONTENT_WIDTH / (sum(widths) * mm)
    table = Table(data, colWidths=[w * mm * scale for w in widths], repeatRows=1)
    style = [
        ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
        ("FONTSIZE", (0, 0), (-1, -1), 9.5),
        ("TEXTCOLOR", (0, 0), (-1, -1), TEXT),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("ALIGN", (1, 0), (2, -1), "LEFT"),
        ("LEFTPADDING", (1, 0), (2, -1), 8),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 1), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 1), (-1, -1), 4),
        ("GRID", (0, 0), (-1, -1), 0.5, GRID),
        ("BACKGROUND", (0, 0), (-1, 0), HEADER_BG),
        ("TEXTCOLOR", (0, 0), (-1, 0), BRAND_DARK),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("LINEBELOW", (0, 0), (-1, 0), 1.4, BRAND),
        ("FONTNAME", (1, 1), (1, -1), "Helvetica-Bold"),
    ]
    for r, emp in enumerate(ranked, start=1):
        if r % 2 == 0:
            style.append(("BACKGROUND", (0, r), (-1, r), STRIPE_BG))
        tone = _completion_tone(_completion(emp))
        if tone:
            bg, fg = TONE[tone]
            style += [("BACKGROUND", (4, r), (4, r), bg), ("TEXTCOLOR", (4, r), (4, r), fg), ("FONTNAME", (4, r), (4, r), "Helvetica-Bold")]
    table.setStyle(TableStyle(style))
    return table


def _stacked_chart(employees):
    # Horizontal bars are plotted bottom-up, so feed them reversed to get the
    # first employee at the top.
    employees = list(reversed(employees))
    n = len(employees)
    height = max(66 * mm, min(110 * mm, (18 + 9 * n) * mm * 0.9))
    width = CONTENT_WIDTH
    drawing = Drawing(width, height)

    chart = HorizontalBarChart()
    chart.x, chart.y = 70, 40
    chart.width, chart.height = width - 90, height - 52
    chart.data = [
        [e["completed"] for e in employees],
        [e["pending"] for e in employees],
        [e["overdue"] for e in employees],
    ]
    chart.categoryAxis.categoryNames = [e["name"] for e in employees]
    chart.categoryAxis.style = "stacked"
    chart.categoryAxis.labels.fontName = "Helvetica"
    chart.categoryAxis.labels.fontSize = 8.5
    chart.categoryAxis.labels.boxAnchor = "e"
    chart.categoryAxis.labels.dx = -4
    chart.categoryAxis.strokeColor = GRID

    peak = max([e["totalAssigned"] for e in employees] + [1])
    chart.valueAxis.valueMin = 0
    chart.valueAxis.valueMax = peak + max(1, round(peak * 0.08))
    chart.valueAxis.labels.fontName = "Helvetica"
    chart.valueAxis.labels.fontSize = 8
    chart.valueAxis.gridStrokeColor = GRID
    chart.valueAxis.visibleGrid = 1
    chart.valueAxis.strokeColor = GRID

    chart.groupSpacing = 6
    chart.barWidth = 10
    series_colors = [colors.HexColor("#12B76A"), colors.HexColor("#F79009"), colors.HexColor("#F04438")]
    for i, color in enumerate(series_colors):
        chart.bars[i].fillColor = color
        chart.bars[i].strokeColor = colors.white
        chart.bars[i].strokeWidth = 0.4
    drawing.add(chart)

    legend = Legend()
    legend.x, legend.y = width / 2 - 90, 6
    legend.alignment = "right"
    legend.fontName = "Helvetica"
    legend.fontSize = 8.5
    legend.columnMaximum = 1
    legend.deltax = 70
    legend.dxTextSpace = 4
    legend.boxAnchor = "sw"
    legend.colorNamePairs = list(zip(series_colors, ["Completed", "Pending", "Overdue"]))
    drawing.add(legend)
    return drawing


def build_team_pdf(employees, period_label):
    story = _title_bar("KPI DASHBOARD  -  Team Summary", _subtitle(period_label, len(employees)))
    story.append(_stat_cards(employees))
    story.append(Spacer(1, 6 * mm))

    if employees:
        story.append(KeepTogether([
            Paragraph("Completed vs Pending vs Overdue per Person", S_H2),
            _stacked_chart(employees),
        ]))
        story.append(Spacer(1, 4 * mm))
        story.append(Paragraph("Completion Rate Leaderboard", S_H2))
        story.append(_leaderboard(employees))

        story.append(PageBreak())
        story += _title_bar("KPI DASHBOARD  -  Individual Performance", _subtitle(period_label, len(employees)))
        story += [_employee_table(employees), Spacer(1, 4 * mm), _legend_note()]
    else:
        story.append(_empty_notice())
    return _render(story, "KPI Dashboard - Team Summary")
