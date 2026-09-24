// ---- Boxicons ----
const icons = {
  chart: "bx-chart-bar-big-columns",
  concept: "bx-monitor-wallpaper",
  issue: "bx-alert-triangle",
  tool: "bx-spanner",
  pin: "bx-location-pin",
  dollar: "bx-dollar-circle",
  chevron: "bx-chevron-down",
  team: "bx-community",
  folder: "bx-folder",
  door: "bx-door-open-alt",
  cog: "bx-cog",
  user: "bx-user-circle",
};

function iconTag(name) {
  return `<i class="bxf ${icons[name]}"></i>`;
}

// ---- Menu structure ----
// The "Administration" group is only added for role "Super Admin"
// (window.CURRENT_ROLE, injected via templates/partials/top-sidebar.html)
// -- Admin & Member never see this menu at all (not rendered, not just
// hidden with CSS).
const NAV_GROUPS = [
  {
    label: "Workspace",
    items: [
      // QA (Admin) has no access to KPI Dashboard -- only render this
      // item for Super Admin & Member (backend also enforces this via
      // roles_required; this just keeps Admin from seeing a dead link).
      ...(window.CURRENT_ROLE === "Admin"
        ? []
        : [
            {
              id: "kpi-dashboard",
              label: "Team KPI Dashboard",
              icon: "chart",
              href: "/workspace/kpi-dashboard",
            },
          ]),
      {
        id: "analyse",
        label: "TV Design Concept",
        icon: "concept",
        href: "/workspace/tv-design-concept",
      },
      {
        id: "issue-monitor",
        label: "LVT/MNT ─ Issue Monitoring",
        icon: "issue",
        href: "/workspace/issue-monitor",
      },
      {
        id: "tools",
        label: "Integrated Tab Tools",
        icon: "tool",
        href: "/workspace/tools",
      },
    ],
  },
  {
    label: "Team",
    items: [
      {
        id: "structure",
        label: "Organization Structure",
        icon: "team",
        href: "/team/structure",
      },
      { id: "others", label: "Others", icon: "folder", href: "/team/others" },
    ],
  },
];

if (window.CURRENT_ROLE === "Super Admin") {
  NAV_GROUPS.push({
    label: "Administration",
    items: [
      {
        id: "user-management",
        label: "User Management",
        icon: "user",
        href: "/admin/users",
      },
    ],
  });
}

const FOOTER_ITEMS = [
  { id: "settings", label: "Settings", icon: "cog", href: "/settings" },
];

// ---- State ----
let openMenu = null;
let active = window.ACTIVE_NAV || "kpi-dashboard";
let collapsed = true;

// ---- Render nav menu ----
function renderNav() {
  const nav = document.getElementById("nav");
  nav.innerHTML = "";

  NAV_GROUPS.forEach((group) => {
    const groupLabel = document.createElement("div");
    groupLabel.className = "nav-group__label";
    groupLabel.textContent = group.label;
    nav.appendChild(groupLabel);

    group.items.forEach((item) => {
      const hasChildren = !!item.children;
      const isOpen = openMenu === item.id;
      const isActive = active === item.id;

      const wrapper = document.createElement("div");

      const btn = document.createElement("a");
      btn.href = item.href;
      btn.className = "nav-item" + (isActive ? " is-active" : "");
      btn.title = collapsed ? item.label : "";
      btn.innerHTML = `
        <span class="nav-item__left">
          <span class="nav-item__icon">${iconTag(item.icon)}</span>
          <span class="nav-item__label">${item.label}</span>
        </span>
        ${hasChildren ? `<span class="nav-item__chevron${isOpen ? " is-open" : ""}">${iconTag("chevron")}</span>` : ""}
      `;
      btn.addEventListener("click", () => {
        if (hasChildren && !collapsed) {
          openMenu = openMenu === item.id ? null : item.id;
          renderNav(); // only toggles the submenu, doesn't touch the topbar
        }
      });
      wrapper.appendChild(btn);

      // Dropdown/submenu (unused)
      if (hasChildren) {
        const submenu = document.createElement("div");
        submenu.className =
          "submenu" + (isOpen && !collapsed ? " is-open" : "");
        const inner = document.createElement("div");
        inner.className = "submenu__inner";

        item.children.forEach((child) => {
          const childBtn = document.createElement("button");
          childBtn.className =
            "submenu__item" + (active === child.id ? " is-active" : "");
          childBtn.textContent = child.label;
          childBtn.addEventListener("click", (e) => {
            e.stopPropagation();
            active = child.id;
            renderAll();
          });
          inner.appendChild(childBtn);
        });

        submenu.appendChild(inner);
        wrapper.appendChild(submenu);
      }

      nav.appendChild(wrapper);
    });
  });
}

// Render footer menu
function renderFooter() {
  const footer = document.getElementById("footer");
  footer.innerHTML = "";

  FOOTER_ITEMS.forEach((item) => {
    const isActive = active === item.id;
    const btn = document.createElement("a");
    btn.href = item.href || "#";
    btn.className = "footer-item" + (isActive ? " is-active" : "");
    btn.title = collapsed ? item.label : "";
    btn.innerHTML = `
      <span class="footer-item__icon">${iconTag(item.icon)}</span>
      <span class="footer-item__label">${item.label}</span>
    `;
    footer.appendChild(btn);
  });
}

// findActiveChildren
function findActiveItem() {
  for (const group of NAV_GROUPS) {
    for (const item of group.items) {
      if (item.id === active) return { item, group };
      if (item.children) {
        const child = item.children.find((c) => c.id === active);
        if (child) return { item: child, group, parent: item };
      }
    }
  }

  const footerItem = FOOTER_ITEMS.find((item) => item.id === active);
  if (footerItem) return { item: footerItem, group: { label: "Account" } };

  return null;
}

// ---- Update topbar ----
function updateTopbar() {
  const found = findActiveItem();
  if (!found) return;

  const pathEl = document.getElementById("topbarPath");
  const titleEl = document.getElementById("topbarTitle");

  pathEl.textContent = `RnD Portal > ${found.group.label}`;
  titleEl.textContent = found.item.label;
}

function renderAll() {
  renderNav();
  renderFooter();
  updateTopbar();
}

// ---- Collapse / expand ----
const sidebar = document.getElementById("sidebar");
const toggleBtn = document.getElementById("toggleBtn");

toggleBtn.addEventListener("click", (e) => {
  e.stopPropagation();
  collapsed = !collapsed;
  sidebar.classList.toggle("is-collapsed", collapsed);
  toggleBtn.title = collapsed ? "Expand" : "Collapse";
  renderAll();
});

document.addEventListener("click", (e) => {
  if (collapsed) return;
  if (sidebar.contains(e.target)) return;

  collapsed = true;
  sidebar.classList.add("is-collapsed");
  toggleBtn.title = "Expand";
  renderAll();
});

// ---- Initialize ----
renderAll();

// ---- Logout ----
document.getElementById("logoutBtn").addEventListener("click", async () => {
  await fetch("/logout", { method: "POST" });
  window.location.href = "/";
});
