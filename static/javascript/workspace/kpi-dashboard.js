// ==================== DATA ====================
// 'team' pakai kosakata kategori yang sama dengan issue-monitor
// (PCBA/SMT, Line-Prod, SQA, dst) supaya konsisten satu portal.
const employeeData = [
  {
    id: "p1",
    name: "Rani Freya",
    role: "PCBA Engineer",
    totalAssigned: 18,
    completed: 12,
    pending: 4,
    overdue: 2,
    avgResolutionDays: 2.4,
    trendResolved: [3, 5, 2, 6, 4, 7, 5],
    trendPending: [2, 3, 4, 2, 3, 2, 3],
    trendOverdue: [4, 3, 3, 2, 2, 2, 2],
    bestPractices: [
      "Selalu verifikasi root cause sebelum menutup issue.",
      "Update status issue maksimal H+1 setelah ada perkembangan.",
      "Gunakan template laporan standar untuk kategori PCBA/SMT.",
    ],
  },
  {
    id: "p2",
    name: "Dimas Pratama",
    role: "Assembly Lead",
    totalAssigned: 14,
    completed: 9,
    pending: 3,
    overdue: 2,
    avgResolutionDays: 3.1,
    trendResolved: [2, 3, 4, 3, 5, 4, 6],
    trendPending: [3, 2, 2, 3, 2, 3, 1],
    trendOverdue: [4, 4, 3, 3, 2, 2, 2],
    bestPractices: [
      "Koordinasi dengan QA sebelum eskalasi issue assembly.",
      "Dokumentasikan foto sebelum/sesudah perbaikan.",
    ],
  },
  {
    id: "p3",
    name: "Sinta Wijaya",
    role: "QA Inspector",
    totalAssigned: 10,
    completed: 7,
    pending: 2,
    overdue: 1,
    avgResolutionDays: 1.8,
    trendResolved: [1, 2, 3, 2, 4, 3, 5],
    trendPending: [1, 1, 2, 1, 1, 2, 1],
    trendOverdue: [3, 2, 2, 2, 1, 1, 1],
    bestPractices: [
      "Prioritaskan issue kategori High sebelum jam 10 pagi.",
      "Selalu cross-check dengan checklist QA sebelum status Closed.",
    ],
  },
];

// Warna badge tim disamakan dengan categoryColors di issue-monitor.js
const TEAM_COLORS = {
  "PCBA/SMT": "#b32e2e",
  SQA: "#dd3d3d",
  "Line-Prod": "#f18f34",
  OQA: "#2e92cc",
  "CSS/SVC": "#2e92cc",
};

let activeEmployeeId = employeeData[0].id;
let trendChart = null;
let teamChart = null;
const renderedPanels = new Set();

function getActiveEmployee() {
  return employeeData.find((e) => e.id === activeEmployeeId);
}

// ==================== UTIL ====================

function getInitials(name) {
  return name
    .split(" ")
    .filter(Boolean)
    .map((part) => part[0])
    .join("")
    .slice(0, 2)
    .toUpperCase();
}

function todayStamp() {
  return new Date().toISOString().slice(0, 10);
}

// Interpolasi 3 warna: hijau (cepat/ringan) -> kuning (sedang) -> merah (lama/berat).
// Palet dipakai ulang dari warna yang sudah ada di issue-monitor (#1e7e33, #f2a623, #e24b4a).
const WORKLOAD_STOPS = [
  [30, 126, 51], // #1e7e33
  [242, 166, 35], // #f2a623
  [226, 75, 74], // #e24b4a
];

