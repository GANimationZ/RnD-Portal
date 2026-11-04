// ============================================================
// RnD Portal - Assets
// Checks whether an item is a PV asset by scanning it (a USB/Bluetooth
// barcode scanner that types like a keyboard, or the camera) and matching
// the result against the asset list (Item Name + Serial Number).
//
// Data lives in the database (see library/workspace/assets/routes.py):
//   GET  /workspace/assets/api/assets        -> asset list + scan summary
//   POST /workspace/assets/api/assets        -> add an asset manually
//   PUT  /workspace/assets/api/assets/<id>   -> edit an asset
//   DELETE /workspace/assets/api/assets/<id> -> delete an asset
//   POST /workspace/assets/api/assets/scan   -> check a scanned serial
// Scan results are saved, so they survive a page refresh.
//
// showToast() / escapeHtml() come from shared/notify.js.
// ============================================================

const API_BASE = "/workspace/assets/api";

// ------------------------------------------------------------
// CONFIG
// ------------------------------------------------------------
const SCAN_STATUS = {
  pending: { label: "Not Checked", badge: "badge-gray" },
  match: { label: "Verified", badge: "badge-green" },
  mismatch: { label: "Name Mismatch", badge: "badge-yellow" },
};

// ------------------------------------------------------------
// STATE
// ------------------------------------------------------------
let assetData = [];
let filteredData = [];
let currentPage = 1;
let rowsPerPage = 10;
let unknownScanCount = 0; // scans whose serial is not in the database (= not a PV asset)
let isScanning = false;

// ============================================================
// ---- Helpers ---- //
// ============================================================
function setText(id, value) {
  const el = document.getElementById(id);
  if (el) el.textContent = value;
}

// Same normalization as the backend: no whitespace / control characters,
// upper case -- scanners sometimes append stray spaces or control codes.
function normalizeSerial(str) {
  return (str || "")
    .toString()
    .replace(/[\u0000-\u001f\u007f]/g, "")
    .replace(/\s+/g, "")
    .toUpperCase();
}

function formatTime(iso) {
  if (!iso) return "-";
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return "-";
  const pad = (n) => String(n).padStart(2, "0");
  return `${pad(date.getDate())}-${pad(date.getMonth() + 1)}-${date.getFullYear()} ${pad(date.getHours())}:${pad(date.getMinutes())}:${pad(date.getSeconds())}`;
}

async function request(path, options = {}) {
  const res = await fetch(`${API_BASE}${path}`, options);
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    const error = new Error(data.message || "Something went wrong. Please try again.");
    error.fields = data.fields || [];
    throw error;
  }
  return data;
}

// ============================================================
// ---- Data layer ---- //
// ============================================================
async function fetchAssets() {
  try {
    const data = await request("/assets");
    assetData = data.assets || [];
    unknownScanCount = data.unknown_count || 0;
    renderHistory(data.history || []);
  } catch (err) {
    console.error(err);
    assetData = [];
    showToast("Failed to load the asset list.", "error");
  }
}

// ============================================================
// ---- Summary ---- //
// ============================================================
function renderSummary() {
  const total = assetData.length;
  const matched = assetData.filter((a) => a.scan_status === "match").length;
  const mismatched = assetData.filter((a) => a.scan_status === "mismatch").length;

  setText("totalAssets", total);
  setText("totalMatched", matched);
  setText("totalPending", total - matched - mismatched);
  setText("totalRejected", mismatched + unknownScanCount);
}

// ============================================================
// ---- Asset Table ---- //
// ============================================================
function renderTable(flashId = null) {
  const tbody = document.getElementById("assetTableBody");
  if (!tbody) return;
  tbody.innerHTML = "";

  if (filteredData.length === 0) {
    tbody.innerHTML = `<tr class="empty-row"><td colspan="7">No assets match the current filters.</td></tr>`;
    renderPaginationSummary(0, 0);
    renderPaginationPages();
    return;
  }

  const start = (currentPage - 1) * rowsPerPage;
  const pageData = filteredData.slice(start, start + rowsPerPage);

  pageData.forEach((asset, i) => {
    const meta = SCAN_STATUS[asset.scan_status] || SCAN_STATUS.pending;

    const row = document.createElement("tr");
    row.dataset.assetId = asset.id;
    if (flashId && asset.id === flashId) row.classList.add("is-flash");
    row.innerHTML = `
      <td>${start + i + 1}</td>
      <td>${escapeHtml(asset.name)}</td>
      <td class="asset-serial">${escapeHtml(asset.serial)}</td>
      <td class="center"><span class="badge ${meta.badge}">${meta.label}</span></td>
      <td class="center">${escapeHtml(formatTime(asset.scanned_at))}</td>
      <td>${escapeHtml(asset.scanned_by || "-")}</td>
      <td>
        <div class="action-buttons">
          <button type="button" class="action-btn" data-action="edit" title="Edit"><i class="bxf bx-edit"></i></button>
          <button type="button" class="action-btn is-danger" data-action="delete" title="Delete"><i class="bxf bx-trash"></i></button>
        </div>
      </td>
    `;
    tbody.appendChild(row);
  });

  renderPaginationSummary(start, start + pageData.length);
  renderPaginationPages();

  const flashed = tbody.querySelector(".is-flash");
  if (flashed) flashed.scrollIntoView({ block: "nearest", behavior: "smooth" });
}

