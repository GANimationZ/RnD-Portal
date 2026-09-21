// ============================================================
// RnD Portal - Issue Monitoring (LVT/MNT)
// Semua panel (Dashboard, Issue Register, List Issue, Priority
<<<<<<< HEAD
// Matrix) berbagi satu sumber data: `issueData`. Setiap kali
// data berubah (register issue baru, hold, filter, dll) semua
// panel di-render ulang lewat renderAll().
=======
// Matrix) berbagi satu sumber data: `issueData`, yang di-fetch
// dari API (/workspace/issue-monitor/api/issues).
//
// Tab switching (klik .nav-item__left) DITANGANI oleh
// static/javascript/workspace/panel-switcher.js yang di-load
// global lewat layout -- file ini tidak bikin logic tab sendiri.
>>>>>>> 0b853426c00f1067e4464b7223b619a0b4a0e7e9
// ============================================================

Chart.register(ChartDataLabels);

<<<<<<< HEAD
// ------------------------------------------------------------
// CONFIG: mapping label -> warna, dipakai bareng oleh chart,
// matrix table, dan priority-matrix card.
// ------------------------------------------------------------
const CATEGORY_META = {
  "PCBA/SMT": { color: "#b32e2e" },
  "SQA": { color: "#dd3d3d" },
  "Line-Prod": { color: "#f18f34" },
  "OQA": { color: "#2e92cc" },
  "CSS/SVC": { color: "#2e92cc" },
};

=======
const API_BASE = "/workspace/issue-monitor/api";

// ------------------------------------------------------------
// CONFIG: mapping label -> warna
// ------------------------------------------------------------
const CATEGORY_META = {
  "PCBA/SMT": { color: "#b32e2e" },
  "SQA": { color: "#dd3d3d" },
  "Line-Prod": { color: "#f18f34" },
  "OQA": { color: "#2e92cc" },
  "CSS/SVC": { color: "#2e92cc" },
};

>>>>>>> 0b853426c00f1067e4464b7223b619a0b4a0e7e9
const EVENT_META = {
  "PV": { color: "#143820" },
  "Pre-MP": { color: "#e24b4a" },
  "MP": { color: "#2c7db3" },
  "Field": { color: "#8a8f98" },
};

const PRIORITY_CLASS = {
  High: "badge-red",
  Medium: "badge-yellow",
  Low: "badge-green",
};

const STATUS_CLASS = {
  Open: "badge-blue",
  Pending: "badge-yellow",
  Closed: "badge-green",
  "On Hold": "badge-red",
};

<<<<<<< HEAD
// Mapping value <option> di form Register -> label asli
// (sesuai <select> yang ada di template kamu sekarang)
=======
>>>>>>> 0b853426c00f1067e4464b7223b619a0b4a0e7e9
const CATEGORY_VALUE_MAP = {
  pcba_smt: "PCBA/SMT",
  SQA: "SQA",
  "Line-Prod": "Line-Prod",
  OQA: "OQA",
  css_svc: "CSS/SVC",
};
<<<<<<< HEAD
const EVENT_VALUE_MAP = {
  pv: "PV",
  pre_mp: "Pre-MP",
  mp: "MP",
  field: "Field",
};

// Nama user yang login. Idealnya di-set dari Jinja lewat
// data-username di <body> atau elemen lain, contoh:
//   <body data-username="{{ current_user.username }}">
// Kalau belum ada, fallback ke "Admin".
const currentUser = document.body.dataset.username || "Admin";

// ------------------------------------------------------------
// STATE: data issue (dummy awal). `filteredData` adalah hasil
// filter dari panel List Issue, dipakai untuk render tabel +
// export.
// ------------------------------------------------------------
let issueData = [
  { id: 1, title: "Check Quality, Module gone wrong", description: "-", priority: "High", category: "PCBA/SMT", event: "PV", deadline: "18-09-2026", owner: "Admin", status: "Pending" },
  { id: 2, title: "Firmware crash on boot sequence", description: "-", priority: "High", category: "SQA", event: "MP", deadline: "14-09-2026", owner: "Rani", status: "Open" },
  { id: 3, title: "Intermittent connector wobble", description: "-", priority: "Medium", category: "Line-Prod", event: "PV", deadline: "17-09-2026", owner: "Dimas", status: "Open" },
  { id: 4, title: "Assembly misalignment on tray B", description: "-", priority: "Medium", category: "OQA", event: "PV", deadline: "05-10-2026", owner: "Dimas", status: "Open" },
  { id: 5, title: "Mainboard short circuit at test bench", description: "-", priority: "High", category: "SQA", event: "Field", deadline: "20-10-2026", owner: "Admin", status: "Pending" },
  { id: 6, title: "Minor cosmetic scratch on casing", description: "-", priority: "Low", category: "OQA", event: "MP", deadline: "19-09-2026", owner: "Sinta", status: "Open" },
  { id: 7, title: "Update test jig calibration schedule", description: "-", priority: "Low", category: "Line-Prod", event: "Pre-MP", deadline: "30-11-2026", owner: "Sinta", status: "Open" },
  { id: 8, title: "Packaging label misprint batch 12", description: "-", priority: "Low", category: "Line-Prod", event: "MP", deadline: "22-08-2026", owner: "Sinta", status: "Closed" },
];
let nextIssueId = issueData.length + 1;
let filteredData = [...issueData];

// ============================================================
// ---- Nav Tabs ---- //
// ============================================================
function initTabs() {
  document.querySelectorAll(".nav-item__left").forEach((tab) => {
    tab.addEventListener("click", () => switchTab(tab.dataset.tab));
  });
}

