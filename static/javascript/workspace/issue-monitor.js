// ============================================================
// RnD Portal - Issue Monitoring (LVT/MNT)
// Menggunakan API Flask & SQLite/PostgreSQL
// ============================================================

Chart.register(ChartDataLabels);

// ------------------------------------------------------------
// CONFIG: Mapping label -> warna & class
// ------------------------------------------------------------
const CATEGORY_META = {
  "PCBA/SMT": { color: "#b32e2e" },
  "SQA": { color: "#dd3d3d" },
  "Line-Prod": { color: "#f18f34" },
  "OQA": { color: "#2e92cc" },
  "CSS/SVC": { color: "#2e92cc" },
};

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

// STATE DATA
let issueData = [];
let filteredData = [];
let currentPage = 1;
let rowsPerPage = 10;
let categoryChart, eventChart, statusChart;

// ============================================================
// ---- Fetch Data dari Server API ----
// ============================================================
function fetchIssues() {
  fetch("/workspace/issue-monitor/api/issues")
    .then((res) => {
      if (!res.ok) throw new Error("Gagal mengambil data dari server.");
      return res.json();
    })
    .then((data) => {
      // Map data API agar field-nya sesuai dengan kebutuhan UI JS
      issueData = data.issues.map((item) => ({
        id: item.id,
        title: item.title,
        description: item.description,
        priority: item.priority || "Medium",
        category: item.category,
        event: item.event,
        deadline: item.deadline ? formatDateToDMY(item.deadline) : "-",
        owner: item.owner_name || "Admin",
        status: item.status || "Open",
        image_filename: item.image_filename,
      }));
      filteredData = [...issueData];
      renderAll();
    })
    .catch((err) => console.error("Error Fetching Issues:", err));
}

// Helper Format Tanggal dari YYYY-MM-DD ke DD-MM-YYYY
function formatDateToDMY(ymd) {
  if (!ymd || !ymd.includes("-")) return ymd;
  const [y, m, d] = ymd.split("-");
  return `${d}-${m}-${y}`;
}

// ============================================================
// ---- Nav Tabs ----
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
// ---- Helpers Umum ----
// ============================================================
function normalize(str) {
  return (str || "").toString().toLowerCase().replace(/[\s-]/g, "");
}

function parseDeadline(deadline) {
  if (!deadline || deadline === "-") return new Date();
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

// ============================================================
// ---- Panel Dashboard ----
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
      (ev) => issueData.filter((i) => i.category === cat && i.event === ev).length
    )
  );
}

