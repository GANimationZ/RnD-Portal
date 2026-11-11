// ====================================================================
// Notifikasi custom (toast + confirm dialog) -- pengganti alert()/
// ====================================================================

// Escape teks yang berasal dari data (nama user, judul issue, dll.) sebelum
// disisipkan ke template string yang dipakai untuk innerHTML.
window.escapeHtml = function escapeHtml(value) {
  return String(value == null ? "" : value).replace(/[&<>"']/g, (ch) => ({
    "&": "&amp;",
    "<": "&lt;",
    ">": "&gt;",
    '"': "&quot;",
    "'": "&#39;",
  })[ch]);
};

// ============================================================
// bindBackdropClose(overlay, onClose)
// Closes a popup when the dark area around it is clicked -- but ONLY when the
// press AND the release both happened on that dark area.
//
// Without this, selecting text inside the popup and dragging the cursor past
// the edge of the dialog counted as a "click on the backdrop" (the browser
// fires `click` on the common ancestor, i.e. the overlay) and closed the popup
// in the middle of the selection.
// ============================================================
window.bindBackdropClose = function bindBackdropClose(overlay, onClose) {
  if (!overlay) return;
  let pressedOnBackdrop = false;
  let releasedOnBackdrop = false;

  overlay.addEventListener("pointerdown", (e) => {
    pressedOnBackdrop = e.target === overlay;
    releasedOnBackdrop = false;
  });
  overlay.addEventListener("pointerup", (e) => {
    releasedOnBackdrop = e.target === overlay;
  });
  overlay.addEventListener("click", (e) => {
    const isRealBackdropClick = e.target === overlay && pressedOnBackdrop && releasedOnBackdrop;
    pressedOnBackdrop = false;
    releasedOnBackdrop = false;
    if (isRealBackdropClick) onClose(e);
  });
};

(function () {
  function ensureContainer() {
    let container = document.getElementById("toastContainer");
    if (!container) {
      container = document.createElement("div");
      container.id = "toastContainer";
      container.className = "toast-container";
      document.body.appendChild(container);
    }
    return container;
  }

  const ICONS = {
    success: "bx-check-circle",
    error: "bx-error-circle",
    info: "bx-info-circle",
  };

  /**
   * showToast(message, type) -- notifikasi kecil di pojok, hilang sendiri.
   * type: "success" (default) | "error" | "info"
   */
  window.showToast = function showToast(message, type = "success") {
    const container = ensureContainer();
    const toast = document.createElement("div");
    toast.className = `toast toast--${type}`;
    toast.innerHTML = `
      <i class="bxf ${ICONS[type] || ICONS.info}"></i>
      <span class="toast__message"></span>
      <button type="button" class="toast__close" aria-label="Close"><i class="bxf bx-x"></i></button>
    `;
    toast.querySelector(".toast__message").textContent = message;

    const remove = () => {
      toast.classList.add("toast--leaving");
      setTimeout(() => toast.remove(), 180);
    };

    toast.querySelector(".toast__close").addEventListener("click", remove);
    container.appendChild(toast);
    setTimeout(remove, 4000);
  };

  window.showConfirm = function showConfirm(message, { confirmText = "Confirm", cancelText = "Cancel" } = {}) {
    return new Promise((resolve) => {
      const overlay = document.createElement("div");
      overlay.className = "confirm-overlay";
      overlay.innerHTML = `
        <div class="confirm-dialog">
          <p class="confirm-dialog__message"></p>
          <div class="confirm-dialog__actions">
            <button type="button" class="confirm-dialog__cancel"></button>
            <button type="button" class="confirm-dialog__confirm"></button>
          </div>
        </div>
      `;
      overlay.querySelector(".confirm-dialog__message").textContent = message;
      overlay.querySelector(".confirm-dialog__cancel").textContent = cancelText;
      overlay.querySelector(".confirm-dialog__confirm").textContent = confirmText;

      function close(result) {
        overlay.remove();
        document.removeEventListener("keydown", onKeydown);
        resolve(result);
      }
      function onKeydown(e) {
        if (e.key === "Escape") close(false);
      }

      overlay.querySelector(".confirm-dialog__cancel").addEventListener("click", () => close(false));
      overlay.querySelector(".confirm-dialog__confirm").addEventListener("click", () => close(true));
      bindBackdropClose(overlay, () => close(false));
      document.addEventListener("keydown", onKeydown);

      document.body.appendChild(overlay);
    });
  };
})();
