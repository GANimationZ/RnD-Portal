"""Builds and reads KPI Dashboard Excel files with openpyxl.

Styling mirrors the original reference file:
- "KPI DASHBOARD" title row: full merge, yellow background, bold.
- Table header: gray-blue background, bold, centered, thin border all sides.
- Data rows: light blue background, thin border all sides.
"""

from io import BytesIO
from datetime import datetime

from openpyxl import Workbook, load_workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

FONT_NAME = "Calibri"
FONT_SIZE = 12

TITLE_FILL = PatternFill("solid", fgColor="FFFF00")           # yellow
HEADER_FILL = PatternFill("solid", fgColor="B4BBC3")          # gray-blue, matches reference file
DATA_FILL = PatternFill("solid", fgColor="DAE3F3")            # light blue, matches reference file

THIN = Side(style="thin", color="000000")
BORDER_ALL = Border(top=THIN, bottom=THIN, left=THIN, right=THIN)

CENTER = Alignment(horizontal="center", vertical="center")
CENTER_H_ONLY = Alignment(horizontal="center")

# Urutan kolom persis seperti file referensi.
COLUMNS = [
    "No", "Name", "Role", "Total Assigned", "Completed",
    "Pending", "Overdue", "Completion", "Avg Resolution", "Avg Resolution",
]
SUB_HEADERS = {9: "(Days)", 10: "(Hours)"}  # columns I & J (1-indexed)

# Lebar kolom persis seperti file referensi (kolom yang tidak disebut dibiarkan default Excel).
COLUMN_WIDTHS = {
    "B": 18.25, "C": 15.5, "D": 18.125, "E": 9.875,
    "H": 11.125, "I": 17.25, "J": 19.375,
}


def _style_title_row(ws, last_col):
    ws.merge_cells(start_row=1, start_column=1, end_row=2, end_column=last_col)
    for row in ws.iter_rows(min_row=1, max_row=2, min_col=1, max_col=last_col):
        for cell in row:
            cell.fill = TITLE_FILL
            cell.border = BORDER_ALL
    title_cell = ws.cell(row=1, column=1)
    title_cell.value = "KPI DASHBOARD"
    title_cell.font = Font(name=FONT_NAME, size=FONT_SIZE, bold=True)
    title_cell.alignment = CENTER


def _style_header_rows(ws, last_col):
    # Baris 3 & 4: kolom A-H merge vertikal (satu header, 2 baris tinggi),
    # Columns I & J are NOT merged (matches the reference file: "Avg
    # Resolution" is repeated in I3 & J3, then "(Days)"/"(Hours)" in row 4).
    for col in range(1, last_col + 1):
        header_cell = ws.cell(row=3, column=col)
        header_cell.value = COLUMNS[col - 1]
        header_cell.font = Font(name=FONT_NAME, size=FONT_SIZE, bold=True)
        header_cell.alignment = CENTER
        header_cell.fill = HEADER_FILL
        header_cell.border = BORDER_ALL

        sub_cell = ws.cell(row=4, column=col)
        sub_cell.border = BORDER_ALL
        if col in SUB_HEADERS:
            sub_cell.value = SUB_HEADERS[col]
            sub_cell.font = Font(name=FONT_NAME, size=FONT_SIZE, bold=True)
            sub_cell.alignment = CENTER
            sub_cell.fill = HEADER_FILL
        else:
            ws.merge_cells(start_row=3, start_column=col, end_row=4, end_column=col)


def _write_data_rows(ws, rows, start_row=5):
    for offset, row_values in enumerate(rows):
        r = start_row + offset
        for col, value in enumerate(row_values, start=1):
            cell = ws.cell(row=r, column=col, value=value)
            cell.font = Font(name=FONT_NAME, size=FONT_SIZE)
            cell.fill = DATA_FILL
            cell.border = BORDER_ALL
            if col == 1:  # "No" column is centered, matches reference
                cell.alignment = CENTER_H_ONLY


def _apply_column_widths(ws):
    for col_letter, width in COLUMN_WIDTHS.items():
        ws.column_dimensions[col_letter].width = width