function getHeatColor(value, max) {
  const intensity = max === 0 ? 0 : value / max;
  const lightness = 95 - intensity * 55;
  return `hsl(341, 100%, ${lightness}%)`;
}

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
  categoryChart = new Chart(document.getElementById("category"), {
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
  eventChart = new Chart(document.getElementById("event"), {
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

function renderStatusChart() {
  const data = computeStatusData();
  const max = Math.max(1, ...data.map((d) => d.value));
  const colors = data.map((d) => statusColorFromClass(d.label));
  if (statusChart) {
    statusChart.data.labels = data.map((d) => d.label);
    statusChart.data.datasets[0].data = data.map((d) => d.value);
    statusChart.data.datasets[0].backgroundColor = colors;
    statusChart.options.scales.x.max = max;
    statusChart.update();
    return;
  }
  statusChart = new Chart(document.getElementById("status"), {
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
  if (!table) return;
  const categories = Object.keys(CATEGORY_META);
  const events = Object.keys(EVENT_META);
  const matrixData = computeMatrixData();
  const max = Math.max(1, ...matrixData.flat());

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

function setText(id, value) {
  const el = document.getElementById(id);
  if (el) el.textContent = value;
}

// ============================================================
// ---- Panel Issue Register ----
// ============================================================
function initIssueRegister() {
  flatpickr("#issueDate", {
    dateFormat: "Y-m-d",
    altInput: true,
    altFormat: "d - m - Y",
    allowInput: true,
    minDate: "today",
  });

  const form = document.getElementById("issueForm");
  if (!form) return;

  form.addEventListener("submit", (e) => {
    e.preventDefault();

    const title = document.getElementById("issueTitle").value.trim();
    const category = document.getElementById("issueCategory").value;
    const event = document.getElementById("issueEvent").value;
    const description = document.getElementById("issueDescription").value.trim();
    const deadline = document.getElementById("issueDate").value;
    const fileInput = document.getElementById("issueFile");

    if (!title || !category || !event || !description || !deadline) {
      alert("Mohon lengkapi semua field sebelum submit.");
      return;
    }

    // Kirim menggunakan FormData agar mendukung upload file gambar
    const formData = new FormData();
    formData.append("title", title);
    formData.append("category", category);
    formData.append("event", event);
    formData.append("description", description);
    formData.append("deadline", deadline);
    if (fileInput && fileInput.files[0]) {
      formData.append("image", fileInput.files[0]);
    }

    fetch("/workspace/issue-monitor/api/issues", {
      method: "POST",
      body: formData,
    })
      .then((res) => {
        if (!res.ok) throw new Error("Gagal mendaftarkan issue.");
        return res.json();
      })
      .then((data) => {
        alert(data.message || "Issue berhasil didaftarkan.");
        form.reset();
        fetchIssues(); // Refresh data dari server
        switchTab("list-issue");
      })
      .catch((err) => {
        console.error(err);
        alert("Terjadi kesalahan saat mendaftarkan issue.");
      });
  });
}

// ============================================================
// ---- Panel List Issue & Detail Dinamis ----
// ============================================================
function renderTable() {
  const tbody = document.getElementById("issueTableBody");
  if (!tbody) return;
  tbody.innerHTML = "";

  const start = (currentPage - 1) * rowsPerPage;
  const pageData = filteredData.slice(start, start + rowsPerPage);

  pageData.forEach((issue, i) => {
    const row = document.createElement("tr");
    row.dataset.issueId = issue.id;
    row.style.cursor = "pointer";
    row.innerHTML = `
      <td>${start + i + 1}</td>
      <td><strong>${issue.title}</strong></td>
      <td class="center"><span class="badge ${PRIORITY_CLASS[issue.priority] || ""}">${issue.priority}</span></td>
      <td class="center">${issue.category}</td>
      <td class="center">${issue.event}</td>
      <td class="center">${issue.deadline}</td>
      <td>${issue.owner}</td>
      <td class="center"><span class="badge ${STATUS_CLASS[issue.status] || ""}">${issue.status}</span></td>
      <td class="center">
        <div class="action-buttons">
          <button type="button" class="action-btn" data-action="hold" title="Toggle Hold"><i class="bxf bx-lock"></i></button>
          <button type="button" class="action-btn" data-action="detail" title="Lihat Detail"><i class="bxf bx-folder"></i></button>
        </div>
      </td>
    `;
    tbody.appendChild(row);
  });

  renderPaginationSummary(start, start + pageData.length);
  renderPaginationPages();
}

// FUNGSI UNTUK MENAMPILKAN DETAIL DI BAWAH TABEL
function showIssueDetail(issueId) {
  const issue = issueData.find((i) => i.id === issueId);
  if (!issue) return;

  // Timpa elemen detail dengan data baru
  document.getElementById("detailTitle").innerText = `Issue #${issue.id}: ${issue.title}`;
  document.getElementById("detailId").innerText = `#${issue.id}`;
  document.getElementById("detailCategory").innerText = issue.category || "-";
  document.getElementById("detailEvent").innerText = issue.event || "-";
  document.getElementById("detailOwner").innerText = issue.owner || "-";
  document.getElementById("detailStatus").innerText = issue.status;
  document.getElementById("detailPriority").innerText = issue.priority;
  document.getElementById("detailDeadline").innerText = issue.deadline || "-";
  document.getElementById("detailDescription").innerText = issue.description || "-";

  // Tampilkan Gambar dari static/assets/upload/
  const imageWrapper = document.getElementById("detailImageWrapper");
  if (issue.image_filename) {
    imageWrapper.innerHTML = `
      <img src="/static/assets/upload/${issue.image_filename}" 
           alt="Lampiran Issue #${issue.id}" 
           style="max-width: 100%; max-height: 400px; border-radius: 6px; box-shadow: 0 2px 8px rgba(0,0,0,0.1);">
    `;
  } else {
    imageWrapper.innerHTML = `<span style="color: #888;">Tidak ada lampiran gambar untuk issue ini.</span>`;
  }

  // Tampilkan section & scroll ke area detail
  const detailSection = document.getElementById("issueDetailSection");
  if (detailSection) {
    detailSection.style.display = "block";
    detailSection.scrollIntoView({ behavior: "smooth", block: "start" });
  }
}

function closeIssueDetail() {
  const detailSection = document.getElementById("issueDetailSection");
  if (detailSection) detailSection.style.display = "none";
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

function initListIssue() {
  const rowsSelect = document.getElementById("rowsPerPage");
  if (rowsSelect) {
    rowsSelect.addEventListener("change", (e) => {
      rowsPerPage = parseInt(e.target.value, 10);
      currentPage = 1;
      renderTable();
    });
  }

  // Filters
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

  const resetBtn = document.getElementById("reset");
  if (resetBtn) {
    resetBtn.addEventListener("click", (e) => {
      e.preventDefault();
      document.getElementById("s_f")?.reset();
      applyFilters();
    });
  }

  // Export
  document.getElementById("exportCsv")?.addEventListener("click", (e) => { e.preventDefault(); exportData("csv"); });
  document.getElementById("exportExcel")?.addEventListener("click", (e) => { e.preventDefault(); exportData("xls"); });

  // Event Listener Klik Baris / Tombol Action di Tabel
  const tbody = document.getElementById("issueTableBody");
  if (tbody) {
    tbody.addEventListener("click", (e) => {
      const row = e.target.closest("tr");
      if (!row) return;

      const issueId = Number(row.dataset.issueId);
      const btn = e.target.closest(".action-btn");

      if (btn) {
        e.stopPropagation();
        const action = btn.dataset.action;
        if (action === "hold") {
          toggleIssueStatus(issueId);
        } else if (action === "detail") {
          showIssueDetail(issueId);
        }
      } else {
        // Klik di mana saja pada baris tabel akan membuka detail di bawah
        showIssueDetail(issueId);
      }
    });
  }
}

function toggleIssueStatus(issueId) {
  const issue = issueData.find((i) => i.id === issueId);
  if (!issue) return;

  const newStatus = issue.status === "On Hold" ? "Open" : "On Hold";

  fetch(`/workspace/issue-monitor/api/issues/${issueId}/status`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ status: newStatus }),
  })
    .then((res) => {
      if (!res.ok) throw new Error("Gagal memperbarui status.");
      return res.json();
    })
    .then(() => fetchIssues())
    .catch((err) => console.error(err));
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
      if (normalize(issue.status) !== normalize(statusVal)) return false;
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
// ---- Panel Priority Matrix ----
// ============================================================
function renderIssueCard(issue) {
  const daysLeft = daysUntil(issue.deadline);
  const urgency = urgencyMeta(daysLeft);
  const catColor = CATEGORY_META[issue.category]?.color || "#8a8f98";

  return `
    <div class="pm-card" style="cursor:pointer;" onclick="switchTab('list-issue'); showIssueDetail(${issue.id});">
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
  });
}

// ============================================================
// ---- Render All + Init ----
// ============================================================
function renderAll() {
  renderDashboardSummary();
  renderCategoryChart();
  renderEventChart();
  renderStatusChart();
  renderMatrixTable();
  applyFilters();
  renderPriorityMatrix();
}

document.addEventListener("DOMContentLoaded", () => {
  initTabs();
  initIssueRegister();
  initListIssue();
  fetchIssues(); // Mengambil data awal dari database lewat API
});