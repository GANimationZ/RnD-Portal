// ---- Navbar for panel switching ---- //
const navBar = document.querySelector(".nav__bar");
const panels = document.querySelectorAll(".main-body-content .body");

navBar.addEventListener("click", (e) => {
  const item = e.target.closest(".flex-1");
  if (!item) return;

  navBar
    .querySelectorAll(".flex-1")
    .forEach((el) => el.classList.remove("active"));
  item.classList.add("active");

  const target = item.dataset.tab;
  let matched = false;

  panels.forEach((panel) => {
    const isMatch = panel.dataset.panel === target;
    panel.classList.toggle("active", isMatch);
    if (isMatch) matched = true;
  });

  if (!matched) {
    console.warn(`Belum ada panel untuk tab "${target}"`);
  }
});

// ==================== DATA (Dummy) ====================

const toolsData = [
  {
    id: "t1",
    name: "Multimeter Fluke 117",
    type: "Measurement",
    owner: "Rani Freya",
    icon: "bx-analyse",
    href: "https://www.google.com",
  },
  {
    id: "t2",
    name: "Soldering Station Hakko FX-888D",
    type: "Soldering",
    owner: "Dimas Pratama",
    icon: "bx-wrench",
    href: "#",
  },
  {
    id: "t3",
    name: "Oscilloscope Rigol DS1054Z",
    type: "Measurement",
    owner: "Sinta Wijaya",
    icon: "bx-pulse",
    href: "#",
  },
  {
    id: "t4",
    name: "Hot Air Rework Station",
    type: "Soldering",
    owner: "Rani Freya",
    icon: "bx-wind",
    href: "#",
  },
  {
    id: "t5",
    name: "Bench Power Supply",
    type: "Power",
    owner: "Dimas Pratama",
    icon: "bx-bolt-circle",
    href: "#",
  },
];

const equipmentsData = [
  {
    id: "e1",
    name: "Reflow Oven RO-450",
    type: "SMT Machine",
    owner: "Rani Freya",
    icon: "bx-server",
    href: "#",
  },
  {
    id: "e2",
    name: "Pick and Place Machine YSM40",
    type: "SMT Machine",
    owner: "Dimas Pratama",
    icon: "bx-chip",
    href: "#",
  },
  {
    id: "e3",
    name: "Wave Soldering Machine WS-350",
    type: "Assembly Line",
    owner: "Dimas Pratama",
    icon: "bx-git-merge",
    href: "#",
  },
  {
    id: "e4",
    name: "AOI Inspection System AX-8",
    type: "QA Equipment",
    owner: "Sinta Wijaya",
    icon: "bx-search-alt",
    href: "#",
  },
  {
    id: "e5",
    name: "ICT Tester Bed-of-Nails",
    type: "QA Equipment",
    owner: "Sinta Wijaya",
    icon: "bx-test-tube",
    href: "#",
  },
];

// ==================== FACTORY: BROWSER CARD/LIST ====================