def _employee_row(idx, emp):
    avg_days = emp["avgResolutionDays"]
    avg_hours = round(avg_days * 24, 1)
    completion = round((emp["completed"] / emp["totalAssigned"]) * 100) if emp["totalAssigned"] else 0
    return [
        idx, emp["name"], emp["role"], emp["totalAssigned"], emp["completed"],
        emp["pending"], emp["overdue"], completion, avg_days, avg_hours,
    ]


def build_individual_workbook(employees):
    """employees: list of dict dengan key name, role, totalAssigned, completed,
    pending, overdue, avgResolutionDays (persis field yang sudah dipakai di JS)."""
    wb = Workbook()
    ws = wb.active
    ws.title = "Per Employee"

    last_col = len(COLUMNS)
    _style_title_row(ws, last_col)
    _style_header_rows(ws, last_col)

    rows = [_employee_row(i + 1, emp) for i, emp in enumerate(employees)]
    _write_data_rows(ws, rows)
    _apply_column_widths(ws)

    return wb


def build_team_workbook(employees):
    """2 sheet: 'Team Summary' (total tim) + 'Per Employee' (detail, style sama)."""
    wb = Workbook()

    ws_summary = wb.active
    ws_summary.title = "Team Summary"

    totals_columns = ["Total Assigned", "Completed", "Pending", "Overdue", "Team Completion Rate (%)"]
    last_col = len(totals_columns)

    ws_summary.merge_cells(start_row=1, start_column=1, end_row=2, end_column=last_col)
    for row in ws_summary.iter_rows(min_row=1, max_row=2, min_col=1, max_col=last_col):
        for cell in row:
            cell.fill = TITLE_FILL
            cell.border = BORDER_ALL
    title_cell = ws_summary.cell(row=1, column=1)
    title_cell.value = "KPI DASHBOARD - TEAM SUMMARY"
    title_cell.font = Font(name=FONT_NAME, size=FONT_SIZE, bold=True)
    title_cell.alignment = CENTER

    for col, label in enumerate(totals_columns, start=1):
        cell = ws_summary.cell(row=3, column=col, value=label)
        cell.font = Font(name=FONT_NAME, size=FONT_SIZE, bold=True)
        cell.alignment = CENTER
        cell.fill = HEADER_FILL
        cell.border = BORDER_ALL

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
    values = [totals["totalAssigned"], totals["completed"], totals["pending"], totals["overdue"], completion_rate]
    for col, value in enumerate(values, start=1):
        cell = ws_summary.cell(row=4, column=col, value=value)
        cell.font = Font(name=FONT_NAME, size=FONT_SIZE)
        cell.fill = DATA_FILL
        cell.border = BORDER_ALL

    for col_letter in ["A", "B", "C", "D", "E"]:
        ws_summary.column_dimensions[col_letter].width = 20

    # Second sheet: per-employee detail, same style as the Individual export.
    ws_detail = wb.create_sheet("Per Employee")
    last_col_detail = len(COLUMNS)
    _style_title_row(ws_detail, last_col_detail)
    _style_header_rows(ws_detail, last_col_detail)
    rows = [_employee_row(i + 1, emp) for i, emp in enumerate(employees)]
    _write_data_rows(ws_detail, rows)
    _apply_column_widths(ws_detail)

    return wb


def workbook_to_bytes(wb):
    buffer = BytesIO()
    wb.save(buffer)
    buffer.seek(0)
    return buffer


def parse_employee_workbook(file_stream):
    """Baca file hasil export (atau format sejenis) balik jadi list of dict.
    Data dimulai di baris 5 (setelah judul + header 2 baris)."""
    wb = load_workbook(file_stream, data_only=True)
    sheet_name = "Per Employee" if "Per Employee" in wb.sheetnames else wb.sheetnames[0]
    ws = wb[sheet_name]

    rows = []
    for row in ws.iter_rows(min_row=5, values_only=True):
        if not row or row[1] is None:  # empty Name column -> stop reading
            continue
        _, name, role, total_assigned, completed, pending, overdue, completion, avg_days, avg_hours = row[:10]
        rows.append({
            "name": name,
            "role": role,
            "totalAssigned": int(total_assigned or 0),
            "completed": int(completed or 0),
            "pending": int(pending or 0),
            "overdue": int(overdue or 0),
            "avgResolutionDays": float(avg_days) if avg_days is not None else (
                round(float(avg_hours) / 24, 2) if avg_hours is not None else 0
            ),
        })
    return rows