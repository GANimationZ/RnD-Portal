"""Builds KPI Dashboard PDF files with reportlab.

Mirrors kpi_excel.py: same columns, same color scheme (yellow title,
gray-blue header, light blue data rows), so the PDF and Excel exports for
the same month show the same numbers in a visually consistent style.
"""

from io import BytesIO

from reportlab.lib import colors
from reportlab.lib.pagesizes import landscape, A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer

TITLE_FILL = colors.HexColor("#FFFF00")   # yellow, matches kpi_excel.py
HEADER_FILL = colors.HexColor("#B4BBC3")  # gray-blue
DATA_FILL = colors.HexColor("#DAE3F3")    # light blue
GRID_COLOR = colors.black

TITLE_STYLE = ParagraphStyle("title", fontName="Helvetica-Bold", fontSize=14, alignment=1)

INDIVIDUAL_COLUMNS = [
    "No", "Name", "Role", "Total\nAssigned", "Completed",
    "Pending", "Overdue", "Completion", "Avg Resolution\n(Days)", "Avg Resolution\n(Hours)",
]
TEAM_SUMMARY_COLUMNS = ["Total Assigned", "Completed", "Pending", "Overdue", "Team Completion Rate (%)"]


def _employee_row(idx, emp):
    avg_days = emp["avgResolutionDays"]
    avg_hours = round(avg_days * 24, 1)
    completion = round((emp["completed"] / emp["totalAssigned"]) * 100) if emp["totalAssigned"] else 0
    return [
        str(idx), emp["name"], emp["role"], str(emp["totalAssigned"]), str(emp["completed"]),
        str(emp["pending"]), str(emp["overdue"]), f"{completion}%", str(avg_days), str(avg_hours),
    ]


def _styled_table(data, header_rows=1, col_widths=None):
    table = Table(data, colWidths=col_widths, repeatRows=header_rows)
    style = [
        ("GRID", (0, 0), (-1, -1), 0.5, GRID_COLOR),
        ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("BACKGROUND", (0, 0), (-1, header_rows - 1), HEADER_FILL),
        ("FONTNAME", (0, 0), (-1, header_rows - 1), "Helvetica-Bold"),
        ("BACKGROUND", (0, header_rows), (-1, -1), DATA_FILL),
    ]
    table.setStyle(TableStyle(style))
    return table


def _title_paragraph(text):
    return Paragraph(text, TITLE_STYLE)


def _document(download_name_hint=None):
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=landscape(A4),
        leftMargin=12 * mm, rightMargin=12 * mm,
        topMargin=12 * mm, bottomMargin=12 * mm,
    )
    return buffer, doc


def build_individual_pdf(employees):
    """employees: same list-of-dicts shape as kpi_excel.build_individual_workbook."""
    buffer, doc = _document()

    elements = [_title_paragraph("KPI DASHBOARD"), Spacer(1, 10)]
    rows = [INDIVIDUAL_COLUMNS] + [_employee_row(i + 1, e) for i, e in enumerate(employees)]
    elements.append(_styled_table(rows))

    doc.build(elements)
    buffer.seek(0)
    return buffer


def build_team_pdf(employees):
    """2 sections on one PDF: Team Summary totals, then the same
    per-employee table as build_individual_pdf -- mirrors the 2 sheets in
    kpi_excel.build_team_workbook, since a PDF has no concept of sheets."""
    buffer, doc = _document()

    totals = {
        "totalAssigned": sum(e["totalAssigned"] for e in employees),
        "completed": sum(e["completed"] for e in employees),
        "pending": sum(e["pending"] for e in employees),
        "overdue": sum(e["overdue"] for e in employees),
    }
    completion_rate = (
        round((totals["completed"] / totals["totalAssigned"]) * 100)
        if totals["totalAssigned"] else 0
    )
    summary_rows = [
        TEAM_SUMMARY_COLUMNS,
        [str(totals["totalAssigned"]), str(totals["completed"]), str(totals["pending"]),
         str(totals["overdue"]), f"{completion_rate}%"],
    ]

    elements = [
        _title_paragraph("KPI DASHBOARD - TEAM SUMMARY"),
        Spacer(1, 10),
        _styled_table(summary_rows),
        Spacer(1, 24),
        _title_paragraph("PER EMPLOYEE"),
        Spacer(1, 10),
    ]
    detail_rows = [INDIVIDUAL_COLUMNS] + [_employee_row(i + 1, e) for i, e in enumerate(employees)]
    elements.append(_styled_table(detail_rows))

    doc.build(elements)
    buffer.seek(0)
    return buffer