function interpolateWorkloadColor(ratio) {
  const clamped = Math.min(Math.max(ratio, 0), 1);
  const [from, to] =
    clamped <= 0.5
      ? [WORKLOAD_STOPS[0], WORKLOAD_STOPS[1]]
      : [WORKLOAD_STOPS[1], WORKLOAD_STOPS[2]];
  const local = clamped <= 0.5 ? clamped / 0.5 : (clamped - 0.5) / 0.5;

  const [r1, g1, b1] = from;
  const [r2, g2, b2] = to;
  const r = Math.round(r1 + (r2 - r1) * local);
  const g = Math.round(g1 + (g2 - g1) * local);
  const b = Math.round(b1 + (b2 - b1) * local);
  return `rgb(${r}, ${g}, ${b})`;
}

// hours ~20 dianggap ringan/cepat, ~60+ dianggap berat/lama
function getWorkloadBar(hours) {
  const min = 20;
  const max = 60;
  const ratio = (Math.min(Math.max(hours, min), max) - min) / (max - min);
  const widthPct = Math.round(15 + ratio * 85); // floor 15% biar bar selalu kelihatan
  return { widthPct, color: interpolateWorkloadColor(ratio) };
}

function getAvgHours(emp) {
  return emp.avgResolutionDays * 24;
}

function getCompletionRate(emp) {
  return emp.totalAssigned === 0
    ? 0
    : Math.round((emp.completed / emp.totalAssigned) * 100);
}

function getTeamTotals() {
  return employeeData.reduce(
    (acc, emp) => ({
      totalAssigned: acc.totalAssigned + emp.totalAssigned,
      completed: acc.completed + emp.completed,
      pending: acc.pending + emp.pending,
      overdue: acc.overdue + emp.overdue,
    }),
    { totalAssigned: 0, completed: 0, pending: 0, overdue: 0 },
  );
}

// ==================== PANEL: INDIVIDUAL ====================

function renderEmployeeTable() {
  const tbody = document.getElementById("employeeTableBody");
  if (!tbody) return;
  tbody.innerHTML = "";

  employeeData.forEach((emp) => {
    const avgHours = getAvgHours(emp);
    const { widthPct, color } = getWorkloadBar(avgHours);
    const teamColor = TEAM_COLORS[emp.team] || "#666";

    const row = document.createElement("tr");
    row.className = emp.id === activeEmployeeId ? "is-active" : "";
    row.innerHTML = `
      <td title="${emp.name}">${emp.name}</td>
      <td class="center">${avgHours.toFixed(1)}h</td>
      <td>
        <div class="hours-bar-track">
          <div class="hours-bar-fill" style="width:${widthPct}%; background:${color};"></div>
        </div>
      </td>
    `;
    row.addEventListener("click", () => {
      activeEmployeeId = emp.id;
      renderEmployeeTable();
      renderTrendChart();
      renderEmpContent();
    });
    tbody.appendChild(row);
  });
}

// Panel kecil untuk mengisi ruang kosong di bawah tabel:
// menyorot siapa yang beban kerjanya paling ringan & siapa yang paling perlu perhatian.
function renderEmployeeInsights() {
  const el = document.getElementById("employeeInsights");
  if (!el) return;
  if (employeeData.length === 0) {
    el.innerHTML = "";
    return;
  }

  const lightest = employeeData.reduce((a, b) =>
    getAvgHours(a) <= getAvgHours(b) ? a : b,
  );
  const heaviest = employeeData.reduce((a, b) =>
    getAvgHours(a) >= getAvgHours(b) ? a : b,
  );
  const lightColor = getWorkloadBar(getAvgHours(lightest)).color;
  const heavyColor = getWorkloadBar(getAvgHours(heaviest)).color;

  el.innerHTML = `
    <div class="insight">
      <span class="insight__dot" style="background:${lightColor}"></span>
      <div>
        <span class="insight__label">Beban Paling Ringan</span>
        <span class="insight__value">${lightest.name} &middot; ${getAvgHours(lightest).toFixed(1)}h</span>
      </div>
    </div>
    <div class="insight insight--danger">
      <span class="insight__dot" style="background:${heavyColor}"></span>
      <div>
        <span class="insight__label">Perlu Perhatian</span>
        <span class="insight__value">${heaviest.name} &middot; ${getAvgHours(heaviest).toFixed(1)}h</span>
      </div>
    </div>
  `;
}

