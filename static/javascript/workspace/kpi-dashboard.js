// ====================================================================
// KPI Dashboard -- frontend controller
// ====================================================================

const API_BASE = "/workspace/kpi-dashboard";
const EMPLOYEES_ENDPOINT = `${API_BASE}/api/employees`;
const EMPLOYEE_DETAIL_ENDPOINT = `${API_BASE}/api/employees`;
const TEAM_ENDPOINT = `${API_BASE}/api/team`;
const HISTORY_LIST_ENDPOINT = `${API_BASE}/history`;

function el(id) {
  return document.getElementById(id);
}

async function fetchJSON(url) {
  const response = await fetch(url);
  if (!response.ok) throw new Error(`HTTP ${response.status}`);
  return response.json();
}

// ==================== Component: Range Tabs (This Month/Last Week/Last Month/Last Year) ====================

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

// ==================== Panel: Individual (used live & in History) ====================

// `getMonth` is only given by the History panels: it returns the archive month
// ("YYYY-MM") chosen in the Archive Month dropdown. Without it (live panels)
// the range tabs decide the period.
function createEmployeePanelController(ids, rangeScope, getMonth) {
  let chart = null;
  let employees = [];
  let activeId = null;
  let range = "recent";

  function periodQuery() {
    const month = getMonth ? getMonth() : "";
    return month ? `month=${month}` : `range=${range}`;
  }

  function renderTable() {
    const tbody = el(ids.tableBody);
    if (!tbody) return;

    if (employees.length === 0) {
      tbody.innerHTML =
        '<tr><td colspan="3" class="center">No data.</td></tr>';
      return;
    }

    tbody.innerHTML = employees
      .map(
        (emp) => `
      <tr data-id="${emp.id}" class="${emp.id === activeId ? "is-active" : ""}">
        <td title="${escapeHtml(emp.name)}">${escapeHtml(emp.name)}</td>
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
          <span class="insight__label">Lightest Workload</span>
          <span class="insight__value">${escapeHtml(insights.lightest.name)} &middot; ${insights.lightest.hours.toFixed(1)}h</span>
        </div>
      </div>
      <div class="insight insight--danger">
        <span class="insight__dot" style="background:${insights.heaviest.color}"></span>
        <div>
          <span class="insight__label">Needs Attention</span>
          <span class="insight__value">${escapeHtml(insights.heaviest.name)} &middot; ${insights.heaviest.hours.toFixed(1)}h</span>
        </div>
      </div>
    `;
  }

  function renderChart(trend) {
    const canvas = el(ids.chart);
    if (!canvas) return;
    if (chart) chart.destroy();

    // Every day of the period is on the axis (1 .. last day of the month);
    // days that have not happened yet are null, so the line stops at today.
    const line = (label, data, color, extra = {}) => ({
      label,
      data,
      borderColor: color,
      backgroundColor: color,
      fill: false,
      tension: 0,
      pointRadius: 2,
      pointHoverRadius: 4,
      spanGaps: false,
      ...extra,
    });

    chart = new Chart(canvas, {
      type: "line",
      data: {
        labels: trend.labels,
        datasets: [
          line("Resolved", trend.resolved, "#3ddc97"),
          line("Available", trend.available, "#4f8cff"),
          line("Pending", trend.pending, "#f2a623"),
          line("Overdue", trend.overdue, "#e24b4a", { borderDash: [4, 3] }),
        ],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        interaction: { mode: "index", intersect: false },
        plugins: {
          legend: { position: "bottom" },
          tooltip: {
            callbacks: {
              title: (items) =>
                items.length ? `${items[0].label} \u00b7 ${trend.title}` : "",
            },
          },
        },
        scales: {
          x: {
            title: { display: true, text: trend.title },
            ticks: { autoSkip: trend.labels.length > 31, maxRotation: 0 },
            grid: { display: false },
          },
          y: { beginAtZero: true, ticks: { precision: 0 } },
        },
      },
    });
  }

  function renderContent(detail) {
    const container = el(ids.content);
    if (!container) return;

    container.innerHTML = `
      <div class="emp-profile">
        <span class="emp-avatar emp-avatar--lg" style="background:${detail.completionRateColor}22; color:${detail.completionRateColor}">${escapeHtml(detail.initials)}</span>
        <div>
          <div class="emp-profile__name">${escapeHtml(detail.name)}</div>
          <div class="emp-profile__role">${escapeHtml(detail.role)} &middot; ${escapeHtml(detail.team)}</div>
        </div>
      </div>
      <div class="emp-stats">
        <div class="emp-stat"><span class="emp-stat__label">Total Assigned</span><span class="emp-stat__value">${detail.totalAssigned}</span></div>
        <div class="emp-stat"><span class="emp-stat__label">Completed</span><span class="emp-stat__value">${detail.completed}</span></div>
        <div class="emp-stat"><span class="emp-stat__label">Available</span><span class="emp-stat__value">${detail.available}</span></div>
        <div class="emp-stat"><span class="emp-stat__label">Pending</span><span class="emp-stat__value">${detail.pending}</span></div>
        <div class="emp-stat ${detail.overdue > 0 ? "emp-stat--danger" : ""}"><span class="emp-stat__label">Overdue</span><span class="emp-stat__value">${detail.overdue}</span></div>
        <div class="emp-stat"><span class="emp-stat__label">Completion Rate</span><span class="emp-stat__value">${detail.completionRate}%</span></div>
        <div class="emp-stat"><span class="emp-stat__label">Avg. Resolution</span><span class="emp-stat__value">${detail.avgResolutionHours} hours</span></div>
      </div>
      <div class="emp-notes">
        <span class="emp-notes__title">Best Practice Notes &middot; ${escapeHtml(detail.rangeLabel)}</span>
        <ul>${detail.bestPractices.map((note) => `<li>${escapeHtml(note)}</li>`).join("")}</ul>
      </div>
    `;
  }

  async function loadDetail() {
    if (activeId == null) return;
    try {
      const detail = await fetchJSON(
        `${EMPLOYEE_DETAIL_ENDPOINT}/${activeId}?${periodQuery()}`,
      );
      renderChart(detail.trend);
      renderContent(detail);
    } catch (err) {
      console.error(err);
    }
  }

  async function load() {
    try {
      const data = await fetchJSON(`${EMPLOYEES_ENDPOINT}?${periodQuery()}`);
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

// ==================== Panel: Team (used live & in History) ====================

function createTeamPanelController(ids, rangeScope, getMonth) {
  let chart = null;
  let range = "recent";

  function periodQuery() {
    const month = getMonth ? getMonth() : "";
    return month ? `month=${month}` : `range=${range}`;
  }

  function renderSummary(totals, rate) {
    const container = el(ids.summary);
    if (!container) return;

    container.innerHTML = `
      <div class="emp-stats emp-stats--team">
        <div class="emp-stat"><span class="emp-stat__label">Total Assigned</span><span class="emp-stat__value">${totals.totalAssigned}</span></div>
        <div class="emp-stat"><span class="emp-stat__label">Completed</span><span class="emp-stat__value">${totals.completed}</span></div>
        <div class="emp-stat"><span class="emp-stat__label">Available</span><span class="emp-stat__value">${totals.available}</span></div>
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
            label: "Available",
            data: chartData.available,
            backgroundColor: "#4f8cff",
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
        <span class="emp-avatar" style="background:${emp.completionRateColor}22; color:${emp.completionRateColor}">${escapeHtml(emp.initials)}</span>
        <div class="team-leaderboard__info">
          <span class="team-leaderboard__name">${escapeHtml(emp.name)}</span>
          <span class="team-leaderboard__team">${escapeHtml(emp.role)}</span>
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
      const data = await fetchJSON(`${TEAM_ENDPOINT}?${periodQuery()}`);
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

// ==================== Controller instances ====================

// Archive month chosen in History ("2026-11"), or "" before the list has loaded.
function selectedHistoryMonth() {
  const select = el("historyMonthSelect");
  return select && select.value ? select.value.replace(".xlsx", "") : "";
}

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
  selectedHistoryMonth,
);

const historyTeamPanel = createTeamPanelController(
  {
    summary: "historyTeamSummary",
    chart: "historyTeamComparisonChart",
    leaderboard: "historyTeamLeaderboard",
  },
  "history-team",
  selectedHistoryMonth,
);

// ==================== Monthly Excel archive (Export per selected month) ====================
let historySnapshots = [];
let historyMonthsLoaded = false;

function currentMonthFilename() {
  const now = new Date();
  return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, "0")}.xlsx`;
}

function renderHistoryMonthOptions() {
  const select = el("historyMonthSelect");
  if (!select) return;

  if (historySnapshots.length === 0) {
    select.innerHTML = '<option value="">No archive yet</option>';
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
              ? `${snap.label} (This month)`
              : snap.label;
          return `<option value="${escapeHtml(snap.filename)}">${escapeHtml(label)}</option>`;
        })
        .join("");
      return `<optgroup label="${escapeHtml(year)}">${options}</optgroup>`;
    })
    .join("");
}

// Every item of the Export dropdown (Individual / Team, Excel / PDF) exports
// the month currently chosen in the Archive Month dropdown ("YYYY-MM" is sent
// as ?month=; the PDF links already carry ?format=pdf).
function updateExportLinks() {
  const select = el("historyMonthSelect");
  const monthKey = select && select.value ? select.value.replace(".xlsx", "") : "";

  document.querySelectorAll("[data-export-link]").forEach((link) => {
    if (!link.dataset.baseHref) link.dataset.baseHref = link.getAttribute("href");
    const url = new URL(link.dataset.baseHref, window.location.origin);
    if (monthKey) url.searchParams.set("month", monthKey);
    link.href = url.pathname + url.search;
  });
}

// ---- Export dropdown: open / close ----
function initExportMenu() {
  const menu = el("exportMenu");
  const btn = el("exportMenuBtn");
  const list = el("exportMenuList");
  if (!menu || !btn || !list) return;

  const setOpen = (open) => {
    list.classList.toggle("is-hidden", !open);
    btn.setAttribute("aria-expanded", String(open));
    menu.classList.toggle("is-open", open);
  };

  btn.addEventListener("click", (e) => {
    e.stopPropagation();
    setOpen(list.classList.contains("is-hidden"));
  });
  // Choosing an item starts the download and closes the menu
  list.addEventListener("click", (e) => {
    if (e.target.closest("[data-export-link]")) setOpen(false);
  });
  document.addEventListener("click", (e) => {
    if (!menu.contains(e.target)) setOpen(false);
  });
  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape") setOpen(false);
  });
}

