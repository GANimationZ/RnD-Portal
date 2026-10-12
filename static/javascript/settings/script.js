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

    if (data.username) {
      const nameEl = document.querySelector(".settings-card__username");
      const avatarEl = document.querySelector(".settings-card__avatar");
      if (nameEl) nameEl.textContent = data.username;
      // Only swap initials when no photo is set (a photo must stay put).
      if (avatarEl && !avatarEl.querySelector("img")) {
        avatarEl.textContent = data.username.slice(0, 2).toUpperCase();
      }
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

// ---- Profile picture: change / remove ----
const pictureInput = document.getElementById("pictureInput");
const pictureChangeBtn = document.getElementById("pictureChangeBtn");
const pictureRemoveBtn = document.getElementById("pictureRemoveBtn");

function applyAvatar(url) {
  const initials = (document.querySelector(".settings-card__username")?.textContent || "?")
    .slice(0, 2)
    .toUpperCase();
  const markup = url ? `<img src="${url}" alt="" />` : initials;

  const settingsAvatar = document.getElementById("settingsAvatar");
  if (settingsAvatar) settingsAvatar.innerHTML = markup;

  const sidebarAvatar = document.querySelector(".profile__avatar");
  if (sidebarAvatar) sidebarAvatar.innerHTML = markup;

  if (pictureRemoveBtn) pictureRemoveBtn.classList.toggle("is-hidden", !url);
}

if (pictureChangeBtn && pictureInput) {
  pictureChangeBtn.addEventListener("click", () => pictureInput.click());

  pictureInput.addEventListener("change", async () => {
    const file = pictureInput.files[0];
    if (!file) return;

    const formData = new FormData();
    formData.append("picture", file);

    try {
      const res = await fetch("/settings/profile-picture", { method: "POST", body: formData });
      const data = await res.json();
      if (!res.ok) {
        showToast(data.error || "Failed to upload the picture.", "error");
        return;
      }
      applyAvatar(`${data.picture_url}?t=${Date.now()}`);
      showToast(data.message, "success");
    } catch (err) {
      console.error(err);
      showToast("Unable to reach the server.", "error");
    } finally {
      pictureInput.value = "";
    }
  });
}

if (pictureRemoveBtn) {
  pictureRemoveBtn.addEventListener("click", async () => {
    const confirmed = await showConfirm("Remove your profile picture?");
    if (!confirmed) return;

    try {
      const res = await fetch("/settings/profile-picture", { method: "DELETE" });
      const data = await res.json();
      if (!res.ok) {
        showToast(data.error || "Failed to remove the picture.", "error");
        return;
      }
      applyAvatar(null);
      showToast(data.message, "success");
    } catch (err) {
      console.error(err);
      showToast("Unable to reach the server.", "error");
    }
  });
}