function renderTrendChart() {
  const emp = getActiveEmployee();
  const ctx = document.getElementById("empTrendChart");
  if (!ctx) return;

  if (trendChart) trendChart.destroy();

  trendChart = new Chart(ctx, {
    type: "line",
    data: {
      labels: ["W1", "W2", "W3", "W4", "W5", "W6", "W7"],
      datasets: [
        {
          label: "Resolved",
          data: emp.trendResolved,
          borderColor: "#4f8cff",
          backgroundColor: "rgba(79, 140, 255, 0.12)",
          fill: false,
          tension: 0,
          pointRadius: 3,
        },
        {
          label: "Pending",
          data: emp.trendPending,
          borderColor: "#f2a623",
          backgroundColor: "rgba(242, 166, 35, 0.12)",
          fill: false,
          tension: 0,
          pointRadius: 3,
        },
        {
          label: "Overdue",
          data: emp.trendOverdue,
          borderColor: "#e24b4a",
          backgroundColor: "rgba(226, 75, 74, 0.12)",
          fill: false,
          tension: 0,
          pointRadius: 3,
          borderDash: [4, 3],
        },
      ],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: { legend: { position: "bottom" } },
      scales: { y: { beginAtZero: true } },
    },
  });
}

function renderEmpContent() {
  const emp = getActiveEmployee();
  const el = document.getElementById("empContent");
  if (!el) return;

  const completionRate = getCompletionRate(emp);
  const teamColor = TEAM_COLORS[emp.team] || "#666";

  el.innerHTML = `
    <div class="emp-profile">
      <span class="emp-avatar emp-avatar--lg" style="background:${teamColor}22; color:${teamColor}">${getInitials(emp.name)}</span>
      <div>
        <div class="emp-profile__name">${emp.name}</div>
        <div class="emp-profile__role">${emp.role} &middot; ${emp.team}</div>
      </div>
    </div>
    <div class="emp-stats">
      <div class="emp-stat"><span class="emp-stat__label">Total Assigned</span><span class="emp-stat__value">${emp.totalAssigned}</span></div>
      <div class="emp-stat"><span class="emp-stat__label">Completed</span><span class="emp-stat__value">${emp.completed}</span></div>
      <div class="emp-stat"><span class="emp-stat__label">Pending</span><span class="emp-stat__value">${emp.pending}</span></div>
      <div class="emp-stat ${emp.overdue > 0 ? "emp-stat--danger" : ""}"><span class="emp-stat__label">Overdue</span><span class="emp-stat__value">${emp.overdue}</span></div>
      <div class="emp-stat"><span class="emp-stat__label">Completion Rate</span><span class="emp-stat__value">${completionRate}%</span></div>
      <div class="emp-stat"><span class="emp-stat__label">Avg. Resolution</span><span class="emp-stat__value">${emp.avgResolutionDays} hari</span></div>
    </div>
    <div class="emp-notes">
      <span class="emp-notes__title">Best Practice Notes</span>
      <ul>${emp.bestPractices.map((note) => `<li>${note}</li>`).join("")}</ul>
    </div>
  `;
}

function renderIndividualPanel() {
  renderEmployeeTable();
  renderEmployeeInsights();
  renderTrendChart();
  renderEmpContent();
}

// ==================== PANEL: TEAM ====================

