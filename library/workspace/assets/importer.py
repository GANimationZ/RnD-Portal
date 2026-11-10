"""Excel import for the Assets page.

Pure functions (no Flask / DB access) so the rules live in one place:

* parse_assets_workbook(stream) -> rows read from the .xlsx (with per-row errors)
* analyze_rows(rows, mode, existing) -> what the import would do
* build_template_workbook() -> the downloadable template

The route (routes.py) calls parse + analyze for the preview (dry run) and again
for the real import, so what the user reviews is exactly what gets applied.
"""

import re
from collections import OrderedDict
from io import BytesIO

from openpyxl import Workbook, load_workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side

NAME_MAX = 120
MAX_ROWS = 5000
MAX_FILE_BYTES = 3 * 1024 * 1024  # 3 MB

# Serial Number = 4 letters + 8 digits, no dashes or spaces (e.g. ABCD12345678)
SERIAL_PATTERN = re.compile(r"^[A-Z]{4}[0-9]{8}$")
SERIAL_RULE = "4 letters followed by 8 digits, without dashes or spaces (e.g. ABCD12345678)"

# Header names accepted in the file (lower case). The title / subtitle rows of
# the portal's own Excel export are skipped automatically, so an exported file
# can be imported again.
NAME_HEADERS = {"item name", "name", "item", "asset name", "nama barang", "nama"}
SERIAL_HEADERS = {"serial number", "serial", "serial no", "serial no.", "serial #", "nomor seri", "no seri", "s/n", "sn"}
HEADER_SEARCH_ROWS = 30


class ImportFormatError(Exception):
    """The file cannot be read as an asset list (message is shown to the user)."""


def collapse_spaces(value):
    return re.sub(r"\s+", " ", value or "").strip()


def name_key(value):
    return collapse_spaces(value).lower()


def normalize_serial(value):
    """Upper case, surrounding whitespace removed. Dashes/inner spaces are kept
    so that they are reported as format errors instead of silently altered."""
    return (value or "").strip().upper()


def is_valid_serial(serial):
    return bool(SERIAL_PATTERN.fullmatch(serial or ""))


def _cell_text(value):
    if value is None:
        return ""
    if isinstance(value, float) and value.is_integer():
        value = int(value)
    return str(value).strip()


def _header_key(value):
    return collapse_spaces(_cell_text(value)).lower().rstrip(":")


# ====================================================================
# Parsing
# ====================================================================
def parse_assets_workbook(stream):
    """Read an .xlsx. Returns a list of {"row", "name", "serial", "error"}."""
    try:
        wb = load_workbook(stream, read_only=True, data_only=True)
    except Exception as exc:  # noqa: BLE001  (any unreadable / non-xlsx file)
        raise ImportFormatError("This file could not be read. Please upload a valid .xlsx Excel file.") from exc

    ws = wb["PV Assets"] if "PV Assets" in wb.sheetnames else wb.worksheets[0]

    name_col = serial_col = None
    rows = []
    for row_number, values in enumerate(ws.iter_rows(values_only=True), start=1):
        if name_col is None:
            if row_number > HEADER_SEARCH_ROWS:
                break
            keys = [_header_key(v) for v in values]
            n = next((i for i, k in enumerate(keys) if k in NAME_HEADERS), None)
            s = next((i for i, k in enumerate(keys) if k in SERIAL_HEADERS), None)
            if n is not None and s is not None:
                name_col, serial_col = n, s
            continue

        name = collapse_spaces(_cell_text(values[name_col] if name_col < len(values) else None))
        serial_raw = _cell_text(values[serial_col] if serial_col < len(values) else None)
        if not name and not serial_raw:
            continue  # empty row

        if len(rows) >= MAX_ROWS:
            raise ImportFormatError(f"The file has more than {MAX_ROWS} rows. Please split it into smaller files.")

        serial = normalize_serial(serial_raw)
        error = None
        if not name or name == "-":
            error = "Item Name is empty."
        elif len(name) > NAME_MAX:
            error = f"Item Name is longer than {NAME_MAX} characters."
        elif not serial or serial == "-":
            error = "Serial Number is empty."
        elif not is_valid_serial(serial):
            error = f"Serial Number \"{serial_raw}\" must be {SERIAL_RULE}."

        rows.append({"row": row_number, "name": name, "serial": serial, "error": error})

    wb.close()

    if name_col is None:
        raise ImportFormatError(
            "Could not find the \"Item Name\" and \"Serial Number\" columns. "
            "Download the template to see the expected layout."
        )
    if not rows:
        raise ImportFormatError("The file does not contain any asset rows.")
    return rows


