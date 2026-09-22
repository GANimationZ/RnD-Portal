// ====================================================================
// Notifikasi custom (toast + confirm dialog) -- pengganti alert()/
// confirm() bawaan browser yang tampilannya beda-beda tiap browser &
// tidak bisa di-style. Dimuat global lewat templates/partials/
// top-sidebar.html, jadi tersedia di semua halaman workspace/admin
// sebagai window.showToast() & window.showConfirm().
// ====================================================================

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
      <button type="button" class="toast__close" aria-label="Tutup"><i class="bxf bx-x"></i></button>
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

  /**
   * showConfirm(message) -- dialog konfirmasi custom, mengembalikan
   * Promise<boolean> supaya bisa dipakai dengan `await` menggantikan
   * `if (confirm(...))`.
   */
  window.showConfirm = function showConfirm(message, { confirmText = "Ya, lanjutkan", cancelText = "Batal" } = {}) {
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
      overlay.addEventListener("click", (e) => {
        if (e.target === overlay) close(false);
      });
      document.addEventListener("keydown", onKeydown);

      document.body.appendChild(overlay);
    });
  };
})();