function selectHistoryMonthByIndex(index) {
  const select = el("historyMonthSelect");
  if (!select || historySnapshots[index] == null) return;

  select.value = historySnapshots[index].filename;
  onHistoryMonthChanged();
}

// A different archive month: refresh export links, arrows AND the data shown.
function onHistoryMonthChanged() {
  updateExportLinks();
  updateHistoryNavButtons();
  reloadHistoryPanels();
}

function reloadHistoryPanels() {
  if (historySubtab === "team") {
    historyTeamPanel.load();
  } else {
    historyIndividualPanel.load();
  }
}

function updateHistoryNavButtons() {
  const select = el("historyMonthSelect");
  const prevBtn = el("historyPrevBtn");
  const nextBtn = el("historyNextBtn");
  if (!select || !prevBtn || !nextBtn) return;

  const index = historySnapshots.findIndex((s) => s.filename === select.value);
  prevBtn.disabled = index === -1 || index >= historySnapshots.length - 1;
  nextBtn.disabled = index <= 0;
}

async function loadHistoryMonths() {
  const select = el("historyMonthSelect");
  if (!select) return;

  try {
    const data = await fetchJSON(HISTORY_LIST_ENDPOINT);
    historySnapshots = data.snapshots || [];

    renderHistoryMonthOptions();
    if (historySnapshots.length === 0) return;

    updateExportLinks();
    updateHistoryNavButtons();
  } catch (err) {
    console.error(err);
    select.innerHTML = '<option value="">Failed to load archive</option>';
  }
}

