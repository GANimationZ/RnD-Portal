// ---- Navbar for Panel switching ---- //
const navBar = document.querySelector(".nav__bar");
const panels = document.querySelectorAll(".main-body-content .body");

navBar.addEventListener("click", (e) => {
  const item = e.target.closest(".flex-1");
  if (!item) return;

  navBar
    .querySelectorAll(".flex-1")
    .forEach((el) => el.classList.remove("active"));
  item.classList.add("active");

  const target = item.dataset.tab;
  let matched = false;

  panels.forEach((panel) => {
    const isMatch = panel.dataset.panel === target;
    panel.classList.toggle("active", isMatch);
    if (isMatch) matched = true;
  });

  if (!matched) {
    console.warn(`Belum ada panel untuk tab "${target}"`);
  }
});

// ---- Panel Dashboard ---- //
// Area fungsi untuk panel dashboard

// ---- Matrix Table Chart ---- //
Chart.register(ChartDataLabels);

// ---- Define Data ---- (Dummy Data) //
// Categories //
const categoryData = [
  { label: "PCBA/SMT", value: 1, color: "#b32e2e" },
  { label: "SQA", value: 4, color: "#dd3d3d" },
  { label: "Line-Prod", value: 2, color: "#f18f34" },
  { label: "OQA", value: 5, color: "#2e92cc" },
  { label: "CSS/SVC", value: 0, color: "#2e92cc" },
];

// Event //
const eventData = [
  { label: "PV", value: 3, color: "#143820" },
  { label: "Pre-MP", value: 2, color: "#e24b4a" },
  { label: "MP", value: 7, color: "#2c7db3" },
  { label: "Field", value: 0, color: "#e24b4a" },
];

// Status //
const statusData = [
  { label: "Open", value: 3, color: "#143820" },
  { label: "HOLD", value: 2, color: "#e24b4a" },
  { label: "Open - MR in progress", value: 7, color: "#2c7db3" },
  { label: "HOLD by SQA", value: 0, color: "#e24b4a" },
  { label: "CLOSED - Temporary ECO issued", value: 0, color: "#1e7e33" },
  { label: "Open - analysis requested", value: 0, color: "#215227" },
];

// Matrix (Issue x Event) //
const events = ["PV", "PRE-MP", "MP", "FIELD"];
const matrixData = [
  [1, 0, 0, 0],
  [2, 1, 1, 0],
  [0, 1, 1, 0],
  [0, 0, 5, 0],
  [0, 0, 0, 0],
];

// ---- Define Mapping and Colors ---- //
// Categories //
const categories = categoryData.map((d) => d.label);
const categoryColors = Object.fromEntries(
  categoryData.map((d) => [d.label, d.color]),
);

// Event //
const event = eventData.map((e) => e.label);
const eventColors = Object.fromEntries(
  eventData.map((e) => [e.label, e.color]),
);

// Status //
const status = statusData.map((s) => s.label);
const statusColors = Object.fromEntries(
  statusData.map((s) => [s.label, s.color]),
);

// Matrix (Issue x Event) //
const maxValue = Math.max(...categoryData.map((d) => d.value));

function getHeatColor(value, max) {
  const intensity = max === 0 ? 0 : value / max;
  const lightness = 95 - intensity * 55;
  return `hsl(341, 100%, ${lightness}%)`;
}

// ---- Fucntion Render Chart ---- //
// Categories //
const ctc = document.getElementById("category");
new Chart(ctc, {
  type: "bar",
  data: {
    labels: categoryData.map((d) => d.label),
    datasets: [
      {
        label: "Jumlah Issue",
        data: categoryData.map((d) => d.value),
        backgroundColor: categoryData.map((d) => d.color),
        borderRadius: 4,
        categoryPercentage: 1.0,
        barPercentage: 0.9,
      },
    ],
  },
  options: {
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
      x: {
        beginAtZero: true,
        max: maxValue,
        grid: { display: true },
        ticks: { display: false },
      },
      y: {
        grid: { display: false },
        ticks: { crossAlign: "far", padding: 0 },
      },
    },
  },
});

// Event //
const cte = document.getElementById("event");
new Chart(cte, {
  type: "bar",
  data: {
    labels: eventData.map((e) => e.label),
    datasets: [
      {
        label: "Jumlah Issue",
        data: eventData.map((e) => e.value),
        backgroundColor: eventData.map((e) => e.color),
        borderRadius: 4,
        categoryPercentage: 1.0,
        barPercentage: 0.9,
      },
    ],
  },
  options: {
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
      x: {
        beginAtZero: true,
        max: maxValue,
        grid: { display: true },
        ticks: { display: false },
      },
      y: {
        grid: { display: false },
        ticks: { crossAlign: "far", padding: 0 },
      },
    },
  },
});

// Status //
const cts = document.getElementById("status");
new Chart(cts, {
  type: "bar",
  data: {
    labels: statusData.map((s) => s.label),
    datasets: [
      {
        label: "Jumlah Issue",
        data: statusData.map((s) => s.value),
        backgroundColor: eventData.map((s) => s.color),
        borderRadius: 4,
        categoryPercentage: 1.0,
        barPercentage: 0.9,
      },
    ],
  },
  options: {
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
      x: {
        beginAtZero: true,
        max: maxValue,
        grid: { display: true },
        ticks: { display: false },
      },
      y: {
        grid: { display: false },
        ticks: { crossAlign: "far", padding: 0 },
      },
    },
  },
});

// Matrix (Issue x Event) //
function renderMatrixTable() {
  const table = document.getElementById("matrixTable");
  const max = Math.max(...matrixData.flat());

  const theadRow = table.querySelector("thead tr");
  const cornerCell = theadRow.querySelector("th");
  cornerCell.textContent = "Category \\ Event";
  cornerCell.classList.add("corner-cell");

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
  const columnSums = new Array(events.length).fill(0);

  categories.forEach((cat, i) => {
    const row = document.createElement("tr");

    const rowHeader = document.createElement("th");
    rowHeader.classList.add("category-badge-cell");
    rowHeader.innerHTML = `<span class="category-badge" style="background:${categoryColors[cat]}22; color:${categoryColors[cat]}">${cat}</span>`;
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

renderMatrixTable();

// ---- Panel Issue Register ---- //
// Area fungsi untuk panel mendaftarkan issue

// DateTime Placeholder
flatpickr("#issueDate", {
  dateFormat: "Y-m-d",
  altInput: true,
  altFormat: "d/m/Y",
  allowInput: true,
});
