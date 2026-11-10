document.querySelectorAll(".btn-approve").forEach((btn) => {
  btn.addEventListener("click", async () => {
    const userId = btn.dataset.userId;
    const res = await fetch(`/admin/users/${userId}/approve`, { method: "POST" });
    const data = await res.json();
    if (!res.ok) return alert(data.error || "Gagal menyetujui user.");
    window.location.reload();
  });
});

document.querySelectorAll(".btn-delete").forEach((btn) => {
  btn.addEventListener("click", async () => {
    if (!confirm("Yakin hapus user ini? Tindakan ini tidak bisa dibatalkan.")) return;
    const userId = btn.dataset.userId;
    const res = await fetch(`/admin/users/${userId}`, { method: "DELETE" });
    const data = await res.json();
    if (!res.ok) return alert(data.error || "Gagal menghapus user.");
    window.location.reload();
  });
});

document.querySelectorAll(".admin-users__role-select").forEach((select) => {
  select.addEventListener("change", async () => {
    const userId = select.dataset.userId;
    const res = await fetch(`/admin/users/${userId}/role`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ role: select.value }),
    });
    const data = await res.json();
    if (!res.ok) return alert(data.error || "Gagal mengubah role.");
  });
});
