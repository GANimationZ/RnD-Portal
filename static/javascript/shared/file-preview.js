// ====================================================================
// Shared file preview modal -- window.openFilePreview({name, type, url}).
// Loaded globally via templates/partials/top-sidebar.html, used by both
// Issue Monitor attachments and TV Design Concept assets.
//
// Preview support by type:
//   image -> <img>
//   pdf   -> <iframe> (native browser PDF viewer)
//   excel -> parsed client-side with SheetJS (CDN, needs internet) and
//            rendered as an HTML table
//   word / ppt / other -> no reliable client-only renderer exists, so we
//            show a "preview not available" state with a download button
// ====================================================================

(function () {
  let sheetJsLoadPromise = null;

  function loadSheetJs() {
    if (window.XLSX) return Promise.resolve();
    if (sheetJsLoadPromise) return sheetJsLoadPromise;

    sheetJsLoadPromise = new Promise((resolve, reject) => {
      const script = document.createElement("script");
      script.src = "https://cdnjs.cloudflare.com/ajax/libs/xlsx/0.18.5/xlsx.full.min.js";
      script.onload = resolve;
      script.onerror = () => reject(new Error("SheetJS gagal dimuat (butuh koneksi internet)."));
      document.head.appendChild(script);
    });
    return sheetJsLoadPromise;
  }

  function buildOverlay() {
    const overlay = document.createElement("div");
    overlay.className = "file-preview-overlay";
    overlay.innerHTML = `
      <div class="file-preview-dialog">
        <div class="file-preview-dialog__head">
          <span class="file-preview-dialog__name"></span>
          <div class="file-preview-dialog__actions">
            <a class="file-preview-dialog__download" target="_blank" rel="noopener">
              <i class="bxf bx-download"></i> Download
            </a>
            <button type="button" class="file-preview-dialog__close" aria-label="Tutup">
              <i class="bxf bx-x"></i>
            </button>
          </div>
        </div>
        <div class="file-preview-dialog__body">
          <div class="file-preview-loading">Memuat preview...</div>
        </div>
      </div>
    `;
    return overlay;
  }

  async function renderBody(body, file) {
    if (file.type === "image") {
      body.innerHTML = `<img src="${file.url}" alt="${file.name}" class="file-preview-image" />`;
      return;
    }

    if (file.type === "pdf") {
      body.innerHTML = `<iframe src="${file.url}" class="file-preview-frame"></iframe>`;
      return;
    }

    if (file.type === "excel") {
      try {
        await loadSheetJs();
        const response = await fetch(file.url);
        const buffer = await response.arrayBuffer();
        const workbook = window.XLSX.read(buffer, { type: "array" });
        const firstSheetName = workbook.SheetNames[0];
        const html = window.XLSX.utils.sheet_to_html(workbook.Sheets[firstSheetName]);
        body.innerHTML = `<div class="file-preview-excel">${html}</div>`;
      } catch (err) {
        console.error(err);
        body.innerHTML = unsupportedPreviewMarkup(
          "Preview Excel butuh koneksi internet (memuat SheetJS). Silakan download file-nya.",
        );
      }
      return;
    }

    // Word / PowerPoint / other: no client-only renderer available.
    body.innerHTML = unsupportedPreviewMarkup(
      `Preview belum didukung untuk tipe file ini (${file.type.toUpperCase()}). Silakan download untuk membukanya.`,
    );
  }

  function unsupportedPreviewMarkup(message) {
    return `
      <div class="file-preview-unsupported">
        <i class="bxf bx-file-blank"></i>
        <p>${message}</p>
      </div>
    `;
  }

  window.openFilePreview = function openFilePreview(file) {
    if (!file || !file.url) return;

    const overlay = buildOverlay();
    overlay.querySelector(".file-preview-dialog__name").textContent = file.name || "File";
    const downloadLink = overlay.querySelector(".file-preview-dialog__download");
    downloadLink.href = file.url;
    downloadLink.setAttribute("download", file.name || "");

    function close() {
      overlay.remove();
      document.removeEventListener("keydown", onKeydown);
    }
    function onKeydown(e) {
      if (e.key === "Escape") close();
    }

    overlay.querySelector(".file-preview-dialog__close").addEventListener("click", close);
    overlay.addEventListener("click", (e) => {
      if (e.target === overlay) close();
    });
    document.addEventListener("keydown", onKeydown);

    document.body.appendChild(overlay);
    renderBody(overlay.querySelector(".file-preview-dialog__body"), file);
  };
})();
