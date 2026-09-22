// ====================================================================
// KPI Dashboard -- frontend controller
//
// Semua data & kalkulasi (workload bar, completion rate, leaderboard,
// agregasi Recent/Last Week/Last Month/Last Year, trend chart) sekarang
// datang SUDAH JADI dari backend (lihat library/workspace/kpi_dashboard/
// metrics.py & routes.py). File ini murni:
//   1. fetch data dari /workspace/kpi-dashboard/api/*
//   2. render ke DOM
//   3. jalankan Chart.js (satu-satunya bagian yang memang wajib di
//      client, karena Chart.js adalah library rendering canvas)
//
// createEmployeePanelController() & createTeamPanelController() dipakai
// DUA KALI: sekali untuk panel live (Individual/Team), sekali lagi untuk
// sub-panel History (Individual/Team) -- makanya kedua tempat itu selalu
// tampil identik (layout + filter rentang waktu).
// ====================================================================

const API_BASE = "/workspace/kpi-dashboard";
const EMPLOYEES_ENDPOINT = `${API_BASE}/api/employees`;
const EMPLOYEE_DETAIL_ENDPOINT = `${API_BASE}/api/employees`;
const TEAM_ENDPOINT = `${API_BASE}/api/team`;
const HISTORY_LIST_ENDPOINT = `${API_BASE}/history`;
const IMPORT_ENDPOINT = `${API_BASE}/import`;

function el(id) {
  return document.getElementById(id);
}

async function fetchJSON(url) {
  const response = await fetch(url);
  if (!response.ok) throw new Error(`HTTP ${response.status}`);
  return response.json();
}

// ==================== Komponen: Range Tabs (Recent/Last Week/Last Month/Last Year) ====================

function setupRangeTabs(scope, onChange) {
  const group = document.querySelector(
    `.range-tabs[data-range-scope="${scope}"]`,
  );
  if (!group) return;

  group.querySelectorAll(".range-tabs__btn").forEach((btn) => {
    btn.addEventListener("click", () => {
      if (btn.classList.contains("active")) return;
      group
        .querySelectorAll(".range-tabs__btn")
        .forEach((b) => b.classList.toggle("active", b === btn));
      onChange(btn.dataset.range);
    });
  });
}

// ==================== Panel: Individual (dipakai live & History) ====================

