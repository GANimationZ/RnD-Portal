// ============================================================
// RnD Portal - Assets
// Cek ketersediaan asset: apakah sebuah barang milik PV atau bukan,
// dengan scanner (barcode scanner USB/Bluetooth yang bekerja seperti
// keyboard, atau kamera). Hasil scan dicocokkan dengan daftar asset
// (Nama Barang + Nomor Seri).
//
// TAHAP 1 -- FrontEnd saja: `assetData` di bawah adalah DATA CONTOH.
// Saat backend siap, cukup ganti isi fetchAssets() dengan fetch ke
// API (mis. GET /workspace/assets/api/assets) -- bagian lain tidak
// perlu diubah. Bentuk data: { id, name, serial }.
//
// Helper showToast() / escapeHtml() datang dari shared/notify.js.
// ============================================================

// ------------------------------------------------------------
// DATA CONTOH (dummy) -- ganti dengan data dari database
// ------------------------------------------------------------
const MOCK_ASSETS = [
  { id: 1, name: "Digital Multimeter Fluke 87V", serial: "FLK-87V-48210931" },
  { id: 2, name: "Oscilloscope Tektronix MSO44", serial: "TEK-MSO44-B0127845" },
  { id: 3, name: "DC Power Supply Keysight E36313A", serial: "KS-E36313A-MY61004521" },
  { id: 4, name: "Color Analyzer Konica Minolta CA-410", serial: "KM-CA410-30417761" },
  { id: 5, name: "Spectroradiometer Konica Minolta CS-2000", serial: "KM-CS2000-20153398" },
  { id: 6, name: "Hipot Tester GW Instek GPT-9803", serial: "GW-9803-GEW0912345" },
  { id: 7, name: "Thermal Chamber ESPEC SU-262", serial: "ESP-SU262-0045781" },
  { id: 8, name: "Video Signal Generator Astro VG-879", serial: "ASTRO-VG879-7791204" },
  { id: 9, name: "HDMI Analyzer Quantum Data 780", serial: "QD-780-D1182009" },
  { id: 10, name: "Torque Screwdriver Kolver FAB12", serial: "KLV-FAB12-5520914" },
  { id: 11, name: "ESD Wrist Strap Tester", serial: "ESD-WT-0012093" },
  { id: 12, name: "Infrared Thermometer Fluke 568", serial: "FLK-568-61827340" },
  { id: 13, name: "Clamp Meter Hioki CM4375", serial: "HIK-CM4375-230981644" },
  { id: 14, name: "LCR Meter Hioki IM3536", serial: "HIK-IM3536-220714502" },
  { id: 15, name: "Spectrum Analyzer R&S FPC1500", serial: "RS-FPC1500-103928" },
  { id: 16, name: "Logic Analyzer Saleae Logic Pro 16", serial: "SAL-LP16-00418237" },
  { id: 17, name: "Sound Level Meter Rion NL-62", serial: "RION-NL62-00871234" },
  { id: 18, name: "Luminance Meter Konica Minolta LS-150", serial: "KM-LS150-10094478" },
  { id: 19, name: "Colorimeter X-Rite i1Pro 3", serial: "XR-I1PRO3-A002917" },
  { id: 20, name: "Soldering Station Hakko FX-951", serial: "HKO-FX951-FX9510773" },
  { id: 21, name: "Digital Caliper Mitutoyo 500-196", serial: "MTY-500196-18040215" },
  { id: 22, name: "Vibration Tester", serial: "VIB-TST-0003391" },
  { id: 23, name: "Remote Control Tester", serial: "RCT-LG-000127" },
  { id: 24, name: "Test Jig TV 55 Inch", serial: "JIG-TV55-0092" },
];

// ------------------------------------------------------------
// CONFIG
// ------------------------------------------------------------
const SCAN_STATUS = {
  pending: { label: "Belum Dicek", badge: "badge-gray" },
  match: { label: "Terverifikasi", badge: "badge-green" },
  mismatch: { label: "Nama Tidak Cocok", badge: "badge-yellow" },
};

const MAX_HISTORY = 6;