function renderTeamSummary() {
  const el = document.getElementById("teamSummary");
  if (!el) return;

  const totals = getTeamTotals();
  const completionRate =
    totals.totalAssigned === 0
      ? 0
      : Math.round((totals.completed / totals.totalAssigned) * 100);

  el.innerHTML = `
    <div class="emp-stats emp-stats--team">
      <div class="emp-stat"><span class="emp-stat__label">Total Assigned</span><span class="emp-stat__value">${totals.totalAssigned}</span></div>
      <div class="emp-stat"><span class="emp-stat__label">Completed</span><span class="emp-stat__value">${totals.completed}</span></div>
      <div class="emp-stat"><span class="emp-stat__label">Pending</span><span class="emp-stat__value">${totals.pending}</span></div>
      <div class="emp-stat ${totals.overdue > 0 ? "emp-stat--danger" : ""}"><span class="emp-stat__label">Overdue</span><span class="emp-stat__value">${totals.overdue}</span></div>
      <div class="emp-stat"><span class="emp-stat__label">Team Completion Rate</span><span class="emp-stat__value">${completionRate}%</span></div>
    </div>
  `;
}

function renderTeamChart() {
  const ctx = document.getElementById("teamComparisonChart");
  if (!ctx) return;

  if (teamChart) teamChart.destroy();

  teamChart = new Chart(ctx, {
    type: "bar",
    data: {
      labels: employeeData.map((e) => e.name),
      datasets: [
        {
          label: "Completed",
          data: employeeData.map((e) => e.completed),
          backgroundColor: "#3ddc97",
          borderRadius: 4,
        },
        {
          label: "Pending",
          data: employeeData.map((e) => e.pending),
          backgroundColor: "#f2a623",
          borderRadius: 4,
        },
        {
          label: "Overdue",
          data: employeeData.map((e) => e.overdue),
          backgroundColor: "#e24b4a",
          borderRadius: 4,
        },
      ],
    },
    options: {
      indexAxis: "y",
      responsive: true,
      maintainAspectRatio: false,
      plugins: { legend: { position: "bottom" } },
      scales: {
        x: { stacked: true, beginAtZero: true },
        y: { stacked: true, grid: { display: false } },
      },
    },
  });
}

// Ranking completion rate per orang, biar panel Team tidak kosong/template.
function renderTeamLeaderboard() {
  const el = document.getElementById("teamLeaderboard");
  if (!el) return;

  const ranked = [...employeeData].sort(
    (a, b) => getCompletionRate(b) - getCompletionRate(a),
  );

  el.innerHTML = ranked
    .map((emp, idx) => {
      const rate = getCompletionRate(emp);
      const teamColor = TEAM_COLORS[emp.team] || "#666";
      const rateColor =
        rate >= 70 ? "#1e7e33" : rate >= 50 ? "#f2a623" : "#e24b4a";

      return `
      <div class="team-leaderboard__row">
        <span class="team-leaderboard__rank">#${idx + 1}</span>
        <span class="emp-avatar" style="background:${teamColor}22; color:${teamColor}">${getInitials(emp.name)}</span>
        <div class="team-leaderboard__info">
          <span class="team-leaderboard__name">${emp.name}</span>
          <span class="team-leaderboard__team">${emp.team}</span>
        </div>
        <div class="team-leaderboard__bar-wrap">
          <div class="hours-bar-track">
            <div class="hours-bar-fill" style="width:${rate}%; background:${rateColor};"></div>
          </div>
          <span class="team-leaderboard__rate">${rate}%</span>
        </div>
      </div>
    `;
    })
    .join("");
}

function renderTeamPanel() {
  renderTeamSummary();
  renderTeamChart();
  renderTeamLeaderboard();
}

// ==================== PANEL: HISTORY ====================
// Export/Import sekarang lewat backend (openpyxl), bukan SheetJS lagi.
// Panel History menampilkan DATA-nya langsung (bukan cuma daftar file),
// mirip panel Individual & Team, tapi sumbernya snapshot bulanan terpilih.

const HISTORY_LIST_ENDPOINT = "/workspace/kpi-dashboard/history";
const HISTORY_DATA_ENDPOINT = "/workspace/kpi-dashboard/history/data";
const IMPORT_ENDPOINT = "/workspace/kpi-dashboard/import";