function renderPaginationSummary(start, end) {
  const summary = document.getElementById("paginationSummary");
  if (!summary) return;
  summary.textContent = `Showing ${filteredData.length === 0 ? 0 : start + 1}-${Math.min(end, filteredData.length)} of ${filteredData.length}`;
}

function renderPaginationPages() {
  const pagesEl = document.getElementById("paginationPages");
  if (!pagesEl) return;
  pagesEl.innerHTML = "";

  const totalPages = Math.max(1, Math.ceil(filteredData.length / rowsPerPage));
  if (currentPage > totalPages) currentPage = totalPages;

  const prevBtn = document.createElement("button");
  prevBtn.type = "button";
  prevBtn.textContent = "Prev";
  prevBtn.disabled = currentPage === 1;
  prevBtn.addEventListener("click", () => { currentPage--; renderTable(); });
  pagesEl.appendChild(prevBtn);

  for (let p = 1; p <= totalPages; p++) {
    const pageBtn = document.createElement("button");
    pageBtn.type = "button";
    pageBtn.textContent = p;
    pageBtn.className = p === currentPage ? "is-active" : "";
    pageBtn.addEventListener("click", () => { currentPage = p; renderTable(); });
    pagesEl.appendChild(pageBtn);
  }

  const nextBtn = document.createElement("button");
  nextBtn.type = "button";
  nextBtn.textContent = "Next";
  nextBtn.disabled = currentPage === totalPages;
  nextBtn.addEventListener("click", () => { currentPage++; renderTable(); });
  pagesEl.appendChild(nextBtn);
}

function applyFilters() {
  const searchVal = (document.getElementById("searchInput")?.value || "").trim().toLowerCase();
  const searchSerial = normalizeSerial(searchVal);
  const statusVal = document.getElementById("filterStatus")?.value || "all";

  filteredData = assetData.filter((asset) => {
    if (searchVal) {
      const inName = asset.name.toLowerCase().includes(searchVal);
      const inSerial = searchSerial && normalizeSerial(asset.serial).includes(searchSerial);
      if (!inName && !inSerial) return false;
    }
    if (statusVal !== "all" && asset.scan_status !== statusVal) return false;
    return true;
  });

  currentPage = 1;
  renderTable();
}

function resetFilters() {
  document.getElementById("s_f")?.reset();
  applyFilters();
}

// Show a specific row: reset the filters if they hide it, jump to the page
// that contains it, and highlight it.
function revealRow(assetId) {
  applyFilters();
  if (!filteredData.some((a) => a.id === assetId)) resetFilters();

  const idx = filteredData.findIndex((a) => a.id === assetId);
  if (idx >= 0) {
    currentPage = Math.floor(idx / rowsPerPage) + 1;
    renderTable(assetId);
  }
}

// ============================================================
// ---- Scan: match against the database ---- //
// ============================================================
const RESULT_ICON = {
  match: "bx-check-circle",
  mismatch: "bx-info-circle",
  unknown: "bx-x-circle",
  idle: "bx-scan-barcode",
};

function showScanResult(kind, { status, message, asset, serial }) {
  const box = document.getElementById("scanResult");
  if (!box) return;

  box.className = `scan-result is-${kind}`;
  const iconEl = box.querySelector(".scan-result__icon i");
  if (iconEl) iconEl.className = `bxf ${RESULT_ICON[kind] || RESULT_ICON.idle}`;

  setText("scanStatus", status);
  setText("scanMessage", message);

  const meta = document.getElementById("scanMeta");
  if (kind === "idle") {
    meta?.classList.add("is-hidden");
    return;
  }
  meta?.classList.remove("is-hidden");
  setText("scanResultName", asset ? asset.name : "- (not in the database)");
  setText("scanResultSerial", asset ? asset.serial : serial);
}