// ------------------------------------------------------------
// STATE
// ------------------------------------------------------------
let assetData = [];
let filteredData = [];
let currentPage = 1;
let rowsPerPage = 10;

// serial (ternormalisasi) -> { status: "match" | "mismatch", at: Date }
const scanState = new Map();
// Scan yang serialnya tidak ada di database (= bukan asset PV)
let unknownScanCount = 0;
const scanHistory = [];

// ============================================================
// ---- Helpers ---- //
// ============================================================
function setText(id, value) {
  const el = document.getElementById(id);
  if (el) el.textContent = value;
}

// Serial dibandingkan tanpa spasi & tanpa pembeda huruf besar/kecil,
// karena scanner kadang menambah spasi/karakter kontrol di ujung.
function normalizeSerial(str) {
  return (str || "")
    .toString()
    .replace(/[\u0000-\u001f\u007f]/g, "")
    .replace(/\s+/g, "")
    .toUpperCase();
}

function normalizeName(str) {
  return (str || "").toString().toLowerCase().replace(/\s+/g, " ").trim();
}

function formatTime(date) {
  const pad = (n) => String(n).padStart(2, "0");
  return `${pad(date.getDate())}-${pad(date.getMonth() + 1)}-${date.getFullYear()} ${pad(date.getHours())}:${pad(date.getMinutes())}:${pad(date.getSeconds())}`;
}

function statusOf(asset) {
  const state = scanState.get(normalizeSerial(asset.serial));
  return state ? state.status : "pending";
}

// ============================================================
// ---- Data layer ---- //
// ============================================================
async function fetchAssets() {
  // TODO (backend): ganti dengan
  //   const res = await fetch("/workspace/assets/api/assets");
  //   assetData = (await res.json()).assets || [];
  assetData = MOCK_ASSETS.map((a) => ({ ...a }));
}

// ============================================================
// ---- Ringkasan ---- //
// ============================================================
function renderSummary() {
  const total = assetData.length;
  let matched = 0;
  let mismatched = 0;
  assetData.forEach((asset) => {
    const status = statusOf(asset);
    if (status === "match") matched++;
    if (status === "mismatch") mismatched++;
  });

  setText("totalAssets", total);
  setText("totalMatched", matched);
  setText("totalPending", total - matched - mismatched);
  setText("totalRejected", mismatched + unknownScanCount);
}

