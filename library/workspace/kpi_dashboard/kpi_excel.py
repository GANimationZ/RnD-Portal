from datetime import datetime
from io import BytesIO

from openpyxl import Workbook, load_workbook
from openpyxl.chart import BarChart, Reference, Series
from openpyxl.formatting.rule import CellIsRule, DataBarRule
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter

FONT_NAME = "Calibri"

# ---- Palette ----
BRAND = "A50034"
BRAND_DARK = "700023"
HEADER_BG = "F4E4E9"
STRIPE_BG = "F8F9FB"
BORDER_COLOR = "D9DDE3"
TEXT = "1D2939"
MUTED = "667085"

TONE = {  # (background, text)
    "blue": ("D9E8FF", "1849A9"),
    "green": ("D1FADF", "05603A"),
    "yellow": ("FEF0C7", "93370D"),
    "red": ("FDE2E1", "B42318"),
}

THIN = Side(style="thin", color=BORDER_COLOR)
BORDER_ALL = Border(top=THIN, bottom=THIN, left=THIN, right=THIN)
HEADER_BORDER = Border(top=THIN, left=THIN, right=THIN, bottom=Side(style="medium", color=BRAND))

# Completion thresholds (used by the colour rules AND explained in the legend)
GOOD_COMPLETION = 0.8
OK_COMPLETION = 0.5

# Column order of the "Per Employee" sheet -- see the compatibility note.
COLUMNS = [
    "No", "Name", "Role", "Total Assigned", "Completed", "Available",
    "Pending", "Overdue", "Completion", "Avg Resolution", "Avg Resolution",
]
COLUMN_WIDTHS = {"A": 6, "B": 24, "C": 18, "D": 15, "E": 13, "F": 12, "G": 12, "H": 12, "I": 14, "J": 12, "K": 12}
FIRST_DATA_ROW = 5


def _fill(color):
    return PatternFill("solid", fgColor=color)


def _font(size=11, bold=False, color=TEXT, italic=False):
    return Font(name=FONT_NAME, size=size, bold=bold, color=color, italic=italic)


def period_label_from_key(month_key=None):
    """"2026-10" -> "October 2026" (defaults to the current month)."""
    try:
        return datetime.strptime(month_key, "%Y-%m").strftime("%B %Y")
    except (TypeError, ValueError):
        return datetime.now().strftime("%B %Y")


def _subtitle(period_label, count):
    return (
        f"Period: {period_label}   |   "
        f"Generated: {datetime.now().strftime('%d-%m-%Y %H:%M')}   |   "
        f"{count} employee{'s' if count != 1 else ''}"
    )


def _title_block(ws, title, subtitle, last_col):
    """Row 1 = coloured title bar, row 2 = subtitle."""
    ws.merge_cells(start_row=1, start_column=1, end_row=1, end_column=last_col)
    ws.merge_cells(start_row=2, start_column=1, end_row=2, end_column=last_col)

    for col in range(1, last_col + 1):
        ws.cell(row=1, column=col).fill = _fill(BRAND)

    title_cell = ws.cell(row=1, column=1, value=title)
    title_cell.font = _font(16, bold=True, color="FFFFFF")
    title_cell.alignment = Alignment(horizontal="left", vertical="center", indent=1)
    ws.row_dimensions[1].height = 32

    sub_cell = ws.cell(row=2, column=1, value=subtitle)
    sub_cell.font = _font(10, italic=True, color=MUTED)
    sub_cell.alignment = Alignment(horizontal="left", vertical="center", indent=1)
    ws.row_dimensions[2].height = 20


def _page_setup(ws, landscape=True, title_rows=None):
    ws.sheet_view.showGridLines = False
    ws.page_setup.orientation = "landscape" if landscape else "portrait"
    ws.page_setup.paperSize = ws.PAPERSIZE_A4
    ws.page_setup.fitToWidth = 1
    ws.page_setup.fitToHeight = 0
    ws.sheet_properties.pageSetUpPr.fitToPage = True
    ws.page_margins.left = ws.page_margins.right = 0.4
    ws.page_margins.top = ws.page_margins.bottom = 0.6
    ws.oddFooter.left.text = "R&&D Portal"
    ws.oddFooter.left.size = 8
    ws.oddFooter.center.text = "Page &P of &N"
    ws.oddFooter.center.size = 8
    ws.oddFooter.right.text = "&D"
    ws.oddFooter.right.size = 8
    if title_rows:
        ws.print_title_rows = title_rows


