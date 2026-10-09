// Consistent with other pages: uses window.showToast() (see
// static/javascript/shared/notify.js) instead of the browser's alert().

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
      showToast(data.error || "Failed to save profile.", "error");
      return;
    }

    showToast(data.message, "success");

    // The display name follows the email, so it may have just changed --
    // refresh the avatar initials/name shown on this page without a
    // full reload.
    if (data.username) {
      const nameEl = document.querySelector(".settings-card__username");
      const avatarEl = document.querySelector(".settings-card__avatar");
      if (nameEl) nameEl.textContent = data.username;
      if (avatarEl) avatarEl.textContent = data.username.slice(0, 2).toUpperCase();
    }
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
      showToast(data.error || "Failed to change password.", "error");
      return;
    }
    showToast(data.message, "success");
    passwordForm.reset();
  });
}
