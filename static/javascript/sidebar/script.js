// ---- Ikon Boxicons ----
const icons = {
  chart: 'bx-chart-bar-big-columns',
  concept: 'bx-monitor-wallpaper',
  issue: 'bx-alert-triangle',
  tool: 'bx-spanner',
  pin: 'bx-location-pin',
  dollar: 'bx-dollar-circle',
  chevron: 'bx-chevron-down',
  team: 'bx-community',
  folder: 'bx-folder',
  door: 'bx-door-open-alt',
  cog: 'bx-cog',
};

function iconTag(name) {
  return `<i class="bxf ${icons[name]}"></i>`;
}

// ---- Struktur menu, dikelompokkan per kategori ----
const NAV_GROUPS = [
  {
    label: 'Workspace',
    items: [
      { id: 'kpi-dashboard', label: 'Team KPI Dashboard', icon: 'chart', href: '/workspace/kpi-dashboard' },
      { id: 'analyse', label: 'TV Design Concept', icon: 'concept', href: '/workspace/tv-design-concept' },
      {
        id: 'issue-monitor',
        label: 'LVT/MNT ─ Issue Monitoring',
        icon: 'issue',
        href: '/workspace/issue-monitor',
      },
      { id: 'mb-tool', label: 'Mainboard Tool', icon: 'tool', href: '/workspace/mainboard-tool' },
      { id: 'asset-equiptment', label: 'Asset/Equipmet Locator', icon: 'pin', href: '/workspace/asset-locator' },
      { id: 'material-cost', label: 'Material Cost Analysis', icon: 'dollar', href: '/workspace/material-cost' },
    ],
  },
  {
    label: 'Team',
    items: [
      { id: 'structure', label: 'Organization Structure', icon: 'team', href: '/team/structure' },
      { id: 'others', label: 'Others', icon: 'folder', href: '/team/others' },
    ],
  },
];

const FOOTER_ITEMS = [{ id: 'settings', label: 'Settings', icon: 'cog' }];

// ---- State ----
let openMenu = null;
let active = window.ACTIVE_NAV || 'kpi-dashboard';
let collapsed = true;

// ---- Render menu navigasi utama (dengan label kategori) ----
function renderNav() {
  const nav = document.getElementById('nav');
  nav.innerHTML = '';

  NAV_GROUPS.forEach((group) => {
    const groupLabel = document.createElement('div');
    groupLabel.className = 'nav-group__label';
    groupLabel.textContent = group.label;
    nav.appendChild(groupLabel);

    group.items.forEach((item) => {
      const hasChildren = !!item.children;
      const isOpen = openMenu === item.id;
      const isActive = active === item.id;

      const wrapper = document.createElement('div');

      const btn = document.createElement('a');
      btn.href = item.href;
      btn.className = 'nav-item' + (isActive ? ' is-active' : '');
      btn.title = collapsed ? item.label : '';
      btn.innerHTML = `
        <span class="nav-item__left">
          <span class="nav-item__icon">${iconTag(item.icon)}</span>
          <span class="nav-item__label">${item.label}</span>
        </span>
        ${hasChildren ? `<span class="nav-item__chevron${isOpen ? ' is-open' : ''}">${iconTag('chevron')}</span>` : ''}
      `;
      btn.addEventListener('click', () => {
        active = item.id;
        if (hasChildren && !collapsed) {
          openMenu = openMenu === item.id ? null : item.id;
        }
        renderAll();
      });
      wrapper.appendChild(btn);

      // Dropdown/submenu (Unused)
      if (hasChildren) {
        const submenu = document.createElement('div');
        submenu.className = 'submenu' + (isOpen && !collapsed ? ' is-open' : '');
        const inner = document.createElement('div');
        inner.className = 'submenu__inner';

        item.children.forEach((child) => {
          const childBtn = document.createElement('button');
          childBtn.className = 'submenu__item' + (active === child.id ? ' is-active' : '');
          childBtn.textContent = child.label;
          childBtn.addEventListener('click', (e) => {
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

// Render Menu Footer (Unused)
function renderFooter() {
  const footer = document.getElementById('footer');
  footer.innerHTML = '';

  FOOTER_ITEMS.forEach((item) => {
    const isActive = active === item.id;
    const btn = document.createElement('button');
    btn.className = 'footer-item' + (isActive ? ' is-active' : '');
    btn.title = collapsed ? item.label : '';
    btn.innerHTML = `
      <span class="footer-item__icon">${iconTag(item.icon)}</span>
      <span class="footer-item__label">${item.label}</span>
    `;
    btn.addEventListener('click', () => {
      active = item.id;
      renderAll();
    });
    footer.appendChild(btn);
  });
}

// findActiveChildren (Unused)
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
  return null;
}

// ---- Update topbar ----
function updateTopbar() {
  const found = findActiveItem();
  if (!found) return;

  const pathEl = document.getElementById('topbarPath');
  const titleEl = document.getElementById('topbarTitle');

  pathEl.textContent = `RnD Portal > ${found.group.label}`;
  titleEl.textContent = found.item.label;
}

function renderAll() {
  renderNav();
  renderFooter();
  updateTopbar();
}

// ---- Collapse / expand ----
const sidebar = document.getElementById('sidebar');
const toggleBtn = document.getElementById('toggleBtn');

toggleBtn.addEventListener('click', (e) => {
  e.stopPropagation();
  collapsed = !collapsed;
  sidebar.classList.toggle('is-collapsed', collapsed);
  toggleBtn.title = collapsed ? 'Expand' : 'Collapse';
  renderAll();
});

document.addEventListener('click', (e) => {
  if (collapsed) return;
  if (sidebar.contains(e.target)) return;

  collapsed = true;
  sidebar.classList.add('is-collapsed');
  toggleBtn.title = 'Expand';
  renderAll();
});

// ---- Initialize ----
renderAll();

// ---- Logout ----
document.getElementById('logoutBtn').addEventListener('click', async () => {
  await fetch('/logout', { method: 'POST' });
  window.location.href = '/';
});
