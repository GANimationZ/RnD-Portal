// ====================================================================
// Attachment gallery: a grid of thumbnails for a list of files
// ({ name, type, url }). Images and videos show a real thumbnail, other
// files (PDF, Word, Excel, PowerPoint, ...) show a coloured file-type tile.
// Clicking a tile opens the preview with arrows to move between files.
//
//   renderAttachmentGallery(containerElement, issue.attachments)
// ====================================================================
(function () {
  function extensionOf(name) {
    const dot = String(name || "").lastIndexOf(".");
    return dot === -1 ? "" : name.slice(dot + 1).toUpperCase().slice(0, 4);
  }

  function thumbMarkup(att) {
    const url = escapeHtml(att.url);
    if (att.type === "image") {
      return `<img src="${url}" alt="${escapeHtml(att.name)}" loading="lazy" />`;
    }
    if (att.type === "video") {
      // "#t=0.1" makes the browser paint a frame as the thumbnail.
      return `<video src="${url}#t=0.1" preload="metadata" muted playsinline></video>
              <span class="att-tile__play" aria-hidden="true"></span>`;
    }
    const label = extensionOf(att.name) || String(att.type || "file").toUpperCase();
    return `<span class="att-tile__ext">${escapeHtml(label)}</span>`;
  }

  window.renderAttachmentGallery = function renderAttachmentGallery(container, attachments) {
    if (!container) return;
    const files = Array.isArray(attachments) ? attachments : [];

    if (files.length === 0) {
      container.innerHTML = "";
      return;
    }

    container.innerHTML = `
      <div class="att-gallery__title">Attachments <span>(${files.length})</span></div>
      <div class="att-gallery">
        ${files
          .map(
            (att, index) => `
          <button type="button" class="att-tile att-tile--${escapeHtml(att.type || "other")}"
                  data-index="${index}" title="${escapeHtml(att.name)}">
            <span class="att-tile__thumb">${thumbMarkup(att)}</span>
            <span class="att-tile__name">${escapeHtml(att.name)}</span>
          </button>`,
          )
          .join("")}
      </div>`;

    container.querySelectorAll(".att-tile").forEach((tile) => {
      tile.addEventListener("click", () => {
        const index = Number(tile.dataset.index);
        window.openFilePreview(files[index], { files, index });
      });
    });
  };
})();