function renderHistory(history) {
  const wrap = document.getElementById("scanHistoryWrap");
  const list = document.getElementById("scanHistory");
  if (!wrap || !list) return;

  if (!history.length) {
    wrap.classList.add("is-hidden");
    list.innerHTML = "";
    return;
  }
  wrap.classList.remove("is-hidden");
  list.innerHTML = history
    .map((h) => `<li class="is-${escapeHtml(h.result)}" title="${escapeHtml(formatTime(h.scanned_at))}">${escapeHtml(h.serial)}</li>`)
    .join("");
}

async function processScan(rawSerial, rawName) {
  const serial = (rawSerial || "").trim();
  if (!normalizeSerial(serial) || isScanning) return false;

  isScanning = true;
  const submitBtn = document.getElementById("scanSubmit");
  if (submitBtn) submitBtn.disabled = true;

  try {
    const data = await request("/assets/scan", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ serial, name: (rawName || "").trim() }),
    });

    unknownScanCount = data.unknown_count;
    renderHistory(data.history || []);

    if (data.result === "unknown") {
      showScanResult("unknown", {
        status: "NOT A PV ASSET",
        message: "This Serial Number was not found in the PV asset database.",
        serial,
      });
      renderSummary();
      return true;
    }

    // Update the local copy of the scanned asset
    const idx = assetData.findIndex((a) => a.id === data.asset.id);
    if (idx >= 0) assetData[idx] = data.asset;

    if (data.result === "mismatch") {
      showScanResult("mismatch", {
        status: "MISMATCH",
        message: `The Serial Number is a registered PV asset, but the item name does not match (entered: "${data.input_name}").`,
        asset: data.asset,
      });
    } else {
      showScanResult("match", {
        status: "PV ASSET - MATCH",
        message: data.already_scanned
          ? "This asset was already scanned before. The scan time has been updated."
          : "The Serial Number and Item Name match the database.",
        asset: data.asset,
      });
    }

    renderSummary();
    revealRow(data.asset.id);
    return true;
  } catch (err) {
    console.error(err);
    showToast(err.message, "error");
    return false;
  } finally {
    isScanning = false;
    if (submitBtn) submitBtn.disabled = false;
  }
}

function initScanner() {
  const form = document.getElementById("scanForm");
  const serialInput = document.getElementById("scanSerial");
  const nameInput = document.getElementById("scanName");
  if (!form || !serialInput) return;

  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    if (!serialInput.value.trim()) {
      showToast("Scan or type a Serial Number first.", "error");
      serialInput.focus();
      return;
    }
    const ok = await processScan(serialInput.value, nameInput?.value);
    if (ok) {
      serialInput.value = "";
      if (nameInput) nameInput.value = "";
    }
    serialInput.focus();
  });

  // Ready for the scanner as soon as the page opens
  serialInput.focus();
}

// ============================================================
// ---- Add / Edit / Delete asset ---- //
// The same popup is used for Add and Edit; #editingAssetId is empty when
// adding and holds the asset id when editing.
// ============================================================
const ADD_FIELD_IDS = { name: "newAssetName", serial: "newAssetSerial" };

function openAssetModal(asset = null) {
  const modal = document.getElementById("addAssetModal");
  if (!modal) return;

  document.getElementById("addAssetForm")?.reset();
  showAddError("");
  document.getElementById("editingAssetId").value = asset ? asset.id : "";
  setText("assetModalTitle", asset ? "Edit Asset" : "Add Asset");
  setText("addAssetSave", asset ? "Save Changes" : "Save Asset");
  if (asset) {
    document.getElementById("newAssetName").value = asset.name;
    document.getElementById("newAssetSerial").value = asset.serial;
  }

  modal.classList.remove("is-hidden");
  document.getElementById("newAssetName")?.focus();
}

function closeAddAsset() {
  document.getElementById("addAssetModal")?.classList.add("is-hidden");
  document.getElementById("scanSerial")?.focus();
}

function showAddError(message, fields = []) {
  setText("addAssetError", message);
  Object.entries(ADD_FIELD_IDS).forEach(([field, id]) => {
    document.getElementById(id)?.classList.toggle("is-invalid", fields.includes(field));
  });
}