let historySnapshots = [];
let historyEmployees = [];
let historyChart = null;
let historySubtab = "individual";

// Data historis cuma punya field yang tersimpan di Excel (Name, Role,
// totalAssigned, completed, pending, overdue, avgResolutionDays) -- tidak ada
// 'team'/trend mingguan, jadi insight & chart di sini dihitung dari field itu saja.

function getHistoryAvgHours(emp) {
  return emp.avgResolutionDays * 24;
}

function getHistoryCompletionRate(emp) {
  return emp.totalAssigned === 0
    ? 0
    : Math.round((emp.completed / emp.totalAssigned) * 100);
}

function renderHistoryEmployeeTable() {
  const tbody = document.getElementById("historyEmployeeTableBody");
  if (!tbody) return;

  if (historyEmployees.length === 0) {
    tbody.innerHTML =
      '<tr><td colspan="4" class="center">Tidak ada data pada bulan ini.</td></tr>';
    return;
  }

  tbody.innerHTML = historyEmployees
    .map((emp) => {
      const avgHours = getHistoryAvgHours(emp);
      const { widthPct, color } = getWorkloadBar(avgHours);
      return `
      <tr>
        <td title="${emp.name}">${emp.name}</td>
        <td>${emp.role}</td>
        <td class="center">${avgHours.toFixed(1)}h</td>
        <td>
          <div class="hours-bar-track">
            <div class="hours-bar-fill" style="width:${widthPct}%; background:${color};"></div>
          </div>
        </td>
      </tr>
    `;
    })
    .join("");
}

function renderHistoryInsights() {
  const el = document.getElementById("historyEmployeeInsights");
  if (!el) return;
  if (historyEmployees.length === 0) {
    el.innerHTML = "";
    return;
  }

  const lightest = historyEmployees.reduce((a, b) =>
    getHistoryAvgHours(a) <= getHistoryAvgHours(b) ? a : b,
  );
  const heaviest = historyEmployees.reduce((a, b) =>
    getHistoryAvgHours(a) >= getHistoryAvgHours(b) ? a : b,
  );
  const lightColor = getWorkloadBar(getHistoryAvgHours(lightest)).color;
  const heavyColor = getWorkloadBar(getHistoryAvgHours(heaviest)).color;

  el.innerHTML = `
    <div class="insight">
      <span class="insight__dot" style="background:${lightColor}"></span>
      <div>
        <span class="insight__label">Beban Paling Ringan</span>
        <span class="insight__value">${lightest.name} &middot; ${getHistoryAvgHours(lightest).toFixed(1)}h</span>
      </div>
    </div>
    <div class="insight insight--danger">
      <span class="insight__dot" style="background:${heavyColor}"></span>
      <div>
        <span class="insight__label">Perlu Perhatian</span>
        <span class="insight__value">${heaviest.name} &middot; ${getHistoryAvgHours(heaviest).toFixed(1)}h</span>
      </div>
    </div>
  `;
}

function renderHistoryTeamSummary() {
  const el = document.getElementById("historyTeamSummary");
  if (!el) return;

  const totals = historyEmployees.reduce(
    (acc, emp) => ({
      totalAssigned: acc.totalAssigned + emp.totalAssigned,
      completed: acc.completed + emp.completed,
      pending: acc.pending + emp.pending,
      overdue: acc.overdue + emp.overdue,
    }),
    { totalAssigned: 0, completed: 0, pending: 0, overdue: 0 },
  );
  const completionRate =
    totals.totalAssigned === 0
      ? 0
      : Math.round((totals.completed / totals.totalAssigned) * 100);

  el.innerHTML = `
    <div class="emp-stats emp-stats--team">
      <div class="emp-stat"><span class="emp-stat__label">Total Assigned</span><span class="emp-stat__value">${totals.totalAssigned}</span></div>
      <div class="emp-stat"><span class="emp-stat__label">Completed</span><span class="emp-stat__value">${totals.completed}</span></div>
      <div class="emp-stat"><span class="emp-stat__label">Pending</span><span class="emp-stat__value">${totals.pending}</span></div>
      <div class="emp-stat ${totals.overdue > 0 ? "emp-stat--danger" : ""}"><span class="emp-stat__label">Overdue</span><span class="emp-stat__value">${totals.overdue}</span></div>
      <div class="emp-stat"><span class="emp-stat__label">Team Completion Rate</span><span class="emp-stat__value">${completionRate}%</span></div>
    </div>
  `;
}