# ====================================================================
# "Per Employee" sheet
# ====================================================================
def _employee_row(idx, emp):
    avg_days = emp["avgResolutionDays"] or 0
    avg_hours = round(avg_days * 24, 1)
    # Nothing assigned -> completion is "not applicable" ("-"), not a red 0%.
    completion = round(emp["completed"] / emp["totalAssigned"], 4) if emp["totalAssigned"] else "-"
    return [
        idx, emp["name"], emp["role"], emp["totalAssigned"], emp["completed"],
        emp.get("available", 0), emp["pending"], emp["overdue"], completion, avg_days, avg_hours,
    ]


def _write_header_rows(ws, last_col):
    """Rows 3-4. Single-line headers span both rows; "Avg Resolution" is one
    merged header over the Days / Hours sub-columns."""
    for col in range(1, last_col + 1):
        for row in (3, 4):
            cell = ws.cell(row=row, column=col)
            cell.fill = _fill(HEADER_BG)
            cell.border = HEADER_BORDER
            cell.font = _font(11, bold=True, color=BRAND_DARK)
            cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)

    for col in range(1, 10):  # No .. Completion
        ws.cell(row=3, column=col, value=COLUMNS[col - 1])
        ws.merge_cells(start_row=3, start_column=col, end_row=4, end_column=col)
    for col in (2, 3):
        ws.cell(row=3, column=col).alignment = Alignment(horizontal="left", vertical="center", indent=1)

    ws.cell(row=3, column=10, value="Avg. Resolution Time")
    ws.merge_cells(start_row=3, start_column=10, end_row=3, end_column=11)
    ws.cell(row=4, column=10, value="Days")
    ws.cell(row=4, column=11, value="Hours")

    ws.row_dimensions[3].height = 22
    ws.row_dimensions[4].height = 20


def _write_data_rows(ws, rows):
    for offset, values in enumerate(rows):
        r = FIRST_DATA_ROW + offset
        ws.row_dimensions[r].height = 21
        for col, value in enumerate(values, start=1):
            cell = ws.cell(row=r, column=col, value=value)
            cell.font = _font(11, bold=(col == 2))
            cell.border = BORDER_ALL
            if offset % 2 == 1:
                cell.fill = _fill(STRIPE_BG)

            if col in (2, 3):
                cell.alignment = Alignment(horizontal="left", vertical="center", indent=1)
            else:
                cell.alignment = Alignment(horizontal="center", vertical="center")

            if col == 9:
                cell.number_format = "0%"
            elif col in (10, 11):
                cell.number_format = "0.0"


def _write_total_row(ws, rows):
    """Totals under the table. Column A (No) is left empty on purpose: that is
    how parse_employee_workbook() recognises it is not an employee."""
    r = FIRST_DATA_ROW + len(rows)
    ws.row_dimensions[r].height = 24

    total_assigned = sum(row[3] for row in rows)
    completed = sum(row[4] for row in rows)
    values = {
        2: "TOTAL",
        4: total_assigned,
        5: completed,
        6: sum(row[5] for row in rows),
        7: sum(row[6] for row in rows),
        8: sum(row[7] for row in rows),
        9: round(completed / total_assigned, 4) if total_assigned else 0,
    }
    for col in range(1, 12):
        cell = ws.cell(row=r, column=col, value=values.get(col))
        cell.font = _font(11, bold=True, color=BRAND_DARK)
        cell.fill = _fill(HEADER_BG)
        cell.border = Border(top=Side(style="medium", color=BRAND), bottom=THIN, left=THIN, right=THIN)
        cell.alignment = Alignment(
            horizontal="left" if col == 2 else "center", vertical="center", indent=1 if col == 2 else 0
        )
        if col == 9:
            cell.number_format = "0%"
    return r