async function deleteAsset(asset) {
  const confirmed = await showConfirm(
    `Delete asset "${asset.name}" (${asset.serial})? This action cannot be undone.`,
    { confirmText: "Delete" },
  );
  if (!confirmed) return;

  try {
    const data = await request(`/assets/${asset.id}`, { method: "DELETE" });
    assetData = assetData.filter((a) => a.id !== asset.id);
    renderSummary();

    // The result card must not keep showing an asset that no longer exists
    if (document.getElementById("scanResultSerial")?.textContent === asset.serial) {
      showScanResult("idle", {
        status: "Waiting for scan...",
        message: "The asset check result will appear here.",
      });
    }

    // Stay on the same page of the table (or the last page if it emptied)
    const page = currentPage;
    applyFilters();
    currentPage = Math.min(page, Math.max(1, Math.ceil(filteredData.length / rowsPerPage)));
    renderTable();
    showToast(data.message, "success");
  } catch (err) {
    showToast(err.message, "error");
  }
}

function initAddAsset() {
  const form = document.getElementById("addAssetForm");
  if (!form) return;

  document.getElementById("addAssetBtn")?.addEventListener("click", () => openAssetModal());
  document.getElementById("addAssetClose")?.addEventListener("click", closeAddAsset);
  document.getElementById("addAssetCancel")?.addEventListener("click", closeAddAsset);
  document.getElementById("addAssetModal")?.addEventListener("click", (e) => {
    if (e.target.id === "addAssetModal") closeAddAsset();
  });
  document.addEventListener("keydown", (e) => {
    const modal = document.getElementById("addAssetModal");
    if (e.key === "Escape" && modal && !modal.classList.contains("is-hidden")) closeAddAsset();
  });

  // Row actions (Edit / Delete)
  document.getElementById("assetTableBody")?.addEventListener("click", (e) => {
    const btn = e.target.closest("button[data-action]");
    if (!btn) return;
    const id = Number(btn.closest("tr")?.dataset.assetId);
    const asset = assetData.find((a) => a.id === id);
    if (!asset) return;

    if (btn.dataset.action === "edit") openAssetModal(asset);
    if (btn.dataset.action === "delete") deleteAsset(asset);
  });

  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    const saveBtn = document.getElementById("addAssetSave");
    const editingId = document.getElementById("editingAssetId").value;
    saveBtn.disabled = true;

    try {
      const data = await request(editingId ? `/assets/${editingId}` : "/assets", {
        method: editingId ? "PUT" : "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          name: document.getElementById("newAssetName").value,
          serial: document.getElementById("newAssetSerial").value,
        }),
      });

      if (editingId) {
        const idx = assetData.findIndex((a) => a.id === Number(editingId));
        if (idx >= 0) assetData[idx] = data.asset;
      } else {
        assetData.push(data.asset);
      }

      closeAddAsset();
      renderSummary();
      revealRow(data.asset.id);
      showToast(editingId ? data.message : `Asset "${data.asset.name}" added successfully.`, "success");
    } catch (err) {
      showAddError(err.message, err.fields);
      const firstField = ADD_FIELD_IDS[(err.fields || [])[0]];
      if (firstField) document.getElementById(firstField)?.focus();
    } finally {
      saveBtn.disabled = false;
    }
  });
}

// ============================================================
// ---- Scan with camera (BarcodeDetector) ---- //
// ============================================================
let cameraStream = null;
let cameraTimer = null;

async function openCamera() {
  const modal = document.getElementById("cameraModal");
  const video = document.getElementById("cameraVideo");
  const hint = document.getElementById("cameraHint");
  if (!modal || !video) return;

  if (!("BarcodeDetector" in window) || !navigator.mediaDevices?.getUserMedia) {
    showToast(
      "This browser does not support camera scanning. Use a barcode scanner or type the Serial Number.",
      "info",
    );
    return;
  }

  modal.classList.remove("is-hidden");
  hint.textContent = "Starting camera...";

  try {
    cameraStream = await navigator.mediaDevices.getUserMedia({
      video: { facingMode: "environment" },
      audio: false,
    });
    video.srcObject = cameraStream;
    await video.play();
    hint.textContent = "Point the camera at the Serial Number barcode / QR code.";

    const detector = new BarcodeDetector();
    cameraTimer = setInterval(async () => {
      try {
        const codes = await detector.detect(video);
        if (codes.length) {
          const value = codes[0].rawValue;
          closeCamera();
          processScan(value, document.getElementById("scanName")?.value);
        }
      } catch (err) {
        // frame not ready yet -- try again on the next tick
      }
    }, 300);
  } catch (err) {
    console.error(err);
    closeCamera();
    showToast("Cannot access the camera. Check the camera permission in your browser.", "error");
  }
}

