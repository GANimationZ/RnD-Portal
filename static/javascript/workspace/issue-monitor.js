// ============================================================
// RnD Portal - Issue Monitoring (LVT/MNT)
// Every panel (Dashboard, Issue Register, List Issue, Priority
// Matrix) shares one data source: `issueData`, fetched from
// /workspace/issue-monitor/api/issues.
//
// Tab switching (.nav-item__left clicks) is handled by
// static/javascript/workspace/panel-switcher.js, loaded globally
// via the layout -- this file has no tab logic of its own.
// ============================================================

Chart.register(ChartDataLabels);

const API_BASE = "/workspace/issue-monitor/api";

// ------------------------------------------------------------
// CONFIG: label -> color mapping
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

// Attachment icon per file type (see issue_monitor routes.py -> get_file_type())
// -- restricted to boxicons class names that actually exist in vendor/boxicons.
const ATTACHMENT_ICON = {
  image: "bx-image",
  pdf: "bx-file",
  word: "bx-file",
  excel: "bx-file",
  ppt: "bx-slideshow",
  other: "bx-file",
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

const CATEGORY_VALUE_MAP = {
  pcba_smt: "PCBA/SMT",
  SQA: "SQA",
  "Line-Prod": "Line-Prod",
  OQA: "OQA",
  css_svc: "CSS/SVC",
};

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
// ---- Generic helpers ---- //
// ============================================================
function normalize(str) {
  return (str || "").toString().toLowerCase().replace(/[\s-]/g, "");
}

function parseDeadline(deadline) {
  // format: dd-mm-yyyy (from the API)
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

function setText(id, value) {
  const el = document.getElementById(id);
  if (el) el.textContent = value;
}

// ============================================================
// ---- Data layer: fetch from API ---- //
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

// ============================================================
// ---- Dashboard panel ---- //
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
  const el = document.getElementById("category");
  if (!el) return;
  categoryChart = new Chart(el, {
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
  const el = document.getElementById("event");
  if (!el) return;
  eventChart = new Chart(el, {
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

function statusColorFromClass(label) {
  const map = { Open: "#2c7db3", Pending: "#f2a623", Closed: "#1e7e33", "On Hold": "#e24b4a" };
  return map[label] || "#8a8f98";
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
  const el = document.getElementById("status");
  if (!el) return;
  statusChart = new Chart(el, {
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

// ============================================================
// ---- Issue Register panel ---- //
// ============================================================

// ---- Assignee combobox: refetched whenever Category & Event change,
// pulling Members whose scope (set in /admin/users) covers BOTH values.
// The endpoint returns [] if either field isn't selected yet. ----
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
  if (document.getElementById("issueDate")) {
    flatpickr("#issueDate", {
      dateFormat: "Y-m-d",
      altInput: true,
      altFormat: "d - m - Y",
      allowInput: true,
      minDate: "today",
    });
  }

  const form = document.getElementById("issueForm");
  if (!form) return;

  document.getElementById("issueCategory")?.addEventListener("change", loadAssignableUsers);
  document.getElementById("issueEvent")?.addEventListener("change", loadAssignableUsers);

  form.addEventListener("submit", async (e) => {
    e.preventDefault();

    const titleEl = document.getElementById("issueTitle");
    const categoryEl = document.getElementById("issueCategory");
    const eventEl = document.getElementById("issueEvent");
    const assigneeEl = document.getElementById("issueAssignee");
    const descEl = document.getElementById("issueDescription");
    const dateEl = document.getElementById("issueDate");
    const fileEl = document.getElementById("issueFile");
    const submitBtn = document.getElementById("sub_btn");

    const title = titleEl.value.trim();
    const categoryVal = categoryEl.value;
    const eventVal = eventEl.value;
    const description = descEl.value.trim();
    const deadlineRaw = dateEl.value; // format Y-m-d from flatpickr

    if (!title || !categoryVal || !eventVal || !description || !deadlineRaw) {
      showToast("Mohon lengkapi semua field sebelum submit.", "error");
      return;
    }

    const formData = new FormData();
    formData.append("title", title);
    formData.append("category", CATEGORY_VALUE_MAP[categoryVal] || categoryVal);
    formData.append("event", EVENT_VALUE_MAP[eventVal] || eventVal);
    formData.append("description", description);
    formData.append("deadline", deadlineRaw);
    if (assigneeEl && assigneeEl.value) {
      formData.append("assignee_id", assigneeEl.value);
    }
    if (fileEl && fileEl.files.length) {
      Array.from(fileEl.files).forEach((file) => formData.append("attachments", file));
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
        showToast(data.message || "Gagal menyimpan issue.", "error");
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
      showToast(`Issue "${data.issue.title}" berhasil didaftarkan.`, "success");
    } catch (err) {
      console.error(err);
      showToast("Terjadi kesalahan saat menghubungi server.", "error");
    } finally {
      if (submitBtn) {
        submitBtn.disabled = false;
        submitBtn.value = originalSubmitValue;
      }
    }
  });
}

// ============================================================
// ---- List Issue panel ---- //
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
      <td>${issue.assignee_name || "-"}</td>
      <td class="center"><span class="badge ${STATUS_CLASS[issue.status] || ""}">${issue.status}</span></td>
      <td class="center">
        <div class="action-buttons">
          ${window.CURRENT_ROLE === "Super Admin" || window.CURRENT_ROLE === "Admin" ? `
          <button type="button" class="action-btn" data-action="hold" title="Hold"><i class="bxf bx-lock"></i></button>
          ` : ""}
          <button type="button" class="action-btn" data-action="info" title="Lihat Detail"><i class="bxf bx-info-circle"></i></button>
          ${window.CURRENT_ROLE === "Super Admin" || window.CURRENT_ROLE === "Admin" ? `
          <button type="button" class="action-btn" data-action="hand" title="Close Issue"><i class="bxf bx-hand"></i></button>
          ` : ""}
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

async function updateIssueStatus(issueId, status, assigneeId) {
  try {
    const body = { status };
    if (assigneeId) body.assignee_id = assigneeId;

    const res = await fetch(`${API_BASE}/issues/${issueId}/status`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    const data = await res.json().catch(() => ({}));
    if (!res.ok) throw new Error(data.message || "Gagal update status");
    await fetchIssues();
    renderAll();
    showToast(data.message || "Status diperbarui.", "success");
    return true;
  } catch (err) {
    console.error(err);
    showToast(err.message || "Gagal memperbarui status issue.", "error");
    return false;
  }
}

function toggleHold(issueId, currentStatus) {
  const nextStatus = currentStatus === "On Hold" ? "Open" : "On Hold";
  return updateIssueStatus(issueId, nextStatus);
}

function applyFilters() {
  const searchVal = (document.getElementById("searchInput")?.value || "").trim().toLowerCase();
  const priorityVal = document.getElementById("filterPriority")?.value || "";
  const statusVal = document.getElementById("filterStatus")?.value || "";
  const categoryVal = document.getElementById("filterCategory")?.value || "";
  const eventVal = document.getElementById("filterEvent")?.value || "";
  const assigneeFilterSelect = document.getElementById("filterAssignee");
  const assigneeFilterText = assigneeFilterSelect
    ? assigneeFilterSelect.options[assigneeFilterSelect.selectedIndex]?.value
    : "All Assignees";

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

    if (assigneeFilterText && assigneeFilterText !== "All Assignees") {
      if (assigneeFilterText === "__unassigned__") {
        if (issue.assignee_name) return false;
      } else if (issue.assignee_name !== assigneeFilterText) {
        return false;
      }
    }

    return true;
  });

  currentPage = 1;
  renderTable();
}

function exportData(type) {
  const rows = [["No", "Title", "Priority", "Category", "Event", "Deadline", "Assignee", "Status"]];
  filteredData.forEach((issue, i) => {
    rows.push([i + 1, issue.title, issue.priority, issue.category, issue.event, issue.deadline, issue.assignee_name || "-", issue.status]);
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
// ---- Inline Detail (modal overlay opened from List Issue) ---- //
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

  // Image (if any) -- backend sends `image_url`, not `image`
  const imgWrapper = document.getElementById("inlineDetailImageWrapper");
  if (imgWrapper) {
    imgWrapper.innerHTML = issue.image_url
      ? `<img src="${issue.image_url}" alt="${issue.title}" />`
      : "";
  }

  // Attachments (Word/Excel/PPT/PDF/image, can be more than one) -- click
  // to preview; the small button in the corner downloads directly.
  const attachmentsWrapper = document.getElementById("inlineDetailAttachments");
  if (attachmentsWrapper) {
    const attachments = issue.attachments || [];
    attachmentsWrapper.innerHTML = attachments
      .map(
        (att, idx) => `
        <button type="button" class="attachment-chip" data-attachment-index="${idx}">
          <i class="bxf ${ATTACHMENT_ICON[att.type] || "bx-file"}"></i> ${att.name}
        </button>`,
      )
      .join("");
    attachmentsWrapper.querySelectorAll("[data-attachment-index]").forEach((chip) => {
      chip.addEventListener("click", () => {
        openFilePreview(attachments[Number(chip.dataset.attachmentIndex)]);
      });
    });
  }

  // Action buttons inside the inline detail
  const holdBtn = document.getElementById("inlineDetailHoldBtn");
  if (holdBtn) {
    holdBtn.textContent = issue.status === "On Hold" ? "Lepas Hold" : "Hold Issue";
    holdBtn.onclick = () => toggleHold(issue.id, issue.status);
  }

  // If this issue has no assignee yet, show the "executor" combobox so
  // whoever actually did the work can be recorded when it's closed
  // (assign-at-close-time, so it's credited on the KPI Dashboard).
  const assigneeSelect = document.getElementById("inlineDetailAssigneeSelect");
  const closeBtn = document.getElementById("inlineDetailCloseBtn");

  if (assigneeSelect) {
    if (issue.assignee_id) {
      assigneeSelect.classList.add("is-hidden");
      assigneeSelect.innerHTML = "";
    } else {
      assigneeSelect.classList.remove("is-hidden");
      assigneeSelect.innerHTML = '<option value="">Memuat pelaksana...</option>';
      fetch(`/admin/users/api/assignable?category=${encodeURIComponent(issue.category)}&event=${encodeURIComponent(issue.event)}`)
        .then((r) => r.json())
        .then((data) => {
          const options = (data.users || [])
            .map((u) => `<option value="${u.id}">${u.username}</option>`)
            .join("");
          assigneeSelect.innerHTML = `<option value="">Tanpa pelaksana</option>${options}`;
        })
        .catch(() => {
          assigneeSelect.innerHTML = '<option value="">Gagal memuat</option>';
        });
    }
  }

  if (closeBtn) {
    closeBtn.onclick = async () => {
      const confirmed = await showConfirm(`Tandai issue "${issue.title}" sebagai Closed?`);
      if (!confirmed) return;

      const chosenAssignee = assigneeSelect && !assigneeSelect.classList.contains("is-hidden")
        ? assigneeSelect.value
        : null;
      updateIssueStatus(issue.id, "Closed", chosenAssignee || null);
    };
  }

  // Show the overlay
  panel.classList.remove("is-hidden");
}

function initInlineDetail() {
  const closeBtn = document.getElementById("inlineDetailClose");
  const panel = document.getElementById("issueInlineDetail");
  if (closeBtn && panel) {
    closeBtn.addEventListener("click", () => panel.classList.add("is-hidden"));
  }
  // Clicking the dark area outside the dialog (not the card) also
  // closes it, like a typical modal.
  if (panel) {
    panel.addEventListener("click", (e) => {
      if (e.target === panel) panel.classList.add("is-hidden");
    });
  }
  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape" && panel && !panel.classList.contains("is-hidden")) {
      panel.classList.add("is-hidden");
    }
  });
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
  const filterAssignee = document.getElementById("filterAssignee");

  [searchInput, filterPriority, filterStatus, filterCategory, filterEvent, filterAssignee]
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

  // ---- Row click / action buttons ----
  const tbody = document.getElementById("issueTableBody");
  if (tbody) {
    tbody.addEventListener("click", async (e) => {
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
        // Icon INFO -> open inline detail
        showInlineDetail(issue.id);
      } else if (action === "hand") {
        // Icon HAND -> quick close from the table. If there's no
        // assignee yet, redirect to the detail modal (it has a combobox
        // for picking the executor so it's credited on the KPI Dashboard).
        if (!issue.assignee_id) {
          showToast("Issue ini belum ada pelaksana -- tentukan pelaksana dulu di halaman detail.", "info");
          showInlineDetail(issue.id);
          return;
        }
        const confirmed = await showConfirm(`Tandai issue "${issue.title}" sebagai Closed?`);
        if (confirmed) {
          updateIssueStatus(issue.id, "Closed");
        }
      }
    });
  }

  // Init inline detail (close button) -- once is enough
  initInlineDetail();
}

// ============================================================
// ---- Priority Matrix panel -> Quarterly Gantt Chart ---- //
// ============================================================
// Current calendar quarter (Q1 Jan-Mar, Q2 Apr-Jun, etc) -- the Gantt
// X-axis always shows the quarter that contains today.
function currentQuarterRange() {
  const today = new Date();
  const quarterIndex = Math.floor(today.getMonth() / 3); // 0..3
  const start = new Date(today.getFullYear(), quarterIndex * 3, 1);
  const end = new Date(today.getFullYear(), quarterIndex * 3 + 3, 0); // hari terakhir quarter
  return { start, end, quarterIndex, year: today.getFullYear() };
}

function clampDate(date, min, max) {
  if (date < min) return min;
  if (date > max) return max;
  return date;
}

function datePercent(date, rangeStart, rangeEnd) {
  const total = rangeEnd - rangeStart;
  if (total <= 0) return 0;
  return Math.min(100, Math.max(0, ((date - rangeStart) / total) * 100));
}

function ganttBarMeta(issue, rangeStart, rangeEnd) {
  const today = new Date();
  today.setHours(0, 0, 0, 0);

  const created = issue.created_at ? parseDeadline(issue.created_at) : rangeStart;
  const deadline = parseDeadline(issue.deadline);
  const isOverdue = deadline < today && issue.status !== "Closed";

  // Overdue -> the bar's end keeps stretching to today (instead of
  // stopping at the deadline), and its color is forced to red.
  const barEndDate = isOverdue ? today : deadline;

  const barStart = clampDate(created, rangeStart, rangeEnd);
  const barEnd = clampDate(barEndDate, rangeStart, rangeEnd);

  const left = datePercent(barStart, rangeStart, rangeEnd);
  const right = datePercent(barEnd, rangeStart, rangeEnd);
  const width = Math.max(1.2, right - left); // biar batang 1-hari tetap kelihatan

  const daysLeft = daysUntil(issue.deadline);
  let color = "#3ddc97"; // longgar
  if (isOverdue) color = "#e24b4a";
  else if (daysLeft <= 7) color = "#f2a623";

  return { left, width, color, isOverdue, daysLeft, todayPercent: datePercent(today, rangeStart, rangeEnd) };
}

function renderGanttHeader(rangeStart, rangeEnd) {
  const header = document.getElementById("ganttHeader");
  const label = document.getElementById("ganttQuarterLabel");
  if (!header) return;

  const { quarterIndex, year } = currentQuarterRange();
  if (label) label.textContent = `Q${quarterIndex + 1} ${year} (${rangeStart.toLocaleDateString("id-ID", { day: "2-digit", month: "short" })} - ${rangeEnd.toLocaleDateString("id-ID", { day: "2-digit", month: "short" })})`;

  // One tick per week so the header doesn't get too crowded.
  const ticks = [];
  const cursor = new Date(rangeStart);
  while (cursor <= rangeEnd) {
    ticks.push(new Date(cursor));
    cursor.setDate(cursor.getDate() + 7);
  }

  header.innerHTML = ticks
    .map((tick) => {
      const pct = datePercent(tick, rangeStart, rangeEnd);
      const label = tick.toLocaleDateString("id-ID", { day: "2-digit", month: "short" });
      return `<span class="gantt__tick" style="left:${pct}%">${label}</span>`;
    })
    .join("");
}

function renderPriorityMatrix() {
  const { start: rangeStart, end: rangeEnd } = currentQuarterRange();
  renderGanttHeader(rangeStart, rangeEnd);

  const body = document.getElementById("ganttBody");
  const emptyState = document.getElementById("ganttEmpty");
  if (!body) return;

  const activeIssues = issueData.filter((issue) => issue.status !== "Closed");

  if (activeIssues.length === 0) {
    body.innerHTML = "";
    if (emptyState) emptyState.classList.remove("is-hidden");
    return;
  }
  if (emptyState) emptyState.classList.add("is-hidden");

  // Overdue rows first (most overdue on top), then the rest sorted by
  // nearest deadline.
  const rows = activeIssues
    .map((issue) => ({ issue, meta: ganttBarMeta(issue, rangeStart, rangeEnd) }))
    .sort((a, b) => {
      if (a.meta.isOverdue !== b.meta.isOverdue) return a.meta.isOverdue ? -1 : 1;
      if (a.meta.isOverdue) return a.meta.daysLeft - b.meta.daysLeft; // most overdue first
      return a.meta.daysLeft - b.meta.daysLeft; // nearest deadline first
    });

  const todayPercent = rows[0].meta.todayPercent;

  body.innerHTML = rows
    .map(({ issue, meta }) => `
      <div class="gantt__row ${meta.isOverdue ? "gantt__row--overdue" : ""}" data-issue-id="${issue.id}">
        <div class="gantt__row-label">
          <span class="badge ${PRIORITY_CLASS[issue.priority] || ""}">${issue.priority}</span>
          <span class="gantt__row-title" title="${issue.title}">${issue.title}</span>
        </div>
        <div class="gantt__track">
          <span class="gantt__today-line" style="left:${todayPercent}%"></span>
          <div class="gantt__bar" style="left:${meta.left}%; width:${meta.width}%; background:${meta.color};" title="${issue.title} — ${meta.isOverdue ? `lewat ${Math.abs(meta.daysLeft)} hari` : `${meta.daysLeft} hari lagi`}">
            ${meta.isOverdue ? '<i class="bxf bx-error"></i>' : ""}
          </div>
        </div>
      </div>
    `)
    .join("");

  // Clicking a Gantt row -> switch to List Issue tab and open the detail overlay
  body.querySelectorAll(".gantt__row").forEach((row) => {
    row.addEventListener("click", () => {
      document.querySelector('.nav-item__left[data-tab="list-issue"]')?.click();
      setTimeout(() => showInlineDetail(row.dataset.issueId), 60);
    });
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

document.addEventListener("DOMContentLoaded", async () => {
  initIssueRegister();
  initListIssue();
  await fetchIssues();
  renderAll();
});