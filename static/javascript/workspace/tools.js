const TOOLS_API = "/workspace/tools/api/items";

const KIND_ICON = { Tool: "bx-cog", Material: "bx-package" };

let toolItems = [];
let toolCategories = [];
let toolView = "card";

const el = (id) => document.getElementById(id);

// escapeHtml() comes from shared/notify.js (also escapes quotes for attributes).

async function loadItems() {
  try {
    const res = await fetch(TOOLS_API);
    const data = await res.json();
    toolItems = data.items || [];
    toolCategories = data.categories || [];
  } catch (err) {
    console.error(err);
    showToast("Failed to load tools.", "error");
  }
  populateCategories();
  render();
}

function populateCategories() {
  const filter = el("toolCategoryFilter");
  const previous = filter.value;
  filter.innerHTML =
    '<option value="All">All Categories</option>' +
    toolCategories.map((c) => `<option value="${escapeHtml(c)}">${escapeHtml(c)}</option>`).join("");
  filter.value = toolCategories.includes(previous) ? previous : "All";

  el("toolCategoryOptions").innerHTML = toolCategories
    .map((c) => `<option value="${escapeHtml(c)}"></option>`)
    .join("");
}

function filteredItems() {
  const search = el("toolSearch").value.trim().toLowerCase();
  const kind = el("toolKindFilter").value;
  const category = el("toolCategoryFilter").value;

  return toolItems.filter((item) => {
    const haystack = `${item.name} ${item.category} ${item.description || ""}`.toLowerCase();
    return (
      (!search || haystack.includes(search)) &&
      (kind === "All" || item.kind === kind) &&
      (category === "All" || item.category === category)
    );
  });
}

function deleteButton(item) {
  return item.can_delete
    ? `<button type="button" class="tool-delete" data-delete-id="${item.id}" title="Delete"><i class="bxf bx-trash"></i></button>`
    : "";
}

function renderCards(items) {
  const container = el("toolCardContainer");
  container.innerHTML = items
    .map(
      (item) => `
    <div class="tool-card">
      <a class="tool-card__link" href="${escapeHtml(item.url)}" target="_blank" rel="noopener noreferrer">
        <span class="tool-card__icon"><i class="bxf ${KIND_ICON[item.kind] || "bx-link"}"></i></span>
        <div class="tool-card__body">
          <span class="tool-card__name">${escapeHtml(item.name)}</span>
          <span class="tool-card__meta">${escapeHtml(item.kind)} &middot; ${escapeHtml(item.category)}</span>
          ${item.description ? `<span class="tool-card__desc">${escapeHtml(item.description)}</span>` : ""}
        </div>
        <i class="bxf bx-link-alt tool-card__go"></i>
      </a>
      ${deleteButton(item)}
    </div>`,
    )
    .join("");
}

function renderList(items) {
  const container = el("toolListContainer");
  container.innerHTML = items
    .map(
      (item) => `
    <div class="tool-list-item">
      <a class="tool-list-item__link" href="${escapeHtml(item.url)}" target="_blank" rel="noopener noreferrer">
        <span class="tool-list-item__icon"><i class="bxf ${KIND_ICON[item.kind] || "bx-link"}"></i></span>
        <span class="tool-list-item__name">${escapeHtml(item.name)}</span>
        <span class="tool-list-item__type">${escapeHtml(item.kind)}</span>
        <span class="tool-list-item__category">${escapeHtml(item.category)}</span>
        <i class="bxf bx-link-alt tool-list-item__go"></i>
      </a>
      ${deleteButton(item)}
    </div>`,
    )
    .join("");
}

function render() {
  const items = filteredItems();
  el("toolCount").textContent = `(${items.length})`;

  const emptyMarkup = '<div class="empty-state">No tools or material match the current filter.</div>';
  if (items.length === 0) {
    el("toolCardContainer").innerHTML = emptyMarkup;
    el("toolListContainer").innerHTML = emptyMarkup;
    return;
  }
  renderCards(items);
  renderList(items);
}

function setView(view) {
  toolView = view;
  el("toolCardView").style.display = view === "card" ? "" : "none";
  el("toolListView").style.display = view === "list" ? "" : "none";
  document.querySelector("#toolViewSwitcher i").className =
    view === "card" ? "bxf bx-list-ul" : "bxf bx-grid";
}

function openModal() {
  el("toolModal").classList.remove("is-hidden");
  el("toolFormName").focus();
}

function closeModal() {
  el("toolModal").classList.add("is-hidden");
  el("toolForm").reset();
}

async function submitForm(e) {
  e.preventDefault();
  const submitBtn = el("toolFormSubmit");
  submitBtn.disabled = true;

  try {
    const res = await fetch(TOOLS_API, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        kind: el("toolFormKind").value,
        name: el("toolFormName").value,
        category: el("toolFormCategory").value,
        url: el("toolFormUrl").value,
        description: el("toolFormDescription").value,
      }),
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.message || "Failed to save.");

    closeModal();
    showToast(data.message, "success");
    await loadItems();
  } catch (err) {
    showToast(err.message, "error");
  } finally {
    submitBtn.disabled = false;
  }
}

async function handleDelete(id) {
  const confirmed = await showConfirm("Delete this entry?");
  if (!confirmed) return;

  try {
    const res = await fetch(`${TOOLS_API}/${id}`, { method: "DELETE" });
    const data = await res.json();
    if (!res.ok) throw new Error(data.message || "Failed to delete.");
    showToast(data.message, "success");
    await loadItems();
  } catch (err) {
    showToast(err.message, "error");
  }
}

document.addEventListener("DOMContentLoaded", () => {
  ["toolSearch"].forEach((id) => el(id).addEventListener("input", render));
  ["toolKindFilter", "toolCategoryFilter"].forEach((id) =>
    el(id).addEventListener("change", render),
  );

  el("toolReset").addEventListener("click", () => {
    el("toolSearch").value = "";
    el("toolKindFilter").value = "All";
    el("toolCategoryFilter").value = "All";
    render();
  });

  el("toolViewSwitcher").addEventListener("click", () =>
    setView(toolView === "card" ? "list" : "card"),
  );

  el("toolAddBtn").addEventListener("click", openModal);
  el("toolModalClose").addEventListener("click", closeModal);
  el("toolModal").addEventListener("click", (e) => {
    if (e.target === el("toolModal")) closeModal();
  });
  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape" && !el("toolModal").classList.contains("is-hidden")) closeModal();
  });
  el("toolForm").addEventListener("submit", submitForm);

  document.querySelector(".main-body-content").addEventListener("click", (e) => {
    const btn = e.target.closest("[data-delete-id]");
    if (btn) handleDelete(btn.dataset.deleteId);
  });

  setView("card");
  loadItems();
});