function switchTab(target) {
  document.querySelectorAll(".nav-item__left").forEach((t) => {
    t.classList.toggle("active", t.dataset.tab === target);
  });
  document.querySelectorAll(".body[data-panel]").forEach((panel) => {
    panel.classList.toggle("active", panel.dataset.panel === target);
  });
}

// ============================================================
// ---- Helpers umum ---- //
// ============================================================
function normalize(str) {
  return (str || "").toString().toLowerCase().replace(/[\s-]/g, "");
}

=======

const EVENT_VALUE_MAP = {
  pv: "PV",
  pre_mp: "Pre-MP",
  mp: "MP",
  field: "Field",
};

// ------------------------------------------------------------
// STATE
// ------------------------------------------------------------
let issueData = [];
let filteredData = [];

// ============================================================
// ---- Helpers umum ---- //
// ============================================================
function normalize(str) {
  return (str || "").toString().toLowerCase().replace(/[\s-]/g, "");
}

>>>>>>> 0b853426c00f1067e4464b7223b619a0b4a0e7e9
function parseDeadline(deadline) {
  // format: dd-mm-yyyy (dari API)
  const [day, month, year] = deadline.split("-").map(Number);
  return new Date(year, month - 1, day);
}

function daysUntil(deadline) {
  const today = new Date();
  today.setHours(0, 0, 0, 0);
  const target = parseDeadline(deadline);
  target.setHours(0, 0, 0, 0);
  return Math.round((target - today) / (1000 * 60 * 60 * 24));
}

function urgencyMeta(daysLeft) {
  let label;
  if (daysLeft < 0) label = `Lewat ${Math.abs(daysLeft)} hari`;
  else if (daysLeft === 0) label = "Deadline hari ini";
  else label = `${daysLeft} hari lagi`;

  const color = daysLeft <= 3 ? "#e24b4a" : daysLeft <= 7 ? "#f2a623" : "#8a8f98";
  return { label, color };
}

function classifyIssue(issue) {
  const daysLeft = daysUntil(issue.deadline);
  const isUrgent = daysLeft <= 7;
  const isHighImpact = issue.priority !== "Low";

  if (isHighImpact && isUrgent) return "do-now";
  if (isHighImpact && !isUrgent) return "schedule";
  if (!isHighImpact && isUrgent) return "delegate";
  return "later";
}

<<<<<<< HEAD
=======
function setText(id, value) {
  const el = document.getElementById(id);
  if (el) el.textContent = value;
}

// ============================================================
// ---- Data layer: fetch dari API ---- //
// ============================================================
async function fetchIssues() {
  try {
    const res = await fetch(`${API_BASE}/issues`);
    if (!res.ok) throw new Error("Gagal memuat data issue.");
    const data = await res.json();
    issueData = data.issues || [];
  } catch (err) {
    console.error(err);
    issueData = [];
  }
}

>>>>>>> 0b853426c00f1067e4464b7223b619a0b4a0e7e9
// ============================================================
// ---- Panel Dashboard ---- //
// ============================================================
function computeCategoryData() {
  return Object.keys(CATEGORY_META).map((label) => ({
    label,
    value: issueData.filter((i) => i.category === label).length,
    color: CATEGORY_META[label].color,
  }));
}

function computeEventData() {
  return Object.keys(EVENT_META).map((label) => ({
    label,
    value: issueData.filter((i) => i.event === label).length,
    color: EVENT_META[label].color,
  }));
}

function computeStatusData() {
  return Object.keys(STATUS_CLASS).map((label) => ({
    label,
    value: issueData.filter((i) => i.status === label).length,
  }));
}

function computeMatrixData() {
  const categories = Object.keys(CATEGORY_META);
  const events = Object.keys(EVENT_META);
  return categories.map((cat) =>
    events.map(
      (ev) => issueData.filter((i) => i.category === cat && i.event === ev).length,
    ),
  );
}

function getHeatColor(value, max) {
  const intensity = max === 0 ? 0 : value / max;
  const lightness = 95 - intensity * 55;
  return `hsl(341, 100%, ${lightness}%)`;
}

let categoryChart, eventChart, statusChart;

<<<<<<< HEAD
=======
function barChartOptions(max) {
  return {
    indexAxis: "y",
    responsive: true,
    maintainAspectRatio: false,
    layout: { padding: { left: 0, right: 36 } },
    plugins: {
      legend: { display: false },
      datalabels: {
        anchor: "end",
        align: "end",
        clamp: true,
        offset: 4,
        color: "#333",
        font: { weight: "bold", size: 11 },
        formatter: (value) => value,
      },
    },
    scales: {
      x: { beginAtZero: true, max, grid: { display: true }, ticks: { display: false } },
      y: { grid: { display: false }, ticks: { crossAlign: "far", padding: 0 } },
    },
  };
}

