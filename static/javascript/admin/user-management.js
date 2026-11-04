// ============================================================
// RnD Portal - User Management (Super Admin only)
// ============================================================

const UM_API_BASE = "/admin/users/api";
// Best Practice notes reuse the KPI Dashboard blueprint's API.
const KPI_API_BASE = "/workspace/kpi-dashboard/api";

const ROLE_BADGE_CLASS = {
  "Super Admin": "badge-red",
  "Admin": "badge-blue",
  "Member": "badge-grey",
};

const STATUS_BADGE_CLASS = {
  Active: "badge-green",
  Pending: "badge-yellow",
  Inactive: "badge-grey",
};
const STATUS_LABEL_ID = {
  Active: "Active",
  Pending: "Pending Verification",
  Inactive: "Inactive",
};

let usersData = [];
let editingId = null;

// ------------------------------------------------------------
// FETCH
// ------------------------------------------------------------
async function fetchUsers() {
  try {
    const res = await fetch(`${UM_API_BASE}/users`);
    const data = await res.json();
    usersData = data.users || [];
    renderSummary();
    renderTable();
  } catch (err) {
    console.error(err);
    showToast("Failed to load the user list.", "error");
  }
}

// ------------------------------------------------------------
// RENDER: summary
// ------------------------------------------------------------
function renderSummary() {
  const setText = (id, val) => {
    const el = document.getElementById(id);
    if (el) el.textContent = val;
  };

  setText("umTotalUsers", usersData.length);
  setText("umTotalSuperAdmin", usersData.filter((u) => u.role === "Super Admin").length);
  setText("umTotalAdmin", usersData.filter((u) => u.role === "Admin").length);
  setText("umTotalMember", usersData.filter((u) => u.role === "Member").length);
  setText("umTotalPending", usersData.filter((u) => u.status_label === "Pending").length);
}

// ------------------------------------------------------------
// RENDER: table
// ------------------------------------------------------------
function scopeBadges(list, badgeClass) {
  if (!list || list.length === 0) {
    return `<span class="um-empty-scope">-</span>`;
  }
  return list.map((v) => `<span class="badge ${badgeClass}">${escapeHtml(v)}</span>`).join("");
}

function renderTable() {
  const tbody = document.getElementById("userTableBody");
  if (!tbody) return;
  tbody.innerHTML = "";

  usersData.forEach((user, i) => {
    const row = document.createElement("tr");
    row.innerHTML = `
      <td>${i + 1}</td>
      <td>${escapeHtml(user.username)}</td>
      <td>${escapeHtml(user.email)}</td>
      <td><span class="badge ${ROLE_BADGE_CLASS[user.role] || "badge-grey"}">${escapeHtml(user.role)}</span></td>
      <td><div class="um-scope-cell">${scopeBadges(user.categories, "badge-blue")}</div></td>
      <td><div class="um-scope-cell">${scopeBadges(user.events, "badge-green")}</div></td>
      <td><span class="badge ${STATUS_BADGE_CLASS[user.status_label] || "badge-grey"}">${escapeHtml(STATUS_LABEL_ID[user.status_label] || user.status_label)}</span></td>
      <td class="center">
        <div class="um-action-buttons">
          <button type="button" data-action="edit" data-id="${user.id}" title="Edit"><i class="bxf bx-edit"></i></button>
          <button type="button" data-action="toggle" data-id="${user.id}" title="${user.is_active ? "Deactivate" : "Activate"}">
            <i class="bxf ${user.is_active ? "bx-toggle-right" : "bx-toggle-left"}"></i>
          </button>
          <button type="button" class="um-danger" data-action="delete" data-id="${user.id}" title="Delete"><i class="bxf bx-trash"></i></button>
        </div>
      </td>
    `;
    tbody.appendChild(row);
  });
}

// ------------------------------------------------------------
// FORM: reset / prefill helpers (edit mode)
// ------------------------------------------------------------
function resetForm() {
  editingId = null;
  document.getElementById("umEditingId").value = "";
  document.getElementById("userForm").reset();

  document.getElementById("umPassword").required = true;
  document.getElementById("umPasswordHint").textContent =
    "Required for a new user. When editing, leave blank to keep the current password.";

  document.getElementById("umFormTitle").textContent = "Add New User";
  document.getElementById("umSubmitBtn").value = "Save User";

  hideBestPracticeSection();
}