// ============================================================
// ---- Tabel Asset ---- //
// ============================================================
function renderTable(flashSerial = null) {
  const tbody = document.getElementById("assetTableBody");
  if (!tbody) return;
  tbody.innerHTML = "";

  if (filteredData.length === 0) {
    tbody.innerHTML = `<tr class="empty-row"><td colspan="5">Tidak ada asset yang cocok dengan filter.</td></tr>`;
    renderPaginationSummary(0, 0);
    renderPaginationPages();
    return;
  }

  const start = (currentPage - 1) * rowsPerPage;
  const pageData = filteredData.slice(start, start + rowsPerPage);

  pageData.forEach((asset, i) => {
    const key = normalizeSerial(asset.serial);
    const status = statusOf(asset);
    const meta = SCAN_STATUS[status];
    const state = scanState.get(key);

    const row = document.createElement("tr");
    row.dataset.serial = key;
    if (flashSerial && key === flashSerial) row.classList.add("is-flash");
    row.innerHTML = `
      <td>${start + i + 1}</td>
      <td>${escapeHtml(asset.name)}</td>
      <td class="asset-serial">${escapeHtml(asset.serial)}</td>
      <td class="center"><span class="badge ${meta.badge}">${meta.label}</span></td>
      <td class="center">${state ? escapeHtml(formatTime(state.at)) : "-"}</td>
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

function applyFilters(flashSerial = null) {
  const searchVal = (document.getElementById("searchInput")?.value || "").trim().toLowerCase();
  const searchSerial = normalizeSerial(searchVal);
  const statusVal = document.getElementById("filterStatus")?.value || "all";

  filteredData = assetData.filter((asset) => {
    if (searchVal) {
      const inName = asset.name.toLowerCase().includes(searchVal);
      const inSerial = searchSerial && normalizeSerial(asset.serial).includes(searchSerial);
      if (!inName && !inSerial) return false;
    }
    if (statusVal !== "all" && statusOf(asset) !== statusVal) return false;
    return true;
  });

  currentPage = 1;
  renderTable(flashSerial);
}

function resetFilters() {
  const form = document.getElementById("s_f");
  if (form) form.reset();
  applyFilters();
}

// ============================================================
// ---- Scan: pencocokan dengan database ---- //
// ============================================================
function showScanResult(kind, { status, message, asset, serial }) {
  const box = document.getElementById("scanResult");
  if (!box) return;

  box.className = `scan-result is-${kind}`;
  const iconEl = box.querySelector(".scan-result__icon i");
  if (iconEl) {
    iconEl.className = `bxf ${{
      match: "bx-check-circle",
      mismatch: "bx-info-circle",
      unknown: "bx-x-circle",
      idle: "bx-scan-barcode",
    }[kind] || "bx-scan-barcode"}`;
  }

  setText("scanStatus", status);
  setText("scanMessage", message);

  const meta = document.getElementById("scanMeta");
  if (kind === "idle") {
    meta?.classList.add("is-hidden");
    return;
  }
  meta?.classList.remove("is-hidden");
  setText("scanResultName", asset ? asset.name : "- (tidak ada di database)");
  setText("scanResultSerial", asset ? asset.serial : serial);
}

function addHistory(kind, serial) {
  scanHistory.unshift({ kind, serial });
  if (scanHistory.length > MAX_HISTORY) scanHistory.pop();

  const wrap = document.getElementById("scanHistoryWrap");
  const list = document.getElementById("scanHistory");
  if (!wrap || !list) return;

  wrap.classList.remove("is-hidden");
  list.innerHTML = scanHistory
    .map((h) => `<li class="is-${h.kind}">${escapeHtml(h.serial)}</li>`)
    .join("");
}

function processScan(rawSerial, rawName) {
  const serial = normalizeSerial(rawSerial);
  if (!serial) return;

  const name = (rawName || "").trim();
  const asset = assetData.find((a) => normalizeSerial(a.serial) === serial);

  // 1) Nomor seri tidak ada di database -> bukan asset PV
  if (!asset) {
    unknownScanCount++;
    showScanResult("unknown", {
      status: "BUKAN ASSET PV",
      message: "Nomor seri ini tidak ditemukan di database asset PV.",
      serial: String(rawSerial).trim(),
    });
    addHistory("unknown", serial);
    renderSummary();
    return;
  }

  // 2) Nomor seri ada, tapi nama barang yang diinput tidak sama dengan database
  const nameMismatch = name && normalizeName(name) !== normalizeName(asset.name);
  const alreadyScanned = scanState.get(serial);

  if (nameMismatch) {
    scanState.set(serial, { status: "mismatch", at: new Date() });
    showScanResult("mismatch", {
      status: "TIDAK COCOK",
      message: `Nomor seri terdaftar sebagai asset PV, tetapi nama barang tidak sama (diinput: "${name}").`,
      asset,
    });
    addHistory("mismatch", serial);
  } else {
    // 3) Cocok
    scanState.set(serial, { status: "match", at: new Date() });
    showScanResult("match", {
      status: "ASSET PV - COCOK",
      message: alreadyScanned
        ? "Asset ini sudah pernah di-scan sebelumnya. Waktu scan diperbarui."
        : "Nomor seri dan nama barang sesuai dengan database.",
      asset,
    });
    addHistory("match", serial);
  }

  renderSummary();

  // Tampilkan barisnya: kalau tersaring oleh filter, filter di-reset dulu
  applyFilters(serial);
  if (!filteredData.some((a) => normalizeSerial(a.serial) === serial)) {
    resetFilters();
  }
  const idx = filteredData.findIndex((a) => normalizeSerial(a.serial) === serial);
  if (idx >= 0) {
    currentPage = Math.floor(idx / rowsPerPage) + 1;
    renderTable(serial);
  }
}

function initScanner() {
  const form = document.getElementById("scanForm");
  const serialInput = document.getElementById("scanSerial");
  const nameInput = document.getElementById("scanName");
  if (!form || !serialInput) return;

  form.addEventListener("submit", (e) => {
    e.preventDefault();
    if (!serialInput.value.trim()) {
      showToast("Scan atau ketik Nomor Seri terlebih dahulu.", "error");
      serialInput.focus();
      return;
    }
    processScan(serialInput.value, nameInput?.value);
    serialInput.value = "";
    if (nameInput) nameInput.value = "";
    serialInput.focus();
  });

  // Scanner siap dipakai begitu halaman dibuka
  serialInput.focus();
}

// ============================================================
// ---- Scan lewat kamera (BarcodeDetector) ---- //
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
      "Browser ini belum mendukung scan lewat kamera. Gunakan barcode scanner atau ketik manual.",
      "info",
    );
    return;
  }

  modal.classList.remove("is-hidden");
  hint.textContent = "Mengaktifkan kamera...";

  try {
    cameraStream = await navigator.mediaDevices.getUserMedia({
      video: { facingMode: "environment" },
      audio: false,
    });
    video.srcObject = cameraStream;
    await video.play();
    hint.textContent = "Arahkan kamera ke barcode / QR Nomor Seri.";

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
        // frame belum siap -- coba lagi di tick berikutnya
      }
    }, 300);
  } catch (err) {
    console.error(err);
    closeCamera();
    showToast("Kamera tidak bisa diakses. Periksa izin kamera di browser.", "error");
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
// Kolom: No, Nama Barang, Nomor Seri
// ============================================================

// Cegah formula injection di CSV: sel berawalan = + - @ dianggap
// formula oleh Excel, jadi diberi awalan apostrof.
function sanitizeCell(value) {
  if (typeof value !== "string") return value;
  if (/^[=+\-@\t\r]/.test(value)) return `'${value}`;
  return value;
}

function exportRows() {
  const rows = [["No", "Nama Barang", "Nomor Seri"]];
  filteredData.forEach((asset, i) => {
    rows.push([i + 1, asset.name, asset.serial]);
  });
  return rows;
}

function exportFileName(ext) {
  const d = new Date();
  const pad = (n) => String(n).padStart(2, "0");
  return `data-asset-pv_${d.getFullYear()}${pad(d.getMonth() + 1)}${pad(d.getDate())}.${ext}`;
}

function exportExcel() {
  if (filteredData.length === 0) {
    showToast("Tidak ada data asset untuk diexport.", "error");
    return;
  }
  if (typeof XLSX === "undefined") {
    showToast("Library Excel belum termuat. Muat ulang halaman.", "error");
    return;
  }

  const ws = XLSX.utils.aoa_to_sheet(exportRows());
  ws["!cols"] = [{ wch: 6 }, { wch: 46 }, { wch: 28 }];

  const wb = XLSX.utils.book_new();
  XLSX.utils.book_append_sheet(wb, ws, "Asset PV");
  XLSX.writeFile(wb, exportFileName("xlsx"));
  showToast(`${filteredData.length} asset diexport ke Excel.`, "success");
}

function exportCsv() {
  if (filteredData.length === 0) {
    showToast("Tidak ada data asset untuk diexport.", "error");
    return;
  }

  const content = exportRows()
    .map((r) => r.map((c) => `"${String(sanitizeCell(c)).replace(/"/g, '""')}"`).join(","))
    .join("\r\n");

  // BOM supaya Excel membaca CSV sebagai UTF-8
  const blob = new Blob(["\ufeff" + content], { type: "text/csv;charset=utf-8" });
  const link = document.createElement("a");
  link.href = URL.createObjectURL(blob);
  link.download = exportFileName("csv");
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(link.href);
  showToast(`${filteredData.length} asset diexport ke CSV.`, "success");
}

// ============================================================
// ---- Filter, pagination, export: pasang event ---- //
// ============================================================
function initList() {
  const searchInput = document.getElementById("searchInput");
  const filterStatus = document.getElementById("filterStatus");

  searchInput?.addEventListener("input", () => applyFilters());
  filterStatus?.addEventListener("change", () => applyFilters());

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
  await fetchAssets();
  renderSummary();
  applyFilters();
});
