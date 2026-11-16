// ====================================================================
// Shared file preview modal
// ====================================================================

(function () {
  let sheetJsLoadPromise = null;

  function loadSheetJs() {
    if (window.XLSX) return Promise.resolve();
    if (sheetJsLoadPromise) return sheetJsLoadPromise;

    sheetJsLoadPromise = new Promise((resolve, reject) => {
      const script = document.createElement("script");
      script.src = "/static/vendor/sheetjs/xlsx.full.min.js";
      script.onload = resolve;
      script.onerror = () => reject(new Error("Failed to load SheetJS."));
      document.head.appendChild(script);
    });
    return sheetJsLoadPromise;
  }

  function buildOverlay() {
    const overlay = document.createElement("div");
    overlay.className = "file-preview-overlay";
    overlay.innerHTML = `
      <button type="button" class="file-preview-nav file-preview-nav--prev" aria-label="Previous file">
        <i class="bxf bx-chevron-left"></i>
      </button>
      <div class="file-preview-dialog">
        <div class="file-preview-dialog__head">
          <span class="file-preview-dialog__name"></span>
          <span class="file-preview-dialog__counter"></span>
          <div class="file-preview-dialog__actions">
            <a class="file-preview-dialog__download" target="_blank" rel="noopener">
              <i class="bxf bx-download"></i> Download
            </a>
            <button type="button" class="file-preview-dialog__close" aria-label="Close">
              <i class="bxf bx-x"></i>
            </button>
          </div>
        </div>
        <div class="file-preview-dialog__body">
          <div class="file-preview-loading">Loading preview...</div>
        </div>
      </div>
      <button type="button" class="file-preview-nav file-preview-nav--next" aria-label="Next file">
        <i class="bxf bx-chevron-right"></i>
      </button>
    `;
    return overlay;
  }

  const MAX_TEXT_PREVIEW_CHARS = 100000;

  async function renderBody(body, file, isStale) {
    const url = escapeHtml(file.url);
    const name = escapeHtml(file.name);

    if (file.type === "image") {
      body.innerHTML = `<img src="${url}" alt="${name}" class="file-preview-image" />`;
      return;
    }

    if (file.type === "video") {
      body.innerHTML = `
        <video class="file-preview-video" src="${url}" controls autoplay playsinline>
          Your browser cannot play this video. Please download it instead.
        </video>`;
      return;
    }

    if (file.type === "audio") {
      body.innerHTML = `
        <div class="file-preview-audio">
          <i class="bxf bx-music"></i>
          <audio src="${url}" controls autoplay></audio>
        </div>`;
      return;
    }

    if (file.type === "pdf") {
      body.innerHTML = `<iframe src="${url}" class="file-preview-frame"></iframe>`;
      return;
    }

    if (file.type === "text") {
      try {
        const response = await fetch(file.url);
        const text = await response.text();
        if (isStale()) return;
        const shown = text.length > MAX_TEXT_PREVIEW_CHARS
          ? `${text.slice(0, MAX_TEXT_PREVIEW_CHARS)}\n\n... (preview truncated, download the file to read the rest)`
          : text;
        const pre = document.createElement("pre");
        pre.className = "file-preview-text";
        pre.textContent = shown; // textContent: never interpret the file as HTML
        body.replaceChildren(pre);
      } catch (err) {
        console.error(err);
        if (!isStale()) {
          body.innerHTML = unsupportedPreviewMarkup(
            "Text preview failed to load. Please download the file instead.",
          );
        }
      }
      return;
    }

    if (file.type === "excel") {
      try {
        await loadSheetJs();
        const response = await fetch(file.url);
        const buffer = await response.arrayBuffer();
        if (isStale()) return;
        const workbook = window.XLSX.read(buffer, { type: "array" });
        const firstSheetName = workbook.SheetNames[0];
        const html = window.XLSX.utils.sheet_to_html(workbook.Sheets[firstSheetName]);
        body.innerHTML = `<div class="file-preview-excel">${html}</div>`;
      } catch (err) {
        console.error(err);
        if (!isStale()) {
          body.innerHTML = unsupportedPreviewMarkup(
            "Excel preview failed to load. Please download the file instead.",
          );
        }
      }
      return;
    }

    // Word, PowerPoint, archives, ...: browsers cannot show these.
    body.innerHTML = unsupportedPreviewMarkup(
      `Preview isn't supported for this file type (${escapeHtml(String(file.type || "file").toUpperCase())}). Please download it to open.`,
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

  // openFilePreview(file)                          -> one file
  // openFilePreview(file, { files, index })        -> a gallery: the arrows and
  //                                                   the left/right keys move
  //                                                   through `files`.
  window.openFilePreview = function openFilePreview(file, options) {
    const files = options && Array.isArray(options.files) && options.files.length
      ? options.files
      : [file];
    let index = options && Number.isInteger(options.index)
      ? options.index
      : Math.max(0, files.indexOf(file));
    if (!files[index] || !files[index].url) return;

    const overlay = buildOverlay();
    const body = overlay.querySelector(".file-preview-dialog__body");
    const downloadLink = overlay.querySelector(".file-preview-dialog__download");
    const prevBtn = overlay.querySelector(".file-preview-nav--prev");
    const nextBtn = overlay.querySelector(".file-preview-nav--next");
    let showToken = 0; // lets a slow preview notice the user already moved on

    function show(newIndex) {
      index = (newIndex + files.length) % files.length;
      const current = files[index];
      const token = ++showToken;

      overlay.querySelector(".file-preview-dialog__name").textContent = current.name || "File";
      overlay.querySelector(".file-preview-dialog__counter").textContent =
        files.length > 1 ? `${index + 1} / ${files.length}` : "";
      downloadLink.href = current.url;
      downloadLink.setAttribute("download", current.name || "");

      body.innerHTML = `<div class="file-preview-loading">Loading preview...</div>`;
      renderBody(body, current, () => token !== showToken);
    }

    function close() {
      body.innerHTML = ""; // stops any playing video/audio
      overlay.remove();
      document.removeEventListener("keydown", onKeydown);
    }
    function onKeydown(e) {
      if (e.key === "Escape") close();
      else if (files.length > 1 && e.key === "ArrowLeft") show(index - 1);
      else if (files.length > 1 && e.key === "ArrowRight") show(index + 1);
    }

    const single = files.length < 2;
    prevBtn.classList.toggle("is-hidden", single);
    nextBtn.classList.toggle("is-hidden", single);
    prevBtn.addEventListener("click", () => show(index - 1));
    nextBtn.addEventListener("click", () => show(index + 1));
    overlay.querySelector(".file-preview-dialog__close").addEventListener("click", close);
    bindBackdropClose(overlay, close);
    document.addEventListener("keydown", onKeydown);

    document.body.appendChild(overlay);
    show(index);
  };
})();