def _add_conditional_formatting(ws, first, last):
    if last < first:
        return

    # Completion: green >= 80%, yellow 50-79%, red < 50%
    comp = f"I{first}:I{last}"
    ws.conditional_formatting.add(comp, CellIsRule(
        operator="greaterThanOrEqual", formula=[str(GOOD_COMPLETION)],
        fill=_fill(TONE["green"][0]), font=Font(name=FONT_NAME, bold=True, color=TONE["green"][1])))
    ws.conditional_formatting.add(comp, CellIsRule(
        operator="between", formula=[str(OK_COMPLETION), str(GOOD_COMPLETION - 0.0001)],
        fill=_fill(TONE["yellow"][0]), font=Font(name=FONT_NAME, bold=True, color=TONE["yellow"][1])))
    ws.conditional_formatting.add(comp, CellIsRule(
        operator="lessThan", formula=[str(OK_COMPLETION)],
        fill=_fill(TONE["red"][0]), font=Font(name=FONT_NAME, bold=True, color=TONE["red"][1])))

    # Overdue: anything above 0 is highlighted in red
    ws.conditional_formatting.add(f"H{first}:H{last}", CellIsRule(
        operator="greaterThan", formula=["0"],
        fill=_fill(TONE["red"][0]), font=Font(name=FONT_NAME, bold=True, color=TONE["red"][1])))


def _write_legend(ws, row):
    ws.merge_cells(start_row=row, start_column=1, end_row=row, end_column=11)
    cell = ws.cell(
        row=row, column=1,
        value=(
            "How to read this:  Completion = Completed / Total Assigned  "
            f"(green \u2265 {int(GOOD_COMPLETION * 100)}%, yellow {int(OK_COMPLETION * 100)}\u2013{int(GOOD_COMPLETION * 100) - 1}%, "
            f"red < {int(OK_COMPLETION * 100)}%).  Overdue above 0 is highlighted in red.  "
            "Available = open, before the midpoint of its time window; Pending = past the midpoint; "
            "Overdue = past the deadline and not closed.  "
            "Avg. Resolution Time = average time to close an issue."
        ),
    )
    cell.font = _font(9, italic=True, color=MUTED)
    cell.alignment = Alignment(horizontal="left", vertical="top", wrap_text=True, indent=1)
    ws.row_dimensions[row].height = 42


def _build_employee_sheet(ws, employees, title, period_label):
    last_col = len(COLUMNS)
    _title_block(ws, title, _subtitle(period_label, len(employees)), last_col)
    _write_header_rows(ws, last_col)

    rows = [_employee_row(i + 1, emp) for i, emp in enumerate(employees)]
    _write_data_rows(ws, rows)

    last_data = FIRST_DATA_ROW + len(rows) - 1
    _add_conditional_formatting(ws, FIRST_DATA_ROW, last_data)

    end_row = last_data
    if rows:
        end_row = _write_total_row(ws, rows)
    else:
        ws.merge_cells(start_row=FIRST_DATA_ROW, start_column=1, end_row=FIRST_DATA_ROW, end_column=last_col)
        empty = ws.cell(row=FIRST_DATA_ROW, column=1, value="No employee data for this period.")
        empty.font = _font(11, italic=True, color=MUTED)
        empty.alignment = Alignment(horizontal="center", vertical="center")
        end_row = FIRST_DATA_ROW

    _write_legend(ws, end_row + 2)

    for letter, width in COLUMN_WIDTHS.items():
        ws.column_dimensions[letter].width = width

    ws.freeze_panes = f"A{FIRST_DATA_ROW}"
    _page_setup(ws, landscape=True, title_rows="3:4")
    ws.print_area = f"A1:{get_column_letter(last_col)}{end_row + 2}"
    return rows


def build_individual_workbook(employees, period_label=None):
    period_label = period_label or period_label_from_key(None)
    wb = Workbook()
    ws = wb.active
    ws.title = "Per Employee"
    _build_employee_sheet(ws, employees, "KPI DASHBOARD  \u2013  Individual Performance", period_label)
    return wb