function createEmployeePanelController(ids, rangeScope) {
  let chart = null;
  let employees = [];
  let activeId = null;
  let range = "recent";

  function renderTable() {
    const tbody = el(ids.tableBody);
    if (!tbody) return;

    if (employees.length === 0) {
      tbody.innerHTML =
        '<tr><td colspan="3" class="center">Tidak ada data.</td></tr>';
      return;
    }

    tbody.innerHTML = employees
      .map(
        (emp) => `
      <tr data-id="${emp.id}" class="${emp.id === activeId ? "is-active" : ""}">
        <td title="${emp.name}">${emp.name}</td>
        <td>
          <div class="hours-bar-track">
            <div class="hours-bar-fill" style="width:${emp.workload.widthPct}%; background:${emp.workload.color};"></div>
          </div>
        </td>
      </tr>
    `,
      )
      .join("");

    tbody.querySelectorAll("tr[data-id]").forEach((row) => {
      row.addEventListener("click", () => {
        activeId = Number(row.dataset.id);
        renderTable();
        loadDetail();
      });
    });
  }

  function renderInsights(insights) {
    const container = el(ids.insights);
    if (!container) return;
    if (!insights) {
      container.innerHTML = "";
      return;
    }

    container.innerHTML = `
      <div class="insight">
        <span class="insight__dot" style="background:${insights.lightest.color}"></span>
        <div>
          <span class="insight__label">Beban Paling Ringan</span>
          <span class="insight__value">${insights.lightest.name} &middot; ${insights.lightest.hours.toFixed(1)}h</span>
        </div>
      </div>
      <div class="insight insight--danger">
        <span class="insight__dot" style="background:${insights.heaviest.color}"></span>
        <div>
          <span class="insight__label">Perlu Perhatian</span>
          <span class="insight__value">${insights.heaviest.name} &middot; ${insights.heaviest.hours.toFixed(1)}h</span>
        </div>
      </div>
    `;
  }

  function renderChart(trend) {
    const canvas = el(ids.chart);
    if (!canvas) return;
    if (chart) chart.destroy();

    chart = new Chart(canvas, {
      type: "line",
      data: {
        labels: trend.labels,
        datasets: [
          {
            label: "Resolved",
            data: trend.resolved,
            borderColor: "#4f8cff",
            backgroundColor: "rgba(79, 140, 255, 0.12)",
            fill: false,
            tension: 0,
            pointRadius: 3,
          },
          {
            label: "Pending",
            data: trend.pending,
            borderColor: "#f2a623",
            backgroundColor: "rgba(242, 166, 35, 0.12)",
            fill: false,
            tension: 0,
            pointRadius: 3,
          },
          {
            label: "Overdue",
            data: trend.overdue,
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

  function renderContent(detail) {
    const container = el(ids.content);
    if (!container) return;

    container.innerHTML = `
      <div class="emp-profile">
        <span class="emp-avatar emp-avatar--lg" style="background:${detail.completionRateColor}22; color:${detail.completionRateColor}">${detail.initials}</span>
        <div>
          <div class="emp-profile__name">${detail.name}</div>
          <div class="emp-profile__role">${detail.role} &middot; ${detail.team}</div>
        </div>
      </div>
      <div class="emp-stats">
        <div class="emp-stat"><span class="emp-stat__label">Total Assigned</span><span class="emp-stat__value">${detail.totalAssigned}</span></div>
        <div class="emp-stat"><span class="emp-stat__label">Completed</span><span class="emp-stat__value">${detail.completed}</span></div>
        <div class="emp-stat"><span class="emp-stat__label">Pending</span><span class="emp-stat__value">${detail.pending}</span></div>
        <div class="emp-stat ${detail.overdue > 0 ? "emp-stat--danger" : ""}"><span class="emp-stat__label">Overdue</span><span class="emp-stat__value">${detail.overdue}</span></div>
        <div class="emp-stat"><span class="emp-stat__label">Completion Rate</span><span class="emp-stat__value">${detail.completionRate}%</span></div>
        <div class="emp-stat"><span class="emp-stat__label">Avg. Resolution</span><span class="emp-stat__value">${detail.avgResolutionDays} hari</span></div>
      </div>
      <div class="emp-notes">
        <span class="emp-notes__title">Best Practice Notes &middot; ${detail.rangeLabel}</span>
        <ul>${detail.bestPractices.map((note) => `<li>${note}</li>`).join("")}</ul>
      </div>
    `;
  }

  async function loadDetail() {
    if (activeId == null) return;
    try {
      const detail = await fetchJSON(
        `${EMPLOYEE_DETAIL_ENDPOINT}/${activeId}?range=${range}`,
      );
      renderChart(detail.trend);
      renderContent(detail);
    } catch (err) {
      console.error(err);
    }
  }

  async function load() {
    try {
      const data = await fetchJSON(`${EMPLOYEES_ENDPOINT}?range=${range}`);
      employees = data.employees || [];
      if (activeId == null || !employees.some((e) => e.id === activeId)) {
        activeId = data.activeEmployeeId;
      }
      renderTable();
      renderInsights(data.insights);
      await loadDetail();
    } catch (err) {
      console.error(err);
    }
  }

  setupRangeTabs(rangeScope, (newRange) => {
    range = newRange;
    load();
  });

  return { load };
}

// ==================== Panel: Team (dipakai live & History) ====================

function createTeamPanelController(ids, rangeScope) {
  let chart = null;
  let range = "recent";

  function renderSummary(totals, rate) {
    const container = el(ids.summary);
    if (!container) return;

    container.innerHTML = `
      <div class="emp-stats emp-stats--team">
        <div class="emp-stat"><span class="emp-stat__label">Total Assigned</span><span class="emp-stat__value">${totals.totalAssigned}</span></div>
        <div class="emp-stat"><span class="emp-stat__label">Completed</span><span class="emp-stat__value">${totals.completed}</span></div>
        <div class="emp-stat"><span class="emp-stat__label">Pending</span><span class="emp-stat__value">${totals.pending}</span></div>
        <div class="emp-stat ${totals.overdue > 0 ? "emp-stat--danger" : ""}"><span class="emp-stat__label">Overdue</span><span class="emp-stat__value">${totals.overdue}</span></div>
        <div class="emp-stat"><span class="emp-stat__label">Team Completion Rate</span><span class="emp-stat__value">${rate}%</span></div>
      </div>
    `;
  }

  function renderChart(chartData) {
    const canvas = el(ids.chart);
    if (!canvas) return;
    if (chart) chart.destroy();

    chart = new Chart(canvas, {
      type: "bar",
      data: {
        labels: chartData.labels,
        datasets: [
          {
            label: "Completed",
            data: chartData.completed,
            backgroundColor: "#3ddc97",
            borderRadius: 4,
          },
          {
            label: "Pending",
            data: chartData.pending,
            backgroundColor: "#f2a623",
            borderRadius: 4,
          },
          {
            label: "Overdue",
            data: chartData.overdue,
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

  function renderLeaderboard(leaderboard) {
    const container = el(ids.leaderboard);
    if (!container) return;

    container.innerHTML = leaderboard
      .map(
        (emp) => `
      <div class="team-leaderboard__row">
        <span class="team-leaderboard__rank">#${emp.rank}</span>
        <span class="emp-avatar" style="background:${emp.completionRateColor}22; color:${emp.completionRateColor}">${emp.initials}</span>
        <div class="team-leaderboard__info">
          <span class="team-leaderboard__name">${emp.name}</span>
          <span class="team-leaderboard__team">${emp.role}</span>
        </div>
        <div class="team-leaderboard__bar-wrap">
          <div class="hours-bar-track">
            <div class="hours-bar-fill" style="width:${emp.completionRate}%; background:${emp.completionRateColor};"></div>
          </div>
          <span class="team-leaderboard__rate">${emp.completionRate}%</span>
        </div>
      </div>
    `,
      )
      .join("");
  }

  async function load() {
    try {
      const data = await fetchJSON(`${TEAM_ENDPOINT}?range=${range}`);
      renderSummary(data.totals, data.completionRate);
      renderLeaderboard(data.leaderboard);
      renderChart(data.chart);
    } catch (err) {
      console.error(err);
    }
  }

  setupRangeTabs(rangeScope, (newRange) => {
    range = newRange;
    load();
  });

  return { load };
}

// ==================== Instansiasi controller ====================
// Panel Individual & Team "live", plus sub-panel History Individual/Team
// yang memakai controller & endpoint yang SAMA PERSIS, supaya keempatnya
// selalu konsisten.

const individualPanel = createEmployeePanelController(
  {
    tableBody: "employeeTableBody",
    insights: "employeeInsights",
    chart: "empTrendChart",
    content: "empContent",
  },
  "individual",
);

const teamPanel = createTeamPanelController(
  {
    summary: "teamSummary",
    chart: "teamComparisonChart",
    leaderboard: "teamLeaderboard",
  },
  "team",
);

const historyIndividualPanel = createEmployeePanelController(
  {
    tableBody: "historyEmployeeTableBody",
    insights: "historyEmployeeInsights",
    chart: "historyEmpTrendChart",
    content: "historyEmpContent",
  },
  "history-individual",
);

const historyTeamPanel = createTeamPanelController(
  {
    summary: "historyTeamSummary",
    chart: "historyTeamComparisonChart",
    leaderboard: "historyTeamLeaderboard",
  },
  "history-team",
);

// ==================== Arsip Excel bulanan (Import/Export/Download) ====================
// Bagian ini TIDAK terkait dengan filter Recent/Last Week/Last Month/Last
// Year -- murni untuk mengelola file .xlsx arsip bulanan yang sudah
// pernah di-export (fitur lama, tetap dipertahankan).

let historySnapshots = [];
let historyMonthsLoaded = false;

// "Bulan Arsip lebih advance": dikelompokkan per tahun (optgroup), ditandai
// kalau itu bulan berjalan, dan bisa dinavigasi lewat tombol Prev/Next
// tanpa perlu buka dropdown-nya.

function currentMonthFilename() {
  const now = new Date();
  return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, "0")}.xlsx`;
}

function renderHistoryMonthOptions() {
  const select = el("historyMonthSelect");
  if (!select) return;

  if (historySnapshots.length === 0) {
    select.innerHTML = '<option value="">Belum ada arsip</option>';
    return;
  }

  const thisMonth = currentMonthFilename();
  const byYear = new Map();
  historySnapshots.forEach((snap) => {
    const year = snap.filename.split("-")[0];
    if (!byYear.has(year)) byYear.set(year, []);
    byYear.get(year).push(snap);
  });

  select.innerHTML = [...byYear.entries()]
    .map(([year, snaps]) => {
      const options = snaps
        .map((snap) => {
          const label =
            snap.filename === thisMonth
              ? `${snap.label} (Bulan ini)`
              : snap.label;
          return `<option value="${snap.filename}">${label}</option>`;
        })
        .join("");
      return `<optgroup label="${year}">${options}</optgroup>`;
    })
    .join("");
}

function selectHistoryMonthByIndex(index) {
  const select = el("historyMonthSelect");
  const downloadBtn = el("historyDownloadBtn");
  if (!select || historySnapshots[index] == null) return;

  select.value = historySnapshots[index].filename;
  if (downloadBtn) downloadBtn.href = historySnapshots[index].downloadUrl;
  updateHistoryNavButtons();
}

function updateHistoryNavButtons() {
  const select = el("historyMonthSelect");
  const prevBtn = el("historyPrevBtn");
  const nextBtn = el("historyNextBtn");
  if (!select || !prevBtn || !nextBtn) return;

  const index = historySnapshots.findIndex((s) => s.filename === select.value);
  // historySnapshots urut dari terbaru -> terlama, jadi "sebelumnya" = index+1.
  prevBtn.disabled = index === -1 || index >= historySnapshots.length - 1;
  nextBtn.disabled = index <= 0;
}

async function loadHistoryMonths() {
  const select = el("historyMonthSelect");
  const downloadBtn = el("historyDownloadBtn");
  if (!select) return;

  try {
    const data = await fetchJSON(HISTORY_LIST_ENDPOINT);
    historySnapshots = data.snapshots || [];

    renderHistoryMonthOptions();
    if (historySnapshots.length === 0) return;

    if (downloadBtn) downloadBtn.href = historySnapshots[0].downloadUrl;
    updateHistoryNavButtons();
  } catch (err) {
    console.error(err);
    select.innerHTML = '<option value="">Gagal memuat arsip</option>';
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

    showToast(
      `Import selesai: ${result.updated} data diperbarui, ${result.created} data baru ditambahkan.`,
      "success",
    );
  } catch (err) {
    console.error(err);
    showToast(
      "Gagal import file Excel. Pastikan formatnya sesuai hasil Export Excel.",
      "error",
    );
  } finally {
    event.target.value = ""; // reset supaya file yang sama bisa dipilih lagi
  }
}

// ==================== Sub-tab History: Individual / Team ====================

let historySubtab = "individual";

function setHistorySubtab(subtab) {
  historySubtab = subtab;

  document.querySelectorAll(".history-subnav__btn").forEach((btn) => {
    btn.classList.toggle("active", btn.dataset.subtab === subtab);
  });
  document.querySelectorAll(".history-subpanel").forEach((panel) => {
    panel.style.display = panel.dataset.subpanel === subtab ? "" : "none";
  });

  if (subtab === "team") {
    historyTeamPanel.load();
  } else {
    historyIndividualPanel.load();
  }
}

// ==================== Kartu Ringkasan Global (independen dari tab aktif) ====================

async function loadKpiOverview() {
  try {
    const data = await fetchJSON(`${TEAM_ENDPOINT}?range=recent`);
    el("ovAssigned").textContent = data.totals.totalAssigned;
    el("ovCompleted").textContent = data.totals.completed;
    el("ovPending").textContent = data.totals.pending;
    el("ovOverdue").textContent = data.totals.overdue;
    el("ovRate").textContent = `${data.completionRate}%`;
    el("ovCaption").textContent = data.rangeLabel;
  } catch (err) {
    console.error(err);
  }
}

// ==================== Hubungkan ke panel-switcher.js ====================

document.addEventListener("panel:show", (e) => {
  const panel = e.detail.panel;

  if (panel === "individual") {
    individualPanel.load();
  }

  if (panel === "team") {
    teamPanel.load();
  }

  if (panel === "history") {
    if (!historyMonthsLoaded) {
      loadHistoryMonths();
      historyMonthsLoaded = true;
    }
    if (historySubtab === "team") {
      historyTeamPanel.load();
    } else {
      historyIndividualPanel.load();
    }
  }
});

document.addEventListener("DOMContentLoaded", () => {
  loadKpiOverview();

  const importHistoryBtn = el("importHistoryBtn");
  const importHistoryInput = el("importHistoryInput");
  if (importHistoryBtn && importHistoryInput) {
    importHistoryBtn.addEventListener("click", () =>
      importHistoryInput.click(),
    );
    importHistoryInput.addEventListener("change", handleHistoryImport);
  }

  const monthSelect = el("historyMonthSelect");
  if (monthSelect) {
    monthSelect.addEventListener("change", (e) => {
      const snap = historySnapshots.find((s) => s.filename === e.target.value);
      const downloadBtn = el("historyDownloadBtn");
      if (snap && downloadBtn) downloadBtn.href = snap.downloadUrl;
      updateHistoryNavButtons();
    });
  }

  const prevBtn = el("historyPrevBtn");
  const nextBtn = el("historyNextBtn");
  if (prevBtn) {
    prevBtn.addEventListener("click", () => {
      const index = historySnapshots.findIndex(
        (s) => s.filename === el("historyMonthSelect").value,
      );
      if (index !== -1) selectHistoryMonthByIndex(index + 1); // +1 = bulan lebih lama
    });
  }
  if (nextBtn) {
    nextBtn.addEventListener("click", () => {
      const index = historySnapshots.findIndex(
        (s) => s.filename === el("historyMonthSelect").value,
      );
      if (index !== -1) selectHistoryMonthByIndex(index - 1); // -1 = bulan lebih baru
    });
  }

  document.querySelectorAll(".history-subnav__btn").forEach((btn) => {
    btn.addEventListener("click", () => setHistorySubtab(btn.dataset.subtab));
  });
});