function renderHistoryTeamChart() {
  const ctx = document.getElementById("historyTeamChart");
  if (!ctx) return;

  if (historyChart) historyChart.destroy();

  historyChart = new Chart(ctx, {
    type: "bar",
    data: {
      labels: historyEmployees.map((e) => e.name),
      datasets: [
        {
          label: "Completed",
          data: historyEmployees.map((e) => e.completed),
          backgroundColor: "#3ddc97",
          borderRadius: 4,
        },
        {
          label: "Pending",
          data: historyEmployees.map((e) => e.pending),
          backgroundColor: "#f2a623",
          borderRadius: 4,
        },
        {
          label: "Overdue",
          data: historyEmployees.map((e) => e.overdue),
          backgroundColor: "#e24b4a",
          borderRadius: 4,
        },
      ],
    },
    options: {
      indexAxis: "y",
      responsive: true,
      maintainAspectRatio: false,
      plugins: { legend: { position: "bottom" } },
      scales: {
        x: { stacked: true, beginAtZero: true },
        y: { stacked: true, grid: { display: false } },
      },
    },
  });
}

function renderHistoryTeamLeaderboard() {
  const el = document.getElementById("historyTeamLeaderboard");
  if (!el) return;

  const ranked = [...historyEmployees].sort(
    (a, b) => getHistoryCompletionRate(b) - getHistoryCompletionRate(a),
  );

  el.innerHTML = ranked
    .map((emp, idx) => {
      const rate = getHistoryCompletionRate(emp);
      const rateColor =
        rate >= 70 ? "#1e7e33" : rate >= 50 ? "#f2a623" : "#e24b4a";

      return `
      <div class="team-leaderboard__row">
        <span class="team-leaderboard__rank">#${idx + 1}</span>
        <span class="emp-avatar" style="background:#66666622; color:#666">${getInitials(emp.name)}</span>
        <div class="team-leaderboard__info">
          <span class="team-leaderboard__name">${emp.name}</span>
          <span class="team-leaderboard__team">${emp.role}</span>
        </div>
        <div class="team-leaderboard__bar-wrap">
          <div class="hours-bar-track">
            <div class="hours-bar-fill" style="width:${rate}%; background:${rateColor};"></div>
          </div>
          <span class="team-leaderboard__rate">${rate}%</span>
        </div>
      </div>
    `;
    })
    .join("");
}

function renderHistorySubpanels() {
  renderHistoryEmployeeTable();
  renderHistoryInsights();
  renderHistoryTeamSummary();
  renderHistoryTeamLeaderboard();
  // Chart cuma di-render kalau sub-tab Team lagi kelihatan, supaya canvas
  // punya ukuran yang benar (Chart.js butuh elemen visible saat dibuat).
  if (historySubtab === "team") {
    renderHistoryTeamChart();
  }
}

function setHistorySubtab(subtab) {
  historySubtab = subtab;

  document.querySelectorAll(".history-subnav__btn").forEach((btn) => {
    btn.classList.toggle("active", btn.dataset.subtab === subtab);
  });
  document.querySelectorAll(".history-subpanel").forEach((panel) => {
    const isMatch = panel.dataset.subpanel === subtab;
    panel.style.display = isMatch ? "" : "none";
  });

  if (subtab === "team") {
    renderHistoryTeamChart();
  }
}