# ====================================================================
# Team workbook
# ====================================================================
def _stat_card(ws, col, label, value, tone, number_format="General"):
    """Two stacked cells (label over big value) in one column."""
    bg, fg = TONE[tone] if tone in TONE else (HEADER_BG, BRAND_DARK)
    card_border = Border(left=Side(style="thick", color=fg), top=THIN, right=THIN, bottom=THIN)

    label_cell = ws.cell(row=4, column=col, value=label.upper())
    label_cell.font = _font(9, bold=True, color=fg)
    label_cell.fill = _fill(bg)
    label_cell.alignment = Alignment(horizontal="left", vertical="center", indent=1)
    label_cell.border = Border(left=card_border.left, top=THIN, right=THIN)

    value_cell = ws.cell(row=5, column=col, value=value)
    value_cell.font = _font(22, bold=True, color=fg)
    value_cell.fill = _fill(bg)
    value_cell.alignment = Alignment(horizontal="left", vertical="center", indent=1)
    value_cell.number_format = number_format
    value_cell.border = Border(left=card_border.left, bottom=THIN, right=THIN)


def build_team_workbook(employees, period_label=None):
    period_label = period_label or period_label_from_key(None)
    wb = Workbook()

    # ---- Sheet 2 first (the summary sheet reads from it) ----
    ws_detail = wb.active
    ws_detail.title = "Per Employee"
    rows = _build_employee_sheet(ws_detail, employees, "KPI DASHBOARD  \u2013  Individual Performance", period_label)

    ws = wb.create_sheet("Team Summary", 0)
    wb.active = 0
    n_cols = 6
    _title_block(ws, "KPI DASHBOARD  \u2013  Team Summary", _subtitle(period_label, len(employees)), n_cols)
    ws.row_dimensions[3].height = 8

    # ---- Headline numbers ----
    total_assigned = sum(e["totalAssigned"] for e in employees)
    completed = sum(e["completed"] for e in employees)
    available = sum(e.get("available", 0) for e in employees)
    pending = sum(e["pending"] for e in employees)
    overdue = sum(e["overdue"] for e in employees)
    rate = (completed / total_assigned) if total_assigned else 0

    _stat_card(ws, 1, "Total Assigned", total_assigned, "blue")
    _stat_card(ws, 2, "Completed", completed, "green")
    _stat_card(ws, 3, "Available", available, "blue")
    _stat_card(ws, 4, "Pending", pending, "yellow")
    _stat_card(ws, 5, "Overdue", overdue, "red")
    _stat_card(ws, 6, "Team Completion Rate", round(rate, 4), None, "0%")
    ws.row_dimensions[4].height = 20
    ws.row_dimensions[5].height = 40
    for letter in "ABCDEF":
        ws.column_dimensions[letter].width = 24

    # ---- Leaderboard ----
    ws.row_dimensions[6].height = 14
    ws.merge_cells("A7:E7")
    lb_title = ws["A7"]
    lb_title.value = "Completion Rate Leaderboard"
    lb_title.font = _font(13, bold=True, color=BRAND_DARK)
    lb_title.alignment = Alignment(horizontal="left", vertical="center", indent=1)
    ws.row_dimensions[7].height = 26

    heads = ["Rank", "Name", "Role", "Completed / Assigned", "Completion"]
    for col, label in enumerate(heads, start=1):
        cell = ws.cell(row=8, column=col, value=label)
        cell.font = _font(11, bold=True, color=BRAND_DARK)
        cell.fill = _fill(HEADER_BG)
        cell.border = HEADER_BORDER
        cell.alignment = Alignment(horizontal="left" if col in (2, 3) else "center", vertical="center", indent=1 if col in (2, 3) else 0)
    ws.row_dimensions[8].height = 24

    ranked = sorted(
        employees,
        key=lambda e: ((e["completed"] / e["totalAssigned"]) if e["totalAssigned"] else 0, e["completed"]),
        reverse=True,
    )
    for i, emp in enumerate(ranked):
        r = 9 + i
        ws.row_dimensions[r].height = 21
        comp = round(emp["completed"] / emp["totalAssigned"], 4) if emp["totalAssigned"] else "-"
        values = [i + 1, emp["name"], emp["role"], f"{emp['completed']} / {emp['totalAssigned']}", comp]
        for col, value in enumerate(values, start=1):
            cell = ws.cell(row=r, column=col, value=value)
            cell.font = _font(11, bold=(col == 2))
            cell.border = BORDER_ALL
            cell.alignment = Alignment(
                horizontal="left" if col in (2, 3) else "center", vertical="center", indent=1 if col in (2, 3) else 0
            )
            if i % 2 == 1:
                cell.fill = _fill(STRIPE_BG)
            if col == 5:
                cell.number_format = "0%"

    lb_last = 8 + len(ranked)
    if ranked:
        ws.conditional_formatting.add(
            f"E9:E{lb_last}",
            DataBarRule(start_type="num", start_value=0, end_type="num", end_value=1, color="12B76A", showValue=True),
        )
    else:
        ws.merge_cells("A9:E9")
        empty = ws["A9"]
        empty.value = "No employee data for this period."
        empty.font = _font(11, italic=True, color=MUTED)
        empty.alignment = Alignment(horizontal="center", vertical="center")
        lb_last = 9

    # ---- Chart: completed / pending / overdue per person ----
    if rows:
        first, last = FIRST_DATA_ROW, FIRST_DATA_ROW + len(rows) - 1
        chart = BarChart()
        chart.type = "bar"           # horizontal bars: names stay readable
        chart.grouping = "stacked"
        chart.overlap = 100
        chart.title = "Completed vs Available vs Pending vs Overdue per Person"
        chart.style = 10
        chart.y_axis.title = "Number of issues"
        chart.x_axis.scaling.orientation = "maxMin"  # first employee on top
        chart.y_axis.delete = False
        chart.x_axis.delete = False

        for col, title, color in (
            (5, "Completed", "12B76A"), (6, "Available", "4F8CFF"),
            (7, "Pending", "F79009"), (8, "Overdue", "F04438"),
        ):
            series = Series(Reference(ws_detail, min_col=col, min_row=first, max_row=last), title=title)
            series.graphicalProperties.solidFill = color
            series.graphicalProperties.line.solidFill = color
            chart.series.append(series)
        chart.set_categories(Reference(ws_detail, min_col=2, min_row=first, max_row=last))
        chart.legend.position = "b"
        chart.width = 26
        chart.height = max(7.5, 2.2 + 1.1 * len(rows))
        ws.add_chart(chart, f"A{lb_last + 3}")

    ws.freeze_panes = "A4"
    _page_setup(ws, landscape=False)
    return wb


