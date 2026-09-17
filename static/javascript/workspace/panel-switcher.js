// ---- Tab/panel switcher generic — dipakai semua halaman workspace ----
// Dimuat SEKALI lewat layout (block script), bukan disalin ulang ke tiap file JS halaman.

(function () {
  const navBar = document.querySelector(".nav__bar");
  const panels = document.querySelectorAll(".main-body-content .body");
  if (!navBar || panels.length === 0) return;

  function activatePanel(target) {
    let matched = false;
    panels.forEach((panel) => {
      const isMatch = panel.dataset.panel === target;
      panel.classList.toggle("active", isMatch);
      if (isMatch) matched = true;
    });

    if (!matched) {
      console.warn(`Belum ada panel untuk tab "${target}"`);
      return;
    }

    document.dispatchEvent(
      new CustomEvent("panel:show", { detail: { panel: target } }),
    );
  }

  navBar.addEventListener("click", (e) => {
    const item = e.target.closest(".flex-1");
    if (!item) return;

    navBar
      .querySelectorAll(".flex-1")
      .forEach((el) => el.classList.remove("active"));
    item.classList.add("active");
    activatePanel(item.dataset.tab);
  });

  // ---- Aktivasi tab awal DITUNDA sampai semua script halaman selesai
  // dimuat & dieksekusi, supaya listener 'panel:show' di file JS halaman
  // (kpi-dashboard.js, issue-monitor.js, dst) sudah pasti terpasang duluan. ----
  window.addEventListener("load", () => {
    const initialTab =
      navBar.querySelector(".flex-1.active") || navBar.querySelector(".flex-1");
    if (initialTab) {
      initialTab.classList.add("active");
      activatePanel(initialTab.dataset.tab);
    }
  });
})();