// ==================== History sub-tabs: Individual / Team ====================

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

// ==================== Wire up to panel-switcher.js ====================

// The month list must be loaded first: the panels below it show the month
// that is selected in the dropdown.
async function openHistory() {
  if (!historyMonthsLoaded) {
    historyMonthsLoaded = true;
    await loadHistoryMonths();
  }
  reloadHistoryPanels();
}

document.addEventListener("panel:show", (e) => {
  const panel = e.detail.panel;

  if (panel === "individual") {
    individualPanel.load();
  }

  if (panel === "team") {
    teamPanel.load();
  }

  if (panel === "history") {
    openHistory();
  }
});

document.addEventListener("DOMContentLoaded", () => {
  initExportMenu();

  const monthSelect = el("historyMonthSelect");
  if (monthSelect) {
    monthSelect.addEventListener("change", onHistoryMonthChanged);
  }

  const prevBtn = el("historyPrevBtn");
  const nextBtn = el("historyNextBtn");
  if (prevBtn) {
    prevBtn.addEventListener("click", () => {
      const index = historySnapshots.findIndex(
        (s) => s.filename === el("historyMonthSelect").value,
      );
      if (index !== -1) selectHistoryMonthByIndex(index + 1);
    });
  }
  if (nextBtn) {
    nextBtn.addEventListener("click", () => {
      const index = historySnapshots.findIndex(
        (s) => s.filename === el("historyMonthSelect").value,
      );
      if (index !== -1) selectHistoryMonthByIndex(index - 1);
    });
  }

  document.querySelectorAll(".history-subnav__btn").forEach((btn) => {
    btn.addEventListener("click", () => setHistorySubtab(btn.dataset.subtab));
  });
});