>>>>>>> 0b853426c00f1067e4464b7223b619a0b4a0e7e9
function renderCategoryChart() {
  const data = computeCategoryData();
  const max = Math.max(1, ...data.map((d) => d.value));
  if (categoryChart) {
    categoryChart.data.labels = data.map((d) => d.label);
    categoryChart.data.datasets[0].data = data.map((d) => d.value);
    categoryChart.data.datasets[0].backgroundColor = data.map((d) => d.color);
    categoryChart.options.scales.x.max = max;
    categoryChart.update();
    return;
  }
<<<<<<< HEAD
  categoryChart = new Chart(document.getElementById("category"), {
=======
  const el = document.getElementById("category");
  if (!el) return;
  categoryChart = new Chart(el, {
>>>>>>> 0b853426c00f1067e4464b7223b619a0b4a0e7e9
    type: "bar",
    data: {
      labels: data.map((d) => d.label),
      datasets: [{
        label: "Jumlah Issue",
        data: data.map((d) => d.value),
        backgroundColor: data.map((d) => d.color),
        borderRadius: 4,
        categoryPercentage: 1.0,
        barPercentage: 0.9,
      }],
    },
    options: barChartOptions(max),
  });
}

function renderEventChart() {
  const data = computeEventData();
  const max = Math.max(1, ...data.map((d) => d.value));
  if (eventChart) {
    eventChart.data.labels = data.map((d) => d.label);
    eventChart.data.datasets[0].data = data.map((d) => d.value);
    eventChart.data.datasets[0].backgroundColor = data.map((d) => d.color);
    eventChart.options.scales.x.max = max;
    eventChart.update();
    return;
  }
<<<<<<< HEAD
  eventChart = new Chart(document.getElementById("event"), {
=======
  const el = document.getElementById("event");
  if (!el) return;
  eventChart = new Chart(el, {
>>>>>>> 0b853426c00f1067e4464b7223b619a0b4a0e7e9
    type: "bar",
    data: {
      labels: data.map((d) => d.label),
      datasets: [{
        label: "Jumlah Issue",
        data: data.map((d) => d.value),
        backgroundColor: data.map((d) => d.color),
        borderRadius: 4,
        categoryPercentage: 1.0,
        barPercentage: 0.9,
      }],
    },
    options: barChartOptions(max),
  });
}

<<<<<<< HEAD
function renderStatusChart() {
  const data = computeStatusData();
  const max = Math.max(1, ...data.map((d) => d.value));
  const colors = data.map((d) => STATUS_CLASS[d.label] ? statusColorFromClass(d.label) : "#8a8f98");
=======
function statusColorFromClass(label) {
  const map = { Open: "#2c7db3", Pending: "#f2a623", Closed: "#1e7e33", "On Hold": "#e24b4a" };
  return map[label] || "#8a8f98";
}

function renderStatusChart() {
  const data = computeStatusData();
  const max = Math.max(1, ...data.map((d) => d.value));
  const colors = data.map((d) => statusColorFromClass(d.label));
>>>>>>> 0b853426c00f1067e4464b7223b619a0b4a0e7e9
  if (statusChart) {
    statusChart.data.labels = data.map((d) => d.label);
    statusChart.data.datasets[0].data = data.map((d) => d.value);
    statusChart.data.datasets[0].backgroundColor = colors;
    statusChart.options.scales.x.max = max;
    statusChart.update();
    return;
  }
<<<<<<< HEAD
  statusChart = new Chart(document.getElementById("status"), {
=======
  const el = document.getElementById("status");
  if (!el) return;
  statusChart = new Chart(el, {
>>>>>>> 0b853426c00f1067e4464b7223b619a0b4a0e7e9
    type: "bar",
    data: {
      labels: data.map((d) => d.label),
      datasets: [{
        label: "Jumlah Issue",
        data: data.map((d) => d.value),
        backgroundColor: colors,
        borderRadius: 4,
        categoryPercentage: 1.0,
        barPercentage: 0.9,
      }],
    },
    options: barChartOptions(max),
  });
}

<<<<<<< HEAD
function statusColorFromClass(label) {
  const map = { Open: "#2c7db3", Pending: "#f2a623", Closed: "#1e7e33", "On Hold": "#e24b4a" };
  return map[label] || "#8a8f98";
}

function barChartOptions(max) {
  return {
    indexAxis: "y",
    responsive: true,
    maintainAspectRatio: false,
    layout: { padding: { left: 0, right: 36 } },
    plugins: {
      legend: { display: false },
      datalabels: {
        anchor: "end",
        align: "end",
        clamp: true,
        offset: 4,
        color: "#333",
        font: { weight: "bold", size: 11 },
        formatter: (value) => value,
      },
    },
    scales: {
      x: { beginAtZero: true, max, grid: { display: true }, ticks: { display: false } },
      y: { grid: { display: false }, ticks: { crossAlign: "far", padding: 0 } },
    },
  };
}

function renderMatrixTable() {
  const table = document.getElementById("matrixTable");
=======
function renderMatrixTable() {
  const table = document.getElementById("matrixTable");
  if (!table) return;
>>>>>>> 0b853426c00f1067e4464b7223b619a0b4a0e7e9
  const categories = Object.keys(CATEGORY_META);
  const events = Object.keys(EVENT_META);
  const matrixData = computeMatrixData();
  const max = Math.max(1, ...matrixData.flat());

<<<<<<< HEAD
  // reset header (dipanggil berkali-kali, harus bersih dulu)
=======
>>>>>>> 0b853426c00f1067e4464b7223b619a0b4a0e7e9
  const theadRow = table.querySelector("thead tr");
  theadRow.innerHTML = "";
  const cornerCell = document.createElement("th");
  cornerCell.textContent = "Category \\ Event";
  cornerCell.classList.add("corner-cell");
  theadRow.appendChild(cornerCell);

  events.forEach((ev) => {
    const th = document.createElement("th");
    th.textContent = ev;
    theadRow.appendChild(th);
  });
  const totalHeaderTh = document.createElement("th");
  totalHeaderTh.textContent = "Total";
  totalHeaderTh.classList.add("total-cell");
  theadRow.appendChild(totalHeaderTh);

<<<<<<< HEAD
  // reset body
=======
>>>>>>> 0b853426c00f1067e4464b7223b619a0b4a0e7e9
  const tbody = table.querySelector("tbody");
  tbody.innerHTML = "";
  const columnSums = new Array(events.length).fill(0);

  categories.forEach((cat, i) => {
    const row = document.createElement("tr");

    const rowHeader = document.createElement("th");
    rowHeader.classList.add("category-badge-cell");
    rowHeader.innerHTML = `<span class="category-badge" style="background:${CATEGORY_META[cat].color}22; color:${CATEGORY_META[cat].color}">${cat}</span>`;
    row.appendChild(rowHeader);

    let rowSum = 0;
    matrixData[i].forEach((value, j) => {
      const td = document.createElement("td");
      td.textContent = value;
      td.style.backgroundColor = getHeatColor(value, max);
      row.appendChild(td);
      rowSum += value;
      columnSums[j] += value;
    });

    const rowTotalTd = document.createElement("td");
    rowTotalTd.textContent = rowSum;
    rowTotalTd.classList.add("total-cell");
    row.appendChild(rowTotalTd);

    tbody.appendChild(row);
  });

  const totalRow = document.createElement("tr");
  totalRow.classList.add("total-row");
  const totalLabelTh = document.createElement("th");
  totalLabelTh.textContent = "Total";
  totalRow.appendChild(totalLabelTh);

  const grandTotal = columnSums.reduce((sum, v) => sum + v, 0);
  columnSums.forEach((sum) => {
    const td = document.createElement("td");
    td.textContent = sum;
    totalRow.appendChild(td);
  });

  const grandTotalTd = document.createElement("td");
  grandTotalTd.textContent = grandTotal;
  grandTotalTd.classList.add("total-cell");
  totalRow.appendChild(grandTotalTd);
  tbody.appendChild(totalRow);
}

<<<<<<< HEAD
// Kotak ringkasan di paling atas dashboard (TOTAL ISSUES, P1 DO
// NOW, dst). Butuh id di masing-masing <span class="pv_number">
// -- lihat catatan HTML di akhir.
=======
>>>>>>> 0b853426c00f1067e4464b7223b619a0b4a0e7e9
function renderDashboardSummary() {
  const total = issueData.length;
  const doNow = issueData.filter((i) => i.status !== "Closed" && classifyIssue(i) === "do-now").length;
  const schedule = issueData.filter((i) => i.status !== "Closed" && classifyIssue(i) === "schedule").length;
  const onHold = issueData.filter((i) => i.status === "On Hold").length;
  const closed = issueData.filter((i) => i.status === "Closed").length;
  const open = issueData.filter((i) => i.status === "Open" || i.status === "Pending").length;

  setText("totalIssues", total);
  setText("totalDoNow", doNow);
  setText("totalSchedule", schedule);
  setText("totalOnHold", onHold);
  setText("totalClosed", closed);
  setText("totalOpen", open);
}

<<<<<<< HEAD
function setText(id, value) {
  const el = document.getElementById(id);
  if (el) el.textContent = value;
}

=======
>>>>>>> 0b853426c00f1067e4464b7223b619a0b4a0e7e9
// ============================================================
// ---- Panel Issue Register ---- //
// ============================================================

// ---- Combobox Assignee: diisi ulang tiap Category & Event berubah,
// ambil daftar Member yang scope-nya (diatur di /admin/users) mencakup
// KEDUA nilai tsb. Endpoint balikin [] kalau salah satu belum dipilih. ----
async function loadAssignableUsers() {
  const categoryEl = document.getElementById("issueCategory");
  const eventEl = document.getElementById("issueEvent");
  const assigneeEl = document.getElementById("issueAssignee");
  if (!categoryEl || !eventEl || !assigneeEl) return;

  const categoryVal = CATEGORY_VALUE_MAP[categoryEl.value] || categoryEl.value;
  const eventVal = EVENT_VALUE_MAP[eventEl.value] || eventEl.value;

  if (!categoryEl.value || !eventEl.value) {
    assigneeEl.disabled = true;
    assigneeEl.innerHTML = `<option value="" selected>Pilih Category & Event dahulu</option>`;
    return;
  }

  assigneeEl.disabled = true;
  assigneeEl.innerHTML = `<option value="" selected>Memuat...</option>`;

  try {
    const params = new URLSearchParams({ category: categoryVal, event: eventVal });
    const res = await fetch(`/admin/users/api/assignable?${params}`);
    const data = await res.json();
    const users = data.users || [];

    if (users.length === 0) {
      assigneeEl.innerHTML = `<option value="" selected>Belum ada Member untuk kombinasi ini</option>`;
      assigneeEl.disabled = true;
      return;
    }

    assigneeEl.innerHTML =
      `<option value="" selected>Tidak ditugaskan (opsional)</option>` +
      users.map((u) => `<option value="${u.id}">${u.username}</option>`).join("");
    assigneeEl.disabled = false;
  } catch (err) {
    console.error(err);
    assigneeEl.innerHTML = `<option value="" selected>Gagal memuat daftar Member</option>`;
    assigneeEl.disabled = true;
  }
}

function initIssueRegister() {
<<<<<<< HEAD
  flatpickr("#issueDate", {
    dateFormat: "Y-m-d",
    altInput: true,
    altFormat: "d - m - Y",
    allowInput: true,
    minDate: "today",
  });
=======
  if (document.getElementById("issueDate")) {
    flatpickr("#issueDate", {
      dateFormat: "Y-m-d",
      altInput: true,
      altFormat: "d - m - Y",
      allowInput: true,
      minDate: "today",
    });
  }
>>>>>>> 0b853426c00f1067e4464b7223b619a0b4a0e7e9

  const form = document.getElementById("issueForm");
  if (!form) return;

<<<<<<< HEAD
  document.getElementById("issueCategory")?.addEventListener("change", loadAssignableUsers);
  document.getElementById("issueEvent")?.addEventListener("change", loadAssignableUsers);

=======
<<<<<<< HEAD
  form.addEventListener("submit", (e) => {
=======
>>>>>>> 71a2d599a616afab50e9c073a9d6143e38260e7f
  form.addEventListener("submit", async (e) => {
>>>>>>> 0b853426c00f1067e4464b7223b619a0b4a0e7e9
    e.preventDefault();

    const titleEl = document.getElementById("issueTitle");
    const categoryEl = document.getElementById("issueCategory");
    const eventEl = document.getElementById("issueEvent");
    const assigneeEl = document.getElementById("issueAssignee");
    const descEl = document.getElementById("issueDescription");
    const dateEl = document.getElementById("issueDate");
    const fileEl = document.getElementById("issueFile");
<<<<<<< HEAD
=======
    const submitBtn = document.getElementById("sub_btn");
>>>>>>> 0b853426c00f1067e4464b7223b619a0b4a0e7e9

    const title = titleEl.value.trim();
    const categoryVal = categoryEl.value;
    const eventVal = eventEl.value;
    const description = descEl.value.trim();
    const deadlineRaw = dateEl.value; // format Y-m-d dari flatpickr

    if (!title || !categoryVal || !eventVal || !description || !deadlineRaw) {
      alert("Mohon lengkapi semua field sebelum submit.");
      return;
    }

<<<<<<< HEAD
    const newIssue = {
      id: nextIssueId++,
      title,
      description,
      category: CATEGORY_VALUE_MAP[categoryVal] || categoryVal,
      event: EVENT_VALUE_MAP[eventVal] || eventVal,
      deadline: formatDeadlineToDMY(deadlineRaw),
      file: fileEl && fileEl.files[0] ? fileEl.files[0].name : null,
      owner: currentUser,
      priority: "Medium", // tidak ada field priority di form saat ini, default Medium
      status: "Open",
    };

    issueData.unshift(newIssue);

    form.reset();
    renderAll();
    switchTab("list-issue");
    alert(`Issue "${newIssue.title}" berhasil didaftarkan.`);
  });
}

function formatDeadlineToDMY(ymd) {
  const [y, m, d] = ymd.split("-");
  return `${d}-${m}-${y}`;
}

=======
    const formData = new FormData();
    formData.append("title", title);
    formData.append("category", CATEGORY_VALUE_MAP[categoryVal] || categoryVal);
    formData.append("event", EVENT_VALUE_MAP[eventVal] || eventVal);
    formData.append("description", description);
    formData.append("deadline", deadlineRaw);
    if (assigneeEl && assigneeEl.value) {
      formData.append("assignee_id", assigneeEl.value);
    }
    if (fileEl && fileEl.files[0]) {
      formData.append("image", fileEl.files[0]);
    }

    const originalSubmitValue = submitBtn ? submitBtn.value : null;
    if (submitBtn) {
      submitBtn.disabled = true;
      submitBtn.value = "Menyimpan...";
    }

    try {
      const res = await fetch(`${API_BASE}/issues`, { method: "POST", body: formData });
      const data = await res.json();

      if (!res.ok) {
        alert(data.message || "Gagal menyimpan issue.");
        return;
      }

      form.reset();
      if (assigneeEl) {
        assigneeEl.disabled = true;
        assigneeEl.innerHTML = `<option value="" selected>Pilih Category & Event dahulu</option>`;
      }
      await fetchIssues();
      renderAll();

      document.querySelector('.nav-item__left[data-tab="list-issue"]')?.click();
      alert(`Issue "${data.issue.title}" berhasil didaftarkan.`);
    } catch (err) {
      console.error(err);
      alert("Terjadi kesalahan saat menghubungi server.");
    } finally {
      if (submitBtn) {
        submitBtn.disabled = false;
        submitBtn.value = originalSubmitValue;
      }
    }
  });
}

>>>>>>> 0b853426c00f1067e4464b7223b619a0b4a0e7e9
// ============================================================
// ---- Panel List Issue ---- //
// ============================================================
let currentPage = 1;
let rowsPerPage = 10;

function renderTable() {
  const tbody = document.getElementById("issueTableBody");
  if (!tbody) return;
  tbody.innerHTML = "";

  const start = (currentPage - 1) * rowsPerPage;
  const pageData = filteredData.slice(start, start + rowsPerPage);

  pageData.forEach((issue, i) => {
    const row = document.createElement("tr");
    row.dataset.issueId = issue.id;
    row.innerHTML = `
      <td>${start + i + 1}</td>
      <td>${issue.title}</td>
      <td class="center"><span class="badge ${PRIORITY_CLASS[issue.priority] || ""}">${issue.priority}</span></td>
      <td class="center">${issue.category}</td>
      <td class="center">${issue.event}</td>
      <td class="center">${issue.deadline}</td>
      <td>${issue.owner}</td>
      <td>${issue.assignee_name || "-"}</td>
      <td class="center"><span class="badge ${STATUS_CLASS[issue.status] || ""}">${issue.status}</span></td>
      <td class="center">
        <div class="action-buttons">
          ${window.CURRENT_ROLE === "Super Admin" || window.CURRENT_ROLE === "Admin" ? `
          <button type="button" class="action-btn" data-action="hold" title="Hold"><i class="bxf bx-lock"></i></button>
<<<<<<< HEAD
          ` : ""}
=======
<<<<<<< HEAD
          <button type="button" class="action-btn" data-action="detail" title="Detail"><i class="bxf bx-folder"></i></button>
          <button type="button" class="action-btn" data-action="info" title="Info"><i class="bxf bx-info-circle"></i></button>
=======
>>>>>>> 71a2d599a616afab50e9c073a9d6143e38260e7f
          <button type="button" class="action-btn" data-action="info" title="Lihat Detail"><i class="bxf bx-info-circle"></i></button>
          ${window.CURRENT_ROLE === "Super Admin" || window.CURRENT_ROLE === "Admin" ? `
          <button type="button" class="action-btn" data-action="hand" title="Close Issue"><i class="bxf bx-hand"></i></button>
<<<<<<< HEAD
          ` : ""}
=======
>>>>>>> 0b853426c00f1067e4464b7223b619a0b4a0e7e9
>>>>>>> 71a2d599a616afab50e9c073a9d6143e38260e7f
        </div>
      </td>
    `;
    tbody.appendChild(row);
  });

  renderPaginationSummary(start, start + pageData.length);
  renderPaginationPages();
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

<<<<<<< HEAD
function initListIssue() {
  const rowsSelect = document.getElementById("rowsPerPage");
  if (rowsSelect) {
    rowsSelect.addEventListener("change", (e) => {
      rowsPerPage = parseInt(e.target.value, 10);
      currentPage = 1;
      renderTable();
    });
  }

  // ---- Filters ----
  const searchInput = document.getElementById("searchInput");
  const filterPriority = document.getElementById("filterPriority");
  const filterStatus = document.getElementById("filterStatus");
  const filterCategory = document.getElementById("filterCategory");
  const filterEvent = document.getElementById("filterEvent");
  const filterOwner = document.getElementById("filterOwner");

  [searchInput, filterPriority, filterStatus, filterCategory, filterEvent, filterOwner]
    .filter(Boolean)
    .forEach((el) => {
      const evt = el.tagName === "SELECT" ? "change" : "input";
      el.addEventListener(evt, applyFilters);
    });

  const searchForm = document.getElementById("s_f");
  if (searchForm) {
    searchForm.addEventListener("submit", (e) => e.preventDefault());
  }

  const resetBtn = document.getElementById("reset");
  if (resetBtn) {
    resetBtn.addEventListener("click", (e) => {
      e.preventDefault();
      if (searchForm) searchForm.reset();
      applyFilters();
    });
  }

  // ---- Export ----
  const exportCsvBtn = document.getElementById("exportCsv");
  if (exportCsvBtn) exportCsvBtn.addEventListener("click", (e) => { e.preventDefault(); exportData("csv"); });

  const exportExcelBtn = document.getElementById("exportExcel");
  if (exportExcelBtn) exportExcelBtn.addEventListener("click", (e) => { e.preventDefault(); exportData("xls"); });

  // ---- Action buttons (Hold / Detail / Info) ----
  const tbody = document.getElementById("issueTableBody");
  if (tbody) {
    tbody.addEventListener("click", (e) => {
      const btn = e.target.closest(".action-btn");
      if (!btn) return;
      const row = btn.closest("tr");
      const issue = issueData.find((i) => i.id === Number(row.dataset.issueId));
      if (!issue) return;

      const action = btn.dataset.action;
      if (action === "hold") {
        issue.status = issue.status === "On Hold" ? "Open" : "On Hold";
        renderAll();
      } else if (action === "detail" || action === "info") {
        alert(
          `${issue.title}\n\nCategory: ${issue.category}\nEvent: ${issue.event}\nPriority: ${issue.priority}\nStatus: ${issue.status}\nDeadline: ${issue.deadline}\nOwner: ${issue.owner}\n\nDeskripsi:\n${issue.description || "-"}`,
        );
      }
    });
  }
=======
async function updateIssueStatus(issueId, status) {
  try {
    const res = await fetch(`${API_BASE}/issues/${issueId}/status`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ status }),
    });
    if (!res.ok) throw new Error("Gagal update status");
    await fetchIssues();
    renderAll();
    return true;
  } catch (err) {
    console.error(err);
    alert("Gagal memperbarui status issue.");
    return false;
  }
}

function toggleHold(issueId, currentStatus) {
  const nextStatus = currentStatus === "On Hold" ? "Open" : "On Hold";
  return updateIssueStatus(issueId, nextStatus);
>>>>>>> 0b853426c00f1067e4464b7223b619a0b4a0e7e9
}

function applyFilters() {
  const searchVal = (document.getElementById("searchInput")?.value || "").trim().toLowerCase();
  const priorityVal = document.getElementById("filterPriority")?.value || "";
  const statusVal = document.getElementById("filterStatus")?.value || "";
  const categoryVal = document.getElementById("filterCategory")?.value || "";
  const eventVal = document.getElementById("filterEvent")?.value || "";
  const ownerSelect = document.getElementById("filterOwner");
  const ownerText = ownerSelect ? ownerSelect.options[ownerSelect.selectedIndex]?.text : "All Owners";

  filteredData = issueData.filter((issue) => {
    if (searchVal && !issue.title.toLowerCase().includes(searchVal)) return false;

    if (priorityVal && !/all priority/i.test(priorityVal)) {
      const wanted = priorityVal === "Mid" ? "Medium" : priorityVal;
      if (normalize(issue.priority) !== normalize(wanted)) return false;
    }

    if (statusVal && !/all status/i.test(statusVal)) {
      const quadrant = classifyIssue(issue);
      if (statusVal === "P1 DO NOW" && quadrant !== "do-now") return false;
      if (statusVal === "P2 SCHEDULE" && quadrant !== "schedule") return false;
      if (statusVal === "ON HOLD" && issue.status !== "On Hold") return false;
      if (statusVal === "CLOSED" && issue.status !== "Closed") return false;
    }

    if (categoryVal && !/all category/i.test(categoryVal)) {
      if (normalize(issue.category) !== normalize(categoryVal)) return false;
    }

    if (eventVal && !/all event/i.test(eventVal)) {
      if (normalize(issue.event) !== normalize(eventVal)) return false;
    }

    if (ownerText && !/all owners/i.test(ownerText)) {
      if (issue.owner !== ownerText) return false;
    }

    return true;
  });

  currentPage = 1;
  renderTable();
}

function exportData(type) {
  const rows = [["No", "Title", "Priority", "Category", "Event", "Deadline", "Owner", "Status"]];
  filteredData.forEach((issue, i) => {
    rows.push([i + 1, issue.title, issue.priority, issue.category, issue.event, issue.deadline, issue.owner, issue.status]);
  });

  const content = rows
    .map((r) => r.map((c) => `"${String(c).replace(/"/g, '""')}"`).join(","))
    .join("\r\n");

  const mime = type === "csv" ? "text/csv" : "application/vnd.ms-excel";
  const ext = type === "csv" ? "csv" : "xls";

  const blob = new Blob([content], { type: mime });
  const link = document.createElement("a");
  link.href = URL.createObjectURL(blob);
  link.download = `issue-list.${ext}`;
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(link.href);
}

// ============================================================
<<<<<<< HEAD
=======
// ---- Inline Detail (muncul di bawah tabel List Issue) ---- //
// ============================================================
function showInlineDetail(issueId) {
  const issue = issueData.find((i) => i.id === Number(issueId));
  if (!issue) return;

  const panel = document.getElementById("issueInlineDetail");
  if (!panel) return;

  setText("inlineDetailEyebrow", `ISSUE #${issue.id}`);
  setText("inlineDetailTitle", issue.title);
  setText("inlineDetailCategory", issue.category);
  setText("inlineDetailEvent", issue.event);
  setText("inlineDetailDeadline", issue.deadline);
  setText("inlineDetailOwner", issue.owner);
  setText("inlineDetailAssignee", issue.assignee_name || "Belum ditugaskan");
  setText("inlineDetailDescription", issue.description || "-");

  const priorityBadge = document.getElementById("inlineDetailPriorityBadge");
  if (priorityBadge) {
    priorityBadge.textContent = issue.priority;
    priorityBadge.className = `badge ${PRIORITY_CLASS[issue.priority] || ""}`;
  }

  const statusBadge = document.getElementById("inlineDetailStatusBadge");
  if (statusBadge) {
    statusBadge.textContent = issue.status;
    statusBadge.className = `badge ${STATUS_CLASS[issue.status] || ""}`;
  }

  // Gambar (kalau ada)
  const imgWrapper = document.getElementById("inlineDetailImageWrapper");
  if (imgWrapper) {
    imgWrapper.innerHTML = issue.image
      ? `<img src="${issue.image}" alt="${issue.title}" />`
      : "";
  }

  // Tombol aksi di dalam inline detail
  const holdBtn = document.getElementById("inlineDetailHoldBtn");
  if (holdBtn) {
    holdBtn.textContent = issue.status === "On Hold" ? "Lepas Hold" : "Hold Issue";
    holdBtn.onclick = () => toggleHold(issue.id, issue.status);
  }

  const closeBtn = document.getElementById("inlineDetailCloseBtn");
  if (closeBtn) {
    closeBtn.onclick = () => {
      if (confirm(`Tandai issue "${issue.title}" sebagai Closed?`)) {
        updateIssueStatus(issue.id, "Closed");
      }
    };
  }

  // Tampilkan panel + scroll ke sana
  panel.classList.remove("is-hidden");
  panel.scrollIntoView({ behavior: "smooth", block: "start" });
}

function initInlineDetail() {
  const closeBtn = document.getElementById("inlineDetailClose");
  const panel = document.getElementById("issueInlineDetail");
  if (closeBtn && panel) {
    closeBtn.addEventListener("click", () => panel.classList.add("is-hidden"));
  }
}

// ============================================================
// ---- Init List Issue ---- //
// ============================================================
function initListIssue() {
  // ---- Filters ----
  const searchInput = document.getElementById("searchInput");
  const filterPriority = document.getElementById("filterPriority");
  const filterStatus = document.getElementById("filterStatus");
  const filterCategory = document.getElementById("filterCategory");
  const filterEvent = document.getElementById("filterEvent");
  const filterOwner = document.getElementById("filterOwner");

  [searchInput, filterPriority, filterStatus, filterCategory, filterEvent, filterOwner]
    .filter(Boolean)
    .forEach((el) => {
      const evt = el.tagName === "SELECT" ? "change" : "input";
      el.addEventListener(evt, applyFilters);
    });

  const searchForm = document.getElementById("s_f");
  if (searchForm) {
    searchForm.addEventListener("submit", (e) => e.preventDefault());
  }

  const resetBtn = document.getElementById("reset");
  if (resetBtn) {
    resetBtn.addEventListener("click", (e) => {
      e.preventDefault();
      if (searchForm) searchForm.reset();
      applyFilters();
    });
  }

  // ---- Export ----
  const exportCsvBtn = document.getElementById("exportCsv");
  if (exportCsvBtn) exportCsvBtn.addEventListener("click", (e) => { e.preventDefault(); exportData("csv"); });

  const exportExcelBtn = document.getElementById("exportExcel");
  if (exportExcelBtn) exportExcelBtn.addEventListener("click", (e) => { e.preventDefault(); exportData("xls"); });

  // ---- Rows per page ----
  const rowsSelect = document.getElementById("rowsPerPage");
  if (rowsSelect) {
    rowsSelect.addEventListener("change", () => {
      rowsPerPage = Number(rowsSelect.value) || 10;
      currentPage = 1;
      renderTable();
    });
  }

  // ---- Klik baris / tombol aksi ----
  const tbody = document.getElementById("issueTableBody");
  if (tbody) {
    tbody.addEventListener("click", (e) => {
      const row = e.target.closest("tr");
      if (!row) return;
      const issue = issueData.find((i) => i.id === Number(row.dataset.issueId));
      if (!issue) return;

      const btn = e.target.closest(".action-btn");
      if (!btn) {
        // Klik di area baris selain tombol aksi -> buka inline detail
        showInlineDetail(issue.id);
        return;
      }

      const action = btn.dataset.action;
      if (action === "hold") {
        toggleHold(issue.id, issue.status);
      } else if (action === "info") {
        // Icon INFO → buka inline detail
        showInlineDetail(issue.id);
      } else if (action === "hand") {
        // Icon HAND → close issue
        if (confirm(`Tandai issue "${issue.title}" sebagai Closed?`)) {
          updateIssueStatus(issue.id, "Closed");
        }
      }
    });
  }

  // Init inline detail (close button) — cukup sekali
  initInlineDetail();
}

// ============================================================
>>>>>>> 0b853426c00f1067e4464b7223b619a0b4a0e7e9
// ---- Panel Priority Matrix ---- //
// ============================================================
function renderIssueCard(issue) {
  const daysLeft = daysUntil(issue.deadline);
  const urgency = urgencyMeta(daysLeft);
  const catColor = CATEGORY_META[issue.category]?.color || "#8a8f98";

  return `
    <div class="pm-card" data-issue-id="${issue.id}">
      <div class="pm-card__top">
        <span class="badge ${PRIORITY_CLASS[issue.priority] || ""}">${issue.priority}</span>
        <span class="pm-card__category" style="color:${catColor}">${issue.category}</span>
      </div>
      <span class="pm-card__title">${issue.title}</span>
      <div class="pm-card__bottom">
        <span class="pm-card__owner"><i class="bxf bx-user-check"></i> ${issue.owner}</span>
        <span class="pm-card__deadline" style="color:${urgency.color}">
          <i class="bxf bx-calendar-check"></i> ${urgency.label}
        </span>
      </div>
    </div>
  `;
}

const QUADRANT_LIST_ID = {
  "do-now": "pmListDoNow",
  schedule: "pmListSchedule",
  delegate: "pmListDelegate",
  later: "pmListLater",
};
const QUADRANT_COUNT_ID = {
  "do-now": "pmCountDoNow",
  schedule: "pmCountSchedule",
  delegate: "pmCountDelegate",
  later: "pmCountLater",
};

function renderPriorityMatrix() {
  const buckets = { "do-now": [], schedule: [], delegate: [], later: [] };

  issueData
    .filter((issue) => issue.status !== "Closed")
    .forEach((issue) => buckets[classifyIssue(issue)].push(issue));

  Object.entries(buckets).forEach(([quadrant, issues]) => {
    const listEl = document.getElementById(QUADRANT_LIST_ID[quadrant]);
    const countEl = document.getElementById(QUADRANT_COUNT_ID[quadrant]);
    if (!listEl || !countEl) return;

    countEl.textContent = issues.length;

    const sorted = [...issues].sort((a, b) => daysUntil(a.deadline) - daysUntil(b.deadline));
    listEl.innerHTML = sorted.length > 0
      ? sorted.map(renderIssueCard).join("")
      : '<div class="pm-empty">Tidak ada issue di kuadran ini.</div>';
<<<<<<< HEAD
=======
  });

  // Klik kartu di Priority Matrix -> pindah ke tab List Issue lalu buka inline detail
  document.querySelectorAll(".pm-card").forEach((card) => {
    card.style.cursor = "pointer";
    card.addEventListener("click", () => {
      document.querySelector('.nav-item__left[data-tab="list-issue"]')?.click();
      // Delay kecil supaya panel-switcher selesai ganti tab dulu
      setTimeout(() => showInlineDetail(card.dataset.issueId), 60);
    });
>>>>>>> 0b853426c00f1067e4464b7223b619a0b4a0e7e9
  });
}

// ============================================================
// ---- Render All + Init ---- //
// ============================================================
function renderAll() {
  renderDashboardSummary();
  renderCategoryChart();
  renderEventChart();
  renderStatusChart();
  renderMatrixTable();
  applyFilters(); // ini juga memanggil renderTable()
  renderPriorityMatrix();
}

<<<<<<< HEAD
document.addEventListener("DOMContentLoaded", () => {
  initTabs();
  initIssueRegister();
  initListIssue();
=======
document.addEventListener("DOMContentLoaded", async () => {
  initIssueRegister();
  initListIssue();
  await fetchIssues();
>>>>>>> 0b853426c00f1067e4464b7223b619a0b4a0e7e9
  renderAll();
});