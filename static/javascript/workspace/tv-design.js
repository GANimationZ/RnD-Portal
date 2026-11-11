// ====================================================================
// TV Design Concept
// ====================================================================

const TV_API_BASE = "/workspace/tv-design-concept/api";

const TV_ATTACHMENT_ICON = {
  image: "bx-image",
  pdf: "bx-file",
  word: "bx-file",
  excel: "bx-file",
  ppt: "bx-slideshow",
  other: "bx-file",
};

let tvAssets = [];

async function fetchTvAssets(query = "") {
  try {
    const url = query
      ? `${TV_API_BASE}/assets?q=${encodeURIComponent(query)}`
      : `${TV_API_BASE}/assets`;
    const res = await fetch(url);
    const data = await res.json();
    tvAssets = data.assets || [];
  } catch (err) {
    console.error(err);
    showToast("Failed to load TV Design Concept data.", "error");
  }
  renderTvGrid();
}

function renderTvGrid() {
  const grid = document.getElementById("tvGrid");
  const empty = document.getElementById("tvEmpty");
  const count = document.getElementById("tvResultCount");
  if (!grid) return;

  if (count)
    count.textContent = `${tvAssets.length} ${tvAssets.length === 1 ? "entry" : "entries"}`;

  if (tvAssets.length === 0) {
    grid.innerHTML = "";
    if (empty) empty.classList.remove("is-hidden");
    return;
  }
  if (empty) empty.classList.add("is-hidden");

  grid.innerHTML = tvAssets
    .map(
      (asset) => `
    <div class="tv-card" data-asset-id="${asset.id}">
      <div class="tv-card__head">
        <span class="tv-card__title">${escapeHtml(asset.title)}</span>
        <button type="button" class="tv-card__delete" data-delete-id="${asset.id}" title="Delete">
          <i class="bxf bx-trash"></i>
        </button>
      </div>
      <div class="tv-card__meta">
        <span><i class="bxf bx-barcode"></i> ${escapeHtml(asset.serial_number)}</span>
        ${asset.production ? `<span><i class="bxf bx-factory"></i> ${escapeHtml(asset.production)}</span>` : ""}
        ${asset.origin ? `<span><i class="bxf bx-map"></i> ${escapeHtml(asset.origin)}</span>` : ""}
      </div>
      ${asset.notes ? `<p class="tv-card__notes">${escapeHtml(asset.notes)}</p>` : ""}
      <div class="tv-card__attachments">
        ${asset.attachments
          .map(
            (att, idx) => `
          <button type="button" class="attachment-chip" data-asset-id="${asset.id}" data-attachment-index="${idx}">
            <i class="bxf ${TV_ATTACHMENT_ICON[att.type] || "bx-file"}"></i> ${escapeHtml(att.name)}
          </button>`,
          )
          .join("")}
      </div>
    </div>
  `,
    )
    .join("");

  grid.querySelectorAll("[data-attachment-index]").forEach((chip) => {
    chip.addEventListener("click", () => {
      const asset = tvAssets.find((a) => a.id === Number(chip.dataset.assetId));
      if (asset)
        openFilePreview(
          asset.attachments[Number(chip.dataset.attachmentIndex)],
        );
    });
  });

  grid.querySelectorAll("[data-delete-id]").forEach((btn) => {
    btn.addEventListener("click", async (e) => {
      e.stopPropagation();
      const confirmed = await showConfirm(
        "Delete this entry along with all its attachments?",
      );
      if (!confirmed) return;

      try {
        const res = await fetch(
          `${TV_API_BASE}/assets/${btn.dataset.deleteId}`,
          { method: "DELETE" },
        );
        const data = await res.json();
        if (!res.ok) throw new Error(data.message || "Failed to delete entry.");
        showToast(data.message, "success");
        await fetchTvAssets(
          document.getElementById("tvSearchInput")?.value.trim(),
        );
      } catch (err) {
        showToast(err.message, "error");
      }
    });
  });
}

function openTvModal() {
  const modal = document.getElementById("tvModal");
  if (!modal) return;
  document.getElementById("tvForm")?.reset();
  const messageEl = document.getElementById("tvFormMessage");
  if (messageEl) messageEl.textContent = "";
  modal.classList.remove("is-hidden");
  document.getElementById("tvTitle")?.focus();
}

function closeTvModal() {
  document.getElementById("tvModal")?.classList.add("is-hidden");
}

document.addEventListener("DOMContentLoaded", () => {
  document.getElementById("tvAddBtn")?.addEventListener("click", openTvModal);
  document
    .getElementById("tvModalClose")
    ?.addEventListener("click", closeTvModal);
  bindBackdropClose(document.getElementById("tvModal"), closeTvModal);
  document.addEventListener("keydown", (e) => {
    const modal = document.getElementById("tvModal");
    if (e.key === "Escape" && modal && !modal.classList.contains("is-hidden"))
      closeTvModal();
  });

  const searchInput = document.getElementById("tvSearchInput");
  if (searchInput) {
    let debounceTimer;
    searchInput.addEventListener("input", (e) => {
      clearTimeout(debounceTimer);
      debounceTimer = setTimeout(
        () => fetchTvAssets(e.target.value.trim()),
        250,
      );
    });
  }

  const form = document.getElementById("tvForm");
  if (form) {
    form.addEventListener("submit", async (e) => {
      e.preventDefault();
      const messageEl = document.getElementById("tvFormMessage");
      const submitBtn = document.getElementById("tvSubmitBtn");
      const filesInput = document.getElementById("tvFiles");

      const formData = new FormData();
      formData.append("title", document.getElementById("tvTitle").value.trim());
      formData.append(
        "serial_number",
        document.getElementById("tvSerialNumber").value.trim(),
      );
      formData.append(
        "production",
        document.getElementById("tvProduction").value.trim(),
      );
      formData.append(
        "origin",
        document.getElementById("tvOrigin").value.trim(),
      );
      formData.append("notes", document.getElementById("tvNotes").value.trim());
      if (filesInput.files.length) {
        Array.from(filesInput.files).forEach((file) =>
          formData.append("attachments", file),
        );
      }

      submitBtn.disabled = true;
      submitBtn.value = "Saving...";

      try {
        const res = await fetch(`${TV_API_BASE}/assets`, {
          method: "POST",
          body: formData,
        });
        const data = await res.json();
        if (!res.ok) throw new Error(data.message || "Failed to save entry.");

        form.reset();
        closeTvModal();
        showToast(data.message, "success");
        await fetchTvAssets();
      } catch (err) {
        messageEl.textContent = err.message;
        showToast(err.message, "error");
      } finally {
        submitBtn.disabled = false;
        submitBtn.value = "Save Entry";
      }
    });
  }

  fetchTvAssets();
});