function closeCamera() {
  clearInterval(cameraTimer);
  cameraTimer = null;
  if (cameraStream) {
    cameraStream.getTracks().forEach((t) => t.stop());
    cameraStream = null;
  }
  const video = document.getElementById("cameraVideo");
  if (video) video.srcObject = null;
  document.getElementById("cameraModal")?.classList.add("is-hidden");
  document.getElementById("scanSerial")?.focus();
}

function initCamera() {
  document.getElementById("cameraBtn")?.addEventListener("click", openCamera);
  document.getElementById("cameraClose")?.addEventListener("click", closeCamera);
  document.getElementById("cameraModal")?.addEventListener("click", (e) => {
    if (e.target.id === "cameraModal") closeCamera();
  });
  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape" && cameraStream) closeCamera();
  });
}

// ============================================================
// ---- Export (Excel .xlsx & CSV) ---- //
// Columns: No, Item Name, Serial Number
// ============================================================

// Prevents CSV formula injection: a cell starting with = + - @ runs as a
// formula when opened in Excel, so prefix it with an apostrophe.
function sanitizeCell(value) {
  if (typeof value !== "string") return value;
  if (/^[=+\-@\t\r]/.test(value)) return `'${value}`;
  return value;
}

function exportRows() {
  const rows = [["No", "Item Name", "Serial Number"]];
  filteredData.forEach((asset, i) => {
    rows.push([i + 1, asset.name, asset.serial]);
  });
  return rows;
}

function exportFileName(ext) {
  const d = new Date();
  const pad = (n) => String(n).padStart(2, "0");
  return `pv-assets_${d.getFullYear()}${pad(d.getMonth() + 1)}${pad(d.getDate())}.${ext}`;
}

function exportExcel() {
  if (filteredData.length === 0) {
    showToast("There are no assets to export.", "error");
    return;
  }
  if (typeof XLSX === "undefined") {
    showToast("The Excel library failed to load. Please reload the page.", "error");
    return;
  }

  const ws = XLSX.utils.aoa_to_sheet(exportRows());
  ws["!cols"] = [{ wch: 6 }, { wch: 46 }, { wch: 28 }];

  const wb = XLSX.utils.book_new();
  XLSX.utils.book_append_sheet(wb, ws, "PV Assets");
  XLSX.writeFile(wb, exportFileName("xlsx"));
  showToast(`${filteredData.length} assets exported to Excel.`, "success");
}

function exportCsv() {
  if (filteredData.length === 0) {
    showToast("There are no assets to export.", "error");
    return;
  }

  const content = exportRows()
    .map((r) => r.map((c) => `"${String(sanitizeCell(c)).replace(/"/g, '""')}"`).join(","))
    .join("\r\n");

  // BOM so Excel reads the CSV as UTF-8
  const blob = new Blob(["\ufeff" + content], { type: "text/csv;charset=utf-8" });
  const link = document.createElement("a");
  link.href = URL.createObjectURL(blob);
  link.download = exportFileName("csv");
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(link.href);
  showToast(`${filteredData.length} assets exported to CSV.`, "success");
}

// ============================================================
// ---- Filters, pagination, export: wire up events ---- //
// ============================================================
function initList() {
  document.getElementById("searchInput")?.addEventListener("input", applyFilters);
  document.getElementById("filterStatus")?.addEventListener("change", applyFilters);

  document.getElementById("s_f")?.addEventListener("submit", (e) => e.preventDefault());
  document.getElementById("reset")?.addEventListener("click", (e) => {
    e.preventDefault();
    resetFilters();
  });

  document.getElementById("exportExcel")?.addEventListener("click", exportExcel);
  document.getElementById("exportCsv")?.addEventListener("click", exportCsv);

  document.getElementById("rowsPerPage")?.addEventListener("change", (e) => {
    rowsPerPage = Number(e.target.value) || 10;
    currentPage = 1;
    renderTable();
  });
}

// ============================================================
// ---- Init ---- //
// ============================================================
document.addEventListener("DOMContentLoaded", async () => {
  initList();
  initScanner();
  initCamera();
  initAddAsset();
  await fetchAssets();
  renderSummary();
  applyFilters();
});