# ====================================================================
# I/O
# ====================================================================
def workbook_to_bytes(wb):
    buffer = BytesIO()
    wb.save(buffer)
    buffer.seek(0)
    return buffer


def parse_employee_workbook(file_stream):
    """Read a monthly archive (or any "Per Employee" export) back into dicts."""
    wb = load_workbook(file_stream, data_only=True)
    sheet_name = "Per Employee" if "Per Employee" in wb.sheetnames else wb.sheetnames[0]
    ws = wb[sheet_name]

    # Archives from before "Available" existed have 10 columns, without it.
    has_available = ws.cell(row=3, column=6).value == "Available"

    rows = []
    for row in ws.iter_rows(min_row=FIRST_DATA_ROW, values_only=True):
        if not row or row[1] is None:
            continue
        # Employee rows start with their running number. The TOTAL row and the
        # legend line under the table do not, so they are skipped here.
        if not isinstance(row[0], (int, float)):
            continue
        if has_available:
            _, name, role, total_assigned, completed, available, pending, overdue, completion, avg_days, avg_hours = row[:11]
        else:
            _, name, role, total_assigned, completed, pending, overdue, completion, avg_days, avg_hours = row[:10]
            available = 0
        rows.append({
            "name": name,
            "role": role,
            "totalAssigned": int(total_assigned or 0),
            "completed": int(completed or 0),
            "available": int(available or 0),
            "pending": int(pending or 0),
            "overdue": int(overdue or 0),
            "avgResolutionDays": float(avg_days) if avg_days is not None else (
                round(float(avg_hours) / 24, 2) if avg_hours is not None else 0
            ),
        })
    return rows
