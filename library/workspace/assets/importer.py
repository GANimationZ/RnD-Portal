import re
from collections import OrderedDict
from io import BytesIO

from openpyxl import Workbook, load_workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side

NAME_MAX = 120
LOCATION_MAX = 120

# Owners are NOT a fixed list: they are whatever the Excel files / the Add &
# Edit forms contain (PV, QA, SQA, ...). "PV" is always offered as a default.
DEFAULT_OWNER = "PV"
OWNER_MAX = 20

MAX_ROWS = 5000
MAX_FILE_BYTES = 3 * 1024 * 1024  # 3 MB

SERIAL_PATTERN = re.compile(r"^[A-Z]{4}[0-9]{8}$")
SERIAL_RULE = "4 letters followed by 8 digits, without dashes or spaces (e.g. ABCD12345678)"

NAME_HEADERS = {"item name", "name", "item", "asset name", "nama barang", "nama"}
SERIAL_HEADERS = {"serial number", "serial", "serial no", "serial no.", "serial #", "nomor seri", "no seri", "s/n", "sn"}
OWNER_HEADERS = {"owner", "asset owner", "pemilik", "pemilik asset", "team", "department"}
LOCATION_HEADERS = {"location", "asset location", "lokasi", "lokasi barang", "place", "room"}
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
    location_col = owner_col = None
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
                location_col = next((i for i, k in enumerate(keys) if k in LOCATION_HEADERS), None)
                owner_col = next((i for i, k in enumerate(keys) if k in OWNER_HEADERS), None)
            continue

        name = collapse_spaces(_cell_text(values[name_col] if name_col < len(values) else None))
        serial_raw = _cell_text(values[serial_col] if serial_col < len(values) else None)
        location = ""
        if location_col is not None and location_col < len(values):
            location = collapse_spaces(_cell_text(values[location_col]))
            if location == "-":
                location = ""
        owner_raw = ""
        if owner_col is not None and owner_col < len(values):
            owner_raw = collapse_spaces(_cell_text(values[owner_col]))
        owner = "" if owner_raw == "-" else owner_raw
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
        elif not owner:
            error = "Owner is empty."
        elif len(owner) > OWNER_MAX:
            error = f"Owner is longer than {OWNER_MAX} characters."
        elif not location:
            error = "Location is empty."
        elif len(location) > LOCATION_MAX:
            error = f"Location is longer than {LOCATION_MAX} characters."

        rows.append({"row": row_number, "name": name, "serial": serial, "owner": owner,
                     "location": location, "error": error})

    wb.close()

    if name_col is None:
        raise ImportFormatError(
            "Could not find the \"Item Name\" and \"Serial Number\" columns. "
            "Download the template to see the expected layout."
        )
    if owner_col is None or location_col is None:
        missing = " and ".join(label for label, col in (("Owner", owner_col), ("Location", location_col)) if col is None)
        raise ImportFormatError(
            f"The \"{missing}\" column is missing. Owner and Location are required for every asset. "
            "Download the template to see the expected layout."
        )
    if not rows:
        raise ImportFormatError("The file does not contain any asset rows.")
    return rows


# ====================================================================
# Analysis
# ====================================================================
def _record_key(name, owner, location):
    """Two records are "the same" when name, owner and location all match
    (ignoring case and extra spaces)."""
    return (name_key(name), name_key(owner), name_key(location))