function createItemBrowser({
  data,
  searchId,
  typeSelectId,
  ownerSelectId,
  resetId,
  switcherId,
  cardListId,
  menuListId,
  cardContainerId,
  menuContainerId,
}) {
  let currentView = "card";

  function populateTypeFilter() {
    const typeSelect = document.getElementById(typeSelectId);
    if (!typeSelect) return;

    const uniqueTypes = [...new Set(data.map((item) => item.type))];
    uniqueTypes.forEach((type) => {
      const option = document.createElement("option");
      option.value = type;
      option.textContent = type;
      typeSelect.appendChild(option);
    });
  }

  function populateOwnerFilter() {
    const ownerSelect = document.getElementById(ownerSelectId);
    if (!ownerSelect) return;

    const uniqueOwners = [...new Set(data.map((item) => item.owner))];
    uniqueOwners.forEach((owner) => {
      const option = document.createElement("option");
      option.value = owner;
      option.textContent = owner;
      ownerSelect.appendChild(option);
    });
  }

  function getFilteredItems() {
    const search = (document.getElementById(searchId)?.value || "")
      .trim()
      .toLowerCase();
    const typeSelect = document.getElementById(typeSelectId);
    const ownerSelect = document.getElementById(ownerSelectId);

    const selectedType = typeSelect?.value || "All Types";
    const selectedOwner = ownerSelect?.value || "All Owners";

    return data.filter((item) => {
      const matchesSearch = !search || item.name.toLowerCase().includes(search);
      const matchesType =
        selectedType === "All Types" || item.type === selectedType;
      const matchesOwner =
        selectedOwner === "All Owners" || item.owner === selectedOwner;
      return matchesSearch && matchesType && matchesOwner;
    });
  }

  function renderCardView(items) {
    const container = document.getElementById(cardContainerId);
    if (!container) return;

    if (items.length === 0) {
      container.innerHTML =
        '<div class="empty-state">Tidak ada data yang cocok dengan filter.</div>';
      return;
    }

    container.innerHTML = items
      .map(
        (item) => `
      <a class="tool-card" href="${item.href}">
        <span class="tool-card__icon"><i class="bxf ${item.icon}"></i></span>
        <div class="tool-card__body">
          <span class="tool-card__name">${item.name}</span>
          <span class="tool-card__type">${item.type}</span>
        </div>
        <span class="tool-card__owner">${item.owner}</span>
      </a>
    `,
      )
      .join("");
  }

  function renderListView(items) {
    const container = document.getElementById(menuContainerId);
    if (!container) return;

    if (items.length === 0) {
      container.innerHTML =
        '<div class="empty-state">Tidak ada data yang cocok dengan filter.</div>';
      return;
    }

    container.innerHTML = items
      .map(
        (item) => `
      <a class="tool-list-item" href="${item.href}">
        <span class="tool-list-item__icon"><i class="bxf ${item.icon}"></i></span>
        <span class="tool-list-item__name">${item.name}</span>
        <span class="tool-list-item__type">${item.type}</span>
        <span class="tool-list-item__owner">${item.owner}</span>
        <i class="bxf bx-chevron-right tool-list-item__chevron"></i>
      </a>
    `,
      )
      .join("");
  }

  function renderItems() {
    const items = getFilteredItems();
    renderCardView(items);
    renderListView(items);
  }

  function setView(view) {
    currentView = view;
    const cardView = document.getElementById(cardListId);
    const listView = document.getElementById(menuListId);
    const switcherIcon = document.querySelector(`#${switcherId} i`);
    if (!cardView || !listView) return;

    if (view === "card") {
      cardView.style.display = "";
      listView.style.display = "none";
      if (switcherIcon) switcherIcon.className = "bxf bx-list-ul";
    } else {
      cardView.style.display = "none";
      listView.style.display = "";
      if (switcherIcon) switcherIcon.className = "bxf bx-grid-alt";
    }
  }

  function init() {
    populateTypeFilter();
    populateOwnerFilter();
    renderItems();
    setView("card");

    document.getElementById(searchId)?.addEventListener("input", renderItems);
    document
      .getElementById(typeSelectId)
      ?.addEventListener("change", renderItems);
    document
      .getElementById(ownerSelectId)
      ?.addEventListener("change", renderItems);

    document.getElementById(resetId)?.addEventListener("click", () => {
      const searchInput = document.getElementById(searchId);
      const typeSelect = document.getElementById(typeSelectId);
      const ownerSelect = document.getElementById(ownerSelectId);
      if (searchInput) searchInput.value = "";
      if (typeSelect) typeSelect.value = "All Types";
      if (ownerSelect) ownerSelect.value = "All Owners";
      renderItems();
    });

    document.getElementById(switcherId)?.addEventListener("click", () => {
      setView(currentView === "card" ? "list" : "card");
    });
  }

  return { init };
}

// ==================== INIT ====================

document.addEventListener("DOMContentLoaded", () => {
  createItemBrowser({
    data: toolsData,
    searchId: "toolSearch",
    typeSelectId: "toolTypeFilter",
    ownerSelectId: "toolOwnerFilter",
    resetId: "reset",
    switcherId: "viewSwitcher",
    cardListId: "cardListView",
    menuListId: "menuListView",
    cardContainerId: "cardContainer",
    menuContainerId: "menuListContainer",
  }).init();

  createItemBrowser({
    data: equipmentsData,
    searchId: "equipmentSearch",
    typeSelectId: "equipmentTypeFilter",
    ownerSelectId: "equipmentOwnerFilter",
    resetId: "resetEquipment",
    switcherId: "equipmentViewSwitcher",
    cardListId: "equipmentCardListView",
    menuListId: "equipmentMenuListView",
    cardContainerId: "equipmentCardContainer",
    menuContainerId: "equipmentMenuListContainer",
  }).init();
});
