// ============================================================
// RnD Portal - User Management (Super Admin only)
// Tab switching (.nav-item__left clicks) is handled by panel-switcher.js,
// loaded globally via the layout -- this file only handles data.
// ============================================================

const UM_API_BASE = "/admin/users/api";

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
  Active: "Aktif",
  Pending: "Menunggu Verifikasi",
  Inactive: "Nonaktif",
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
    showToast("Gagal memuat daftar user.", "error");
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
  return list.map((v) => `<span class="badge ${badgeClass}">${v}</span>`).join("");
}

function renderTable() {
  const tbody = document.getElementById("userTableBody");
  if (!tbody) return;
  tbody.innerHTML = "";

  usersData.forEach((user, i) => {
    const row = document.createElement("tr");
    row.innerHTML = `
      <td>${i + 1}</td>
      <td>${user.username}</td>
      <td>${user.email}</td>
      <td><span class="badge ${ROLE_BADGE_CLASS[user.role] || "badge-grey"}">${user.role}</span></td>
      <td><div class="um-scope-cell">${scopeBadges(user.categories, "badge-blue")}</div></td>
      <td><div class="um-scope-cell">${scopeBadges(user.events, "badge-green")}</div></td>
      <td><span class="badge ${STATUS_BADGE_CLASS[user.status_label] || "badge-grey"}">${STATUS_LABEL_ID[user.status_label] || user.status_label}</span></td>
      <td class="center">
        <div class="um-action-buttons">
          <button type="button" data-action="edit" data-id="${user.id}" title="Edit"><i class="bxf bx-edit"></i></button>
          <button type="button" data-action="toggle" data-id="${user.id}" title="${user.is_active ? "Nonaktifkan" : "Aktifkan"}">
            <i class="bxf ${user.is_active ? "bx-toggle-right" : "bx-toggle-left"}"></i>
          </button>
          <button type="button" class="um-danger" data-action="delete" data-id="${user.id}" title="Hapus"><i class="bxf bx-trash"></i></button>
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

  const usernameEl = document.getElementById("umUsername");
  usernameEl.disabled = false;

  document.getElementById("umPassword").required = true;
  document.getElementById("umPasswordHint").textContent =
    "Wajib diisi untuk user baru. Saat mengedit, kosongkan kalau tidak ingin mengganti password.";

  document.getElementById("umFormTitle").textContent = "Tambah User Baru";
  document.getElementById("umSubmitBtn").value = "Simpan User";
  document.getElementById("umCancelEdit").classList.add("is-hidden");
  document.getElementById("formTabLabel").innerHTML = `<i class="bxf bx-plus"></i> Tambah User`;
}

function fillFormForEdit(user) {
  editingId = user.id;
  document.getElementById("umEditingId").value = user.id;

  const usernameEl = document.getElementById("umUsername");
  usernameEl.value = user.username;
  usernameEl.disabled = true; // username can't be changed here

  document.getElementById("umEmail").value = user.email;
  document.getElementById("umPassword").value = "";
  document.getElementById("umPassword").required = false;
  document.getElementById("umPasswordHint").textContent =
    "Kosongkan kalau tidak ingin mengganti password user ini.";

  document.getElementById("umRole").value = user.role;

  document.querySelectorAll('input[name="umCategory"]').forEach((cb) => {
    cb.checked = user.categories.includes(cb.value);
  });
  document.querySelectorAll('input[name="umEvent"]').forEach((cb) => {
    cb.checked = user.events.includes(cb.value);
  });

  document.getElementById("umFormTitle").textContent = `Edit User: ${user.username}`;
  document.getElementById("umSubmitBtn").value = "Update User";
  document.getElementById("umCancelEdit").classList.remove("is-hidden");
  document.getElementById("formTabLabel").innerHTML = `<i class="bxf bx-edit"></i> Edit User`;

  document.querySelector('.nav-item__left[data-tab="user-form"]')?.click();
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
          showToast(data.message || "Gagal mengubah status user.", "error");
          return;
        }
        await fetchUsers();
      } catch (err) {
        console.error(err);
        showToast("Terjadi kesalahan saat menghubungi server.", "error");
      }
      return;
    }

    if (btn.dataset.action === "delete") {
      const confirmed = await showConfirm(`Hapus user "${user.username}"? Tindakan ini tidak bisa dibatalkan.`);
      if (!confirmed) return;
      try {
        const res = await fetch(`${UM_API_BASE}/users/${id}`, { method: "DELETE" });
        const data = await res.json();
        if (!res.ok) {
          showToast(data.message || "Gagal menghapus user.", "error");
          return;
        }
        await fetchUsers();
        showToast(data.message || "User berhasil dihapus.", "success");
      } catch (err) {
        console.error(err);
        showToast("Terjadi kesalahan saat menghubungi server.", "error");
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

  document.getElementById("umCancelEdit").addEventListener("click", () => {
    resetForm();
    document.querySelector('.nav-item__left[data-tab="user-list"]')?.click();
  });

  form.addEventListener("submit", async (e) => {
    e.preventDefault();

    const username = document.getElementById("umUsername").value.trim();
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
    submitBtn.value = "Menyimpan...";

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
          body: JSON.stringify({ username, email, password, role, categories, events }),
        });
      }

      data = await res.json();

      if (!res.ok) {
        showToast(data.message || "Gagal menyimpan user.", "error");
        return;
      }

      resetForm();
      await fetchUsers();
      document.querySelector('.nav-item__left[data-tab="user-list"]')?.click();
      showToast(data.message || "User berhasil disimpan.", "success");
    } catch (err) {
      console.error(err);
      showToast("Terjadi kesalahan saat menghubungi server.", "error");
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
  fetchUsers();
});