def analyze_rows(rows, mode, existing):
    """Decide what an import would do.

    rows     : output of parse_assets_workbook()
    mode     : "merge" (keep current assets, add / update) or "replace"
               (current assets are deleted first, so nothing can conflict
               with them)
    existing : {serial: {"name", "owner", "location"}} of the assets currently
               in the database

    A Serial Number identifies ONE asset, so it can only have one Item Name,
    one Owner and one Location. A *conflict* is a serial number that shows up
    with a different name, owner or location -- either twice in the file, or
    in the file versus the current data (merge only). The user must pick which
    version to keep (or type a new one). The same name with different serial
    numbers is fine (several units of one item).
    """
    invalid = [r for r in rows if r["error"]]
    valid = [r for r in rows if not r["error"]]

    groups = OrderedDict()
    for r in valid:
        groups.setdefault(r["serial"], []).append(r)

    new, unchanged, conflicts = [], [], []
    file_duplicates = 0

    for serial, items in groups.items():
        distinct = OrderedDict()  # record key -> {"name", "owner", "location", "rows"}
        for it in items:
            key = _record_key(it["name"], it["owner"], it["location"])
            if key in distinct:
                distinct[key]["rows"].append(it["row"])
                file_duplicates += 1
            else:
                distinct[key] = {"name": it["name"], "owner": it["owner"],
                                 "location": it["location"], "rows": [it["row"]]}

        def file_source(entry):
            rows_txt = ", ".join(str(n) for n in entry["rows"])
            return f"File row{'s' if len(entry['rows']) > 1 else ''} {rows_txt}"

        def candidate(entry, source):
            return {"name": entry["name"], "owner": entry["owner"],
                    "location": entry["location"], "source": source}

        db_rec = existing.get(serial) if mode == "merge" else None

        if db_rec is not None:
            db_key = _record_key(db_rec["name"], db_rec["owner"], db_rec["location"])
            others = [e for k, e in distinct.items() if k != db_key]
            if not others:
                unchanged.append({"serial": serial, "name": db_rec["name"]})
                continue
            candidates = [candidate(db_rec, "Current data")] + [candidate(e, file_source(e)) for e in others]
            conflicts.append({"serial": serial, "candidates": candidates})
        elif len(distinct) == 1:
            entry = next(iter(distinct.values()))
            new.append({"serial": serial, "name": entry["name"], "owner": entry["owner"],
                        "location": entry["location"]})
        else:
            candidates = [candidate(e, file_source(e)) for e in distinct.values()]
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

    for col, label in enumerate(["No", "Item Name", "Serial Number", "Owner", "Location"], start=1):
        cell = ws.cell(row=1, column=col, value=label)
        cell.font = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
        cell.fill = PatternFill("solid", fgColor=brand)
        cell.alignment = Alignment(horizontal="center" if col == 1 else "left", vertical="center", indent=0 if col == 1 else 1)
        cell.border = border
    ws.row_dimensions[1].height = 24

    # Rows 2-51 pre-formatted: Serial Number as text so Excel never turns it
    # into a number or drops characters.
    for r in range(2, 52):
        for col in range(1, 6):
            cell = ws.cell(row=r, column=col)
            cell.border = border
            cell.font = Font(name="Calibri", size=11)
            if col in (3, 4, 5):
                cell.number_format = "@"

    ws.column_dimensions["A"].width = 7
    ws.column_dimensions["B"].width = 48
    ws.column_dimensions["C"].width = 24
    ws.column_dimensions["D"].width = 14
    ws.column_dimensions["E"].width = 32
    ws.freeze_panes = "A2"

    guide = wb.create_sheet("Instructions")
    guide.sheet_view.showGridLines = False
    lines = [
        ("How to fill in the PV Assets sheet", True),
        ("", False),
        ("1.  Column B  \"Item Name\"  - the name of the item (max. 120 characters).", False),
        (f"2.  Column C  \"Serial Number\"  - {SERIAL_RULE}.", False),
        ("3.  Column D  \"Owner\"  - REQUIRED. The team that owns the asset, e.g. PV, QA, SQA, DQA, OQA (max. 20 characters).", False),
        ("     Owners are read from this file: a new name simply becomes a new owner in the portal.", False),
        ("4.  Column E  \"Location\"  - REQUIRED. Where the asset is kept, e.g. \"Lab 2 - Shelf A\" (max. 120 characters).", False),
        ("     If an existing asset has a different Owner or Location in the file, it is updated.", False),
        ("5.  Column A  \"No\"  is optional and ignored by the import.", False),
        ("6.  Every Serial Number must be unique. If the same Serial Number appears twice with", False),
        ("     different names, the portal asks which name to keep during the import.", False),
        ("7.  Do not change the header row (row 1). Rows with a missing or invalid value are skipped and reported.", False),
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