function fillFormForEdit(user) {
  editingId = user.id;
  document.getElementById("umEditingId").value = user.id;

  document.getElementById("umEmail").value = user.email;
  document.getElementById("umPassword").value = "";
  document.getElementById("umPassword").required = false;
  document.getElementById("umPasswordHint").textContent =
    "Leave blank to keep this user's current password.";

  document.getElementById("umRole").value = user.role;

  document.querySelectorAll('input[name="umCategory"]').forEach((cb) => {
    cb.checked = user.categories.includes(cb.value);
  });
  document.querySelectorAll('input[name="umEvent"]').forEach((cb) => {
    cb.checked = user.events.includes(cb.value);
  });

  document.getElementById("umFormTitle").textContent = `Edit User: ${user.username}`;
  document.getElementById("umSubmitBtn").value = "Update User";

  // Notes are Member-only, and only once the user exists (edit mode).
  if (user.role === "Member") {
    showBestPracticeSection(user.id);
  } else {
    hideBestPracticeSection();
  }

  openUserModal();
}

// ------------------------------------------------------------
// POPUP: open / close
// ------------------------------------------------------------
function openUserModal() {
  document.getElementById("userModal")?.classList.remove("is-hidden");
}

function closeUserModal() {
  document.getElementById("userModal")?.classList.add("is-hidden");
}

// ------------------------------------------------------------
// BEST PRACTICE NOTES (edit mode, Member only)
// ------------------------------------------------------------
function hideBestPracticeSection() {
  document.getElementById("umBestPracticeSection")?.classList.add("is-hidden");
  const list = document.getElementById("umNotesList");
  if (list) list.innerHTML = "";
  const input = document.getElementById("umNewNote");
  if (input) input.value = "";
}

async function showBestPracticeSection(memberId) {
  const section = document.getElementById("umBestPracticeSection");
  if (section) section.classList.remove("is-hidden");
  await fetchAndRenderNotes(memberId);
}

function renderNotesList(notes) {
  const list = document.getElementById("umNotesList");
  if (!list) return;

  if (notes.length === 0) {
    list.innerHTML = `<li class="um-notes-empty">No notes yet.</li>`;
    return;
  }

  list.innerHTML = notes
    .map(
      (n) => `
    <li data-note-id="${n.id}">
      <span>${escapeHtml(n.note)}</span>
      <button type="button" class="um-notes-delete" data-note-id="${n.id}" title="Delete note">
        <i class="bxf bx-trash"></i>
      </button>
    </li>`
    )
    .join("");
}

async function fetchAndRenderNotes(memberId) {
  const list = document.getElementById("umNotesList");
  if (list) list.innerHTML = `<li class="um-notes-empty">Loading...</li>`;
  try {
    const res = await fetch(`${KPI_API_BASE}/employees/${memberId}/best-practices`);
    const data = await res.json();
    if (!res.ok) {
      showToast(data.message || "Failed to load notes.", "error");
      return;
    }
    renderNotesList(data.notes || []);
  } catch (err) {
    console.error(err);
    showToast("An error occurred while loading the notes.", "error");
  }
}

function initBestPracticeSection() {
  const addBtn = document.getElementById("umAddNoteBtn");
  const input = document.getElementById("umNewNote");
  const list = document.getElementById("umNotesList");
  if (!addBtn || !input || !list) return;

  addBtn.addEventListener("click", async () => {
    const note = input.value.trim();
    if (!note) {
      showToast("Note cannot be empty.", "error");
      return;
    }
    if (!editingId) return; // section is hidden in create mode, but guard anyway

    addBtn.disabled = true;
    try {
      const res = await fetch(`${KPI_API_BASE}/employees/${editingId}/best-practices`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ note }),
      });
      const data = await res.json();
      if (!res.ok) {
        showToast(data.message || "Failed to add note.", "error");
        return;
      }
      input.value = "";
      await fetchAndRenderNotes(editingId);
      showToast(data.message || "Note added.", "success");
    } catch (err) {
      console.error(err);
      showToast("An error occurred while contacting the server.", "error");
    } finally {
      addBtn.disabled = false;
    }
  });

  input.addEventListener("keydown", (e) => {
    if (e.key === "Enter") {
      e.preventDefault();
      addBtn.click();
    }
  });

  list.addEventListener("click", async (e) => {
    const btn = e.target.closest(".um-notes-delete");
    if (!btn || !editingId) return;
    const noteId = Number(btn.dataset.noteId);

    const confirmed = await showConfirm("Delete this note? This action cannot be undone.");
    if (!confirmed) return;

    try {
      const res = await fetch(`${KPI_API_BASE}/employees/${editingId}/best-practices/${noteId}`, {
        method: "DELETE",
      });
      const data = await res.json();
      if (!res.ok) {
        showToast(data.message || "Failed to delete note.", "error");
        return;
      }
      await fetchAndRenderNotes(editingId);
      showToast(data.message || "Note deleted.", "success");
    } catch (err) {
      console.error(err);
      showToast("An error occurred while contacting the server.", "error");
    }
  });

  // Hide the section immediately if the role dropdown changes away from Member.
  document.getElementById("umRole")?.addEventListener("change", (e) => {
    if (!editingId) return;
    if (e.target.value === "Member") {
      showBestPracticeSection(editingId);
    } else {
      hideBestPracticeSection();
    }
  });
}

