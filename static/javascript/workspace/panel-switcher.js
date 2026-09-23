// Generic tab/panel switcher, shared by every workspace page.
// Loaded once via the layout, not duplicated per page script.

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
      console.warn(`No panel found for tab "${target}"`);
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

  // Delay the initial tab activation until page scripts have finished
  // loading, so their 'panel:show' listeners are attached first.
  window.addEventListener("load", () => {
    const initialTab =
      navBar.querySelector(".flex-1.active") || navBar.querySelector(".flex-1");
    if (initialTab) {
      initialTab.classList.add("active");
      activatePanel(initialTab.dataset.tab);
    }
  });
})();