# ====================================================================
# Analysis
# ====================================================================
def analyze_rows(rows, mode, existing):
    """Decide what an import would do.

    rows     : output of parse_assets_workbook()
    mode     : "merge" (keep current assets, add / update) or "replace"
               (current assets are deleted first, so nothing can conflict
               with them)
    existing : {serial: name} of the assets currently in the database

    A *conflict* is one serial number with more than one different name --
    either in the file itself, or between the file and the current data
    (merge only). The user must pick which name to keep (or type a new one).
    """
    invalid = [r for r in rows if r["error"]]
    valid = [r for r in rows if not r["error"]]

    groups = OrderedDict()
    for r in valid:
        groups.setdefault(r["serial"], []).append(r)

    new, unchanged, conflicts = [], [], []
    file_duplicates = 0

    for serial, items in groups.items():
        distinct = OrderedDict()  # name_key -> {"name", "rows"}
        for it in items:
            key = name_key(it["name"])
            if key in distinct:
                distinct[key]["rows"].append(it["row"])
                file_duplicates += 1
            else:
                distinct[key] = {"name": it["name"], "rows": [it["row"]]}

        def file_source(entry):
            rows_txt = ", ".join(str(n) for n in entry["rows"])
            return f"File row{'s' if len(entry['rows']) > 1 else ''} {rows_txt}"

        db_name = existing.get(serial) if mode == "merge" else None

        if db_name is not None:
            others = [e for k, e in distinct.items() if k != name_key(db_name)]
            if not others:
                unchanged.append({"serial": serial, "name": db_name})
                continue
            candidates = [{"name": db_name, "source": "Current data"}] + [
                {"name": e["name"], "source": file_source(e)} for e in others
            ]
            conflicts.append({"serial": serial, "candidates": candidates})
        elif len(distinct) == 1:
            entry = next(iter(distinct.values()))
            new.append({"serial": serial, "name": entry["name"]})
        else:
            candidates = [{"name": e["name"], "source": file_source(e)} for e in distinct.values()]
            conflicts.append({"serial": serial, "candidates": candidates})

    return {
        "rows_read": len(rows),
        "new": new,
        "unchanged": unchanged,
        "conflicts": conflicts,
        "invalid": [
            {"row": r["row"], "name": r["name"], "serial": r["serial"], "reason": r["error"]} for r in invalid
        ],
        "file_duplicates": file_duplicates,
    }


# ====================================================================
# Template
# ====================================================================
def build_template_workbook():
    wb = Workbook()
    ws = wb.active
    ws.title = "PV Assets"

    brand = "A50034"
    thin = Side(style="thin", color="D9DDE3")
    border = Border(top=thin, bottom=thin, left=thin, right=thin)

    for col, label in enumerate(["No", "Item Name", "Serial Number"], start=1):
        cell = ws.cell(row=1, column=col, value=label)
        cell.font = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
        cell.fill = PatternFill("solid", fgColor=brand)
        cell.alignment = Alignment(horizontal="center" if col == 1 else "left", vertical="center", indent=0 if col == 1 else 1)
        cell.border = border
    ws.row_dimensions[1].height = 24

    # Rows 2-51 pre-formatted: Serial Number as text so Excel never turns it
    # into a number or drops characters.
    for r in range(2, 52):
        for col in range(1, 4):
            cell = ws.cell(row=r, column=col)
            cell.border = border
            cell.font = Font(name="Calibri", size=11)
            if col == 3:
                cell.number_format = "@"

    ws.column_dimensions["A"].width = 7
    ws.column_dimensions["B"].width = 48
    ws.column_dimensions["C"].width = 24
    ws.freeze_panes = "A2"

    guide = wb.create_sheet("Instructions")
    guide.sheet_view.showGridLines = False
    lines = [
        ("How to fill in the PV Assets sheet", True),
        ("", False),
        ("1.  Column B  \"Item Name\"  - the name of the item (max. 120 characters).", False),
        (f"2.  Column C  \"Serial Number\"  - {SERIAL_RULE}.", False),
        ("3.  Column A  \"No\"  is optional and ignored by the import.", False),
        ("4.  Every Serial Number must be unique. If the same Serial Number appears twice with", False),
        ("     different names, the portal asks which name to keep during the import.", False),
        ("5.  Do not change the header row (row 1).", False),
        ("", False),
        ("Import modes in the portal:", True),
        ("   Merge    - keeps the current assets and adds / updates the ones from this file.", False),
        ("   Replace  - deletes ALL current assets (and their scan results) and uses only this file.", False),
    ]
    for i, (text, bold) in enumerate(lines, start=1):
        cell = guide.cell(row=i, column=1, value=text)
        cell.font = Font(name="Calibri", size=13 if bold and i == 1 else 11, bold=bold, color=brand if bold else "1D2939")
    guide.column_dimensions["A"].width = 100

    buffer = BytesIO()
    wb.save(buffer)
    buffer.seek(0)
    return buffer