// ------------------------------------------------------------
// EVENTS: table (edit / toggle active / delete)
// ------------------------------------------------------------
function initTableActions() {
  const tbody = document.getElementById("userTableBody");
  if (!tbody) return;

  tbody.addEventListener("click", async (e) => {
    const btn = e.target.closest("button[data-action]");
    if (!btn) return;

    const id = Number(btn.dataset.id);
    const user = usersData.find((u) => u.id === id);
    if (!user) return;

    if (btn.dataset.action === "edit") {
      fillFormForEdit(user);
      return;
    }

    if (btn.dataset.action === "toggle") {
      try {
        const res = await fetch(`${UM_API_BASE}/users/${id}`, {
          method: "PATCH",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ is_active: !user.is_active }),
        });
        const data = await res.json();
        if (!res.ok) {
          showToast(data.message || "Failed to update user status.", "error");
          return;
        }
        await fetchUsers();
      } catch (err) {
        console.error(err);
        showToast("An error occurred while contacting the server.", "error");
      }
      return;
    }

    if (btn.dataset.action === "delete") {
      const confirmed = await showConfirm(`Delete user "${user.username}"? This action cannot be undone.`);
      if (!confirmed) return;
      try {
        const res = await fetch(`${UM_API_BASE}/users/${id}`, { method: "DELETE" });
        const data = await res.json();
        if (!res.ok) {
          showToast(data.message || "Failed to delete user.", "error");
          return;
        }
        await fetchUsers();
        showToast(data.message || "User deleted successfully.", "success");
      } catch (err) {
        console.error(err);
        showToast("An error occurred while contacting the server.", "error");
      }
    }
  });
}

// ------------------------------------------------------------
// EVENTS: add/edit form
// ------------------------------------------------------------
function initForm() {
  const form = document.getElementById("userForm");
  if (!form) return;

  document.getElementById("umAddBtn")?.addEventListener("click", () => {
    resetForm();
    openUserModal();
    document.getElementById("umEmail")?.focus();
  });

  const closeAndReset = () => {
    closeUserModal();
    resetForm();
  };
  document.getElementById("umCancelEdit")?.addEventListener("click", closeAndReset);
  document.getElementById("umModalClose")?.addEventListener("click", closeAndReset);
  document.getElementById("userModal")?.addEventListener("click", (e) => {
    if (e.target.id === "userModal") closeAndReset();
  });
  document.addEventListener("keydown", (e) => {
    const modal = document.getElementById("userModal");
    if (e.key === "Escape" && modal && !modal.classList.contains("is-hidden")) closeAndReset();
  });

  form.addEventListener("submit", async (e) => {
    e.preventDefault();

    const email = document.getElementById("umEmail").value.trim();
    const password = document.getElementById("umPassword").value;
    const role = document.getElementById("umRole").value;
    const categories = Array.from(
      document.querySelectorAll('input[name="umCategory"]:checked')
    ).map((cb) => cb.value);
    const events = Array.from(
      document.querySelectorAll('input[name="umEvent"]:checked')
    ).map((cb) => cb.value);

    const submitBtn = document.getElementById("umSubmitBtn");
    const originalValue = submitBtn.value;
    submitBtn.disabled = true;
    submitBtn.value = "Saving...";

    try {
      let res, data;

      if (editingId) {
        const payload = { email, role, categories, events };
        if (password) payload.password = password;

        res = await fetch(`${UM_API_BASE}/users/${editingId}`, {
          method: "PATCH",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(payload),
        });
      } else {
        res = await fetch(`${UM_API_BASE}/users`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ email, password, role, categories, events }),
        });
      }

      data = await res.json();

      if (!res.ok) {
        showToast(data.message || "Failed to save user.", "error");
        return;
      }

      resetForm();
      closeUserModal();
      await fetchUsers();
      showToast(data.message || "User saved successfully.", "success");
    } catch (err) {
      console.error(err);
      showToast("An error occurred while contacting the server.", "error");
    } finally {
      submitBtn.disabled = false;
      submitBtn.value = originalValue;
    }
  });
}

// ------------------------------------------------------------
// INIT
// ------------------------------------------------------------
document.addEventListener("DOMContentLoaded", () => {
  if (!document.getElementById("userForm")) return; // not this page

  initTableActions();
  initForm();
  initBestPracticeSection();
  fetchUsers();
});