async function loadHistoryData(filename) {
  try {
    const response = await fetch(`${HISTORY_DATA_ENDPOINT}/${filename}`);
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    const data = await response.json();
    historyEmployees = data.employees || [];
    renderHistorySubpanels();
  } catch (err) {
    console.error(err);
    historyEmployees = [];
    renderHistorySubpanels();
  }
}

async function loadHistoryMonths() {
  const select = document.getElementById("historyMonthSelect");
  const downloadBtn = document.getElementById("historyDownloadBtn");
  if (!select) return;

  try {
    const response = await fetch(HISTORY_LIST_ENDPOINT);
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    const data = await response.json();
    historySnapshots = data.snapshots || [];

    if (historySnapshots.length === 0) {
      select.innerHTML = '<option value="">Belum ada riwayat</option>';
      return;
    }

    select.innerHTML = historySnapshots
      .map(
        (snap) => `
      <option value="${snap.filename}">${snap.label}</option>
    `,
      )
      .join("");

    if (downloadBtn) downloadBtn.href = historySnapshots[0].downloadUrl;
    await loadHistoryData(historySnapshots[0].filename);
  } catch (err) {
    console.error(err);
    select.innerHTML = '<option value="">Gagal memuat riwayat</option>';
  }
}

async function handleHistoryImport(event) {
  const file = event.target.files && event.target.files[0];
  if (!file) return;

  const formData = new FormData();
  formData.append("file", file);

  try {
    const response = await fetch(IMPORT_ENDPOINT, {
      method: "POST",
      body: formData,
    });
    const result = await response.json();
    if (!response.ok)
      throw new Error(result.message || `HTTP ${response.status}`);

    alert(
      `Import selesai: ${result.updated} data diperbarui, ${result.created} data baru ditambahkan. Halaman akan dimuat ulang.`,
    );
    window.location.reload();
  } catch (err) {
    console.error(err);
    alert(
      "Gagal import file Excel. Pastikan formatnya sesuai hasil Export Excel.",
    );
  } finally {
    event.target.value = ""; // reset supaya file yang sama bisa dipilih lagi
  }
}

// ==================== HUBUNGKAN KE panel-switcher.js ====================
// Panel "individual" boleh di-render ulang tiap kali tampil lagi (karena ada
// kemungkinan employeeData berubah di masa depan / refresh dari server),
// tapi chart-nya sendiri sudah aman di-destroy dulu di dalam renderTrendChart().
// Panel "team" & "history" cukup di-load sekali per kunjungan tab.

document.addEventListener("panel:show", (e) => {
  const panel = e.detail.panel;

  if (panel === "individual") {
    renderIndividualPanel();
  }

  if (panel === "team" && !renderedPanels.has("team")) {
    renderTeamPanel();
    renderedPanels.add("team");
  }

  if (panel === "history" && !renderedPanels.has("history")) {
    loadHistoryMonths();
    renderedPanels.add("history");
  }
});

document.addEventListener("DOMContentLoaded", () => {
  const importHistoryBtn = document.getElementById("importHistoryBtn");
  const importHistoryInput = document.getElementById("importHistoryInput");
  if (importHistoryBtn && importHistoryInput) {
    importHistoryBtn.addEventListener("click", () =>
      importHistoryInput.click(),
    );
    importHistoryInput.addEventListener("change", handleHistoryImport);
  }

  const monthSelect = document.getElementById("historyMonthSelect");
  if (monthSelect) {
    monthSelect.addEventListener("change", (e) => {
      const snap = historySnapshots.find((s) => s.filename === e.target.value);
      const downloadBtn = document.getElementById("historyDownloadBtn");
      if (snap && downloadBtn) downloadBtn.href = snap.downloadUrl;
      loadHistoryData(e.target.value);
    });
  }

  document.querySelectorAll(".history-subnav__btn").forEach((btn) => {
    btn.addEventListener("click", () => setHistorySubtab(btn.dataset.subtab));
  });
});
