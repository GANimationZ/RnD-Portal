// ====================================================================
// Shared styled Excel (.xlsx) export -- window.exportStyledExcel(options)
// Requires the vendored ExcelJS (static/vendor/exceljs/exceljs.min.js).
//
// Every Excel export in the portal goes through this helper so they all share
// one look: a coloured title bar, a subtitle line (export time / filters),
// a clear header row, striped rows, status colours, a frozen header, filters
// and print-ready page setup.
//
// options = {
//   fileName:  "issue-list_20261104.xlsx",
//   sheetName: "Issue List",
//   title:     "Issue List",
//   subtitle:  "Exported 04-11-2026 10:30  |  25 rows",
//   columns: [{ header: "No", width: 6, align: "center" }, ...],   // align: left|center|right
//   rows:    [[1, "Title", ...], ...],                             // same order as columns
//   // Optional colouring of cells by column header + cell value:
//   //   colors: { Status: { Open: "blue", Closed: "green" } }
//   colors: {},
//   // Optional total line under the table: { label: "Total", values: { 2: 10 } }
// }
// Colour names: red | yellow | green | blue | gray
// ====================================================================
(function () {
  const BRAND = "FFA50034";
  const BRAND_DARK = "FF700023";
  const HEADER_BG = "FFF4E4E9";
  const STRIPE_BG = "FFF8F9FB";
  const BORDER_COLOR = "FFD9DDE3";
  const FONT = "Calibri";

  // [fill, text] pairs -- same hues as the badges in the UI
  const TONES = {
    red: ["FFFDE2E1", "FFB42318"],
    yellow: ["FFFEF0C7", "FF93370D"],
    green: ["FFD1FADF", "FF05603A"],
    blue: ["FFD9E8FF", "FF1849A9"],
    gray: ["FFEAECF0", "FF475467"],
  };

  const thin = { style: "thin", color: { argb: BORDER_COLOR } };
  const BORDER = { top: thin, left: thin, bottom: thin, right: thin };

  function colLetter(n) {
    let s = "";
    while (n > 0) {
      const m = (n - 1) % 26;
      s = String.fromCharCode(65 + m) + s;
      n = Math.floor((n - 1) / 26);
    }
    return s;
  }

  window.exportStyledExcel = async function exportStyledExcel(options) {
    if (typeof ExcelJS === "undefined") {
      throw new Error("The Excel library failed to load. Please reload the page.");
    }

    const { fileName, sheetName, title, subtitle, columns, rows, colors = {}, totalRow } = options;
    const colCount = columns.length;
    const lastCol = colLetter(colCount);

    const wb = new ExcelJS.Workbook();
    wb.creator = "RnD Portal";
    wb.created = new Date();

    const ws = wb.addWorksheet((sheetName || "Sheet1").slice(0, 31), {
      views: [{ state: "frozen", ySplit: 4, showGridLines: false }],
      pageSetup: {
        orientation: colCount > 6 ? "landscape" : "portrait",
        paperSize: 9, // A4
        fitToPage: true,
        fitToWidth: 1,
        fitToHeight: 0,
        margins: { left: 0.4, right: 0.4, top: 0.6, bottom: 0.6, header: 0.3, footer: 0.3 },
      },
      headerFooter: { oddFooter: "&L&8RnD Portal&C&8Page &P of &N&R&8&D" },
    });

    ws.columns = columns.map((c) => ({ width: c.width || 16 }));

    // ---- Row 1: title bar ----
    ws.mergeCells(`A1:${lastCol}1`);
    const titleCell = ws.getCell("A1");
    titleCell.value = title || sheetName || "Export";
    titleCell.font = { name: FONT, size: 16, bold: true, color: { argb: "FFFFFFFF" } };
    titleCell.alignment = { vertical: "middle", horizontal: "left", indent: 1 };
    ws.getRow(1).height = 32;
    for (let c = 1; c <= colCount; c++) {
      ws.getCell(1, c).fill = { type: "pattern", pattern: "solid", fgColor: { argb: BRAND } };
    }

    // ---- Row 2: subtitle ----
    ws.mergeCells(`A2:${lastCol}2`);
    const subCell = ws.getCell("A2");
    subCell.value = subtitle || "";
    subCell.font = { name: FONT, size: 10, italic: true, color: { argb: "FF667085" } };
    subCell.alignment = { vertical: "middle", horizontal: "left", indent: 1 };
    ws.getRow(2).height = 20;

    // ---- Row 3: spacer ----
    ws.getRow(3).height = 6;

    // ---- Row 4: header ----
    const headerRow = ws.getRow(4);
    headerRow.height = 26;
    columns.forEach((col, i) => {
      const cell = headerRow.getCell(i + 1);
      cell.value = col.header;
      cell.font = { name: FONT, size: 11, bold: true, color: { argb: BRAND_DARK } };
      cell.fill = { type: "pattern", pattern: "solid", fgColor: { argb: HEADER_BG } };
      cell.alignment = { vertical: "middle", horizontal: col.align === "left" ? "left" : "center", wrapText: true, indent: col.align === "left" ? 1 : 0 };
      cell.border = { top: thin, left: thin, right: thin, bottom: { style: "medium", color: { argb: BRAND } } };
    });

    // ---- Data rows ----
    rows.forEach((values, r) => {
      const row = ws.getRow(5 + r);
      row.height = 20;
      const striped = r % 2 === 1;

      columns.forEach((col, i) => {
        const cell = row.getCell(i + 1);
        const value = values[i] == null || values[i] === "" ? "-" : values[i];
        cell.value = value;
        cell.font = { name: FONT, size: 11, color: { argb: "FF1D2939" } };
        cell.border = BORDER;
        cell.alignment = {
          vertical: "middle",
          horizontal: col.align || "left",
          indent: (col.align || "left") === "left" ? 1 : 0,
          wrapText: col.wrap === true,
        };
        if (striped) cell.fill = { type: "pattern", pattern: "solid", fgColor: { argb: STRIPE_BG } };

        // Status / priority colouring
        const tone = colors[col.header] && TONES[colors[col.header][String(value)]];
        if (tone) {
          cell.fill = { type: "pattern", pattern: "solid", fgColor: { argb: tone[0] } };
          cell.font = { name: FONT, size: 11, bold: true, color: { argb: tone[1] } };
        }
      });
    });

    // ---- Optional total row ----
    let lastDataRow = 4 + rows.length;
    if (totalRow) {
      lastDataRow += 1;
      const row = ws.getRow(lastDataRow);
      row.height = 22;
      columns.forEach((col, i) => {
        const cell = row.getCell(i + 1);
        cell.value = i === 0 ? totalRow.label : (totalRow.values && totalRow.values[i + 1]) ?? "";
        cell.font = { name: FONT, size: 11, bold: true, color: { argb: BRAND_DARK } };
        cell.fill = { type: "pattern", pattern: "solid", fgColor: { argb: HEADER_BG } };
        cell.border = { ...BORDER, top: { style: "medium", color: { argb: BRAND } } };
        cell.alignment = { vertical: "middle", horizontal: i === 0 ? "left" : (col.align || "center"), indent: i === 0 ? 1 : 0 };
      });
    }

    // ---- Filters + print setup ----
    if (rows.length > 0) {
      ws.autoFilter = { from: { row: 4, column: 1 }, to: { row: 4 + rows.length, column: colCount } };
    }
    ws.pageSetup.printTitlesRow = "4:4";
    ws.pageSetup.printArea = `A1:${lastCol}${Math.max(lastDataRow, 4)}`;

    // ---- Download ----
    const buffer = await wb.xlsx.writeBuffer();
    const blob = new Blob([buffer], {
      type: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    });
    const link = document.createElement("a");
    link.href = URL.createObjectURL(blob);
    link.download = fileName;
    document.body.appendChild(link);
    link.click();
    link.remove();
    setTimeout(() => URL.revokeObjectURL(link.href), 1000);
  };

  // "04-11-2026 10:30" -- used in the subtitle line of every export
  window.formatExportTimestamp = function formatExportTimestamp(date = new Date()) {
    const pad = (n) => String(n).padStart(2, "0");
    return `${pad(date.getDate())}-${pad(date.getMonth() + 1)}-${date.getFullYear()} ${pad(date.getHours())}:${pad(date.getMinutes())}`;
  };
})();
