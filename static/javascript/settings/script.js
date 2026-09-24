// Konsisten dengan halaman lain: pakai window.showToast() (lihat
// static/javascript/shared/notify.js), bukan alert() bawaan browser.

const profileForm = document.getElementById("profileForm");
if (profileForm) {
  profileForm.addEventListener("submit", async (e) => {
    e.preventDefault();
    const formData = new FormData(profileForm);

    const res = await fetch("/settings/profile", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        email: formData.get("email"),
        job_title: formData.get("job_title"),
      }),
    });
    const data = await res.json();

    if (!res.ok) {
      showToast(data.error || "Gagal menyimpan profil.", "error");
      return;
    }
    showToast(data.message, "success");
  });
}

const passwordForm = document.getElementById("passwordForm");
if (passwordForm) {
  passwordForm.addEventListener("submit", async (e) => {
    e.preventDefault();
    const formData = new FormData(passwordForm);

    const res = await fetch("/settings/password", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        current_password: formData.get("current_password"),
        new_password: formData.get("new_password"),
        confirm_password: formData.get("confirm_password"),
      }),
    });
    const data = await res.json();

    if (!res.ok) {
      showToast(data.error || "Gagal mengubah password.", "error");
      return;
    }
    showToast(data.message, "success");
    passwordForm.reset();
  });
}
