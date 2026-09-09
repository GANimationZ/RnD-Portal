// ---- Ikon Boxicons ----
const icons = {
  grid: 'bxs-dashboard',
  chart: 'bxs-bar-chart-alt-2',
  analyse: 'bxs-analyse',
  none: 'bx-empty-set',
  settings: 'bxs-cog',
  chevron: 'bxs-chevron-down',
  team: 'bxs-group', // ganti sesuai icon yang kamu mau untuk item Team
};

function iconTag(name) {
  return `<i class="bx ${icons[name]}"></i>`;
}

// ---- Struktur menu, dikelompokkan per kategori ----
// dropdown/children tetap didukung di renderNav di bawah, tapi sengaja
// tidak dipakai dulu (tidak ada item yang diisi `children`)
const NAV_GROUPS = [
  {
    label: 'Workspace',
    items: [
      {
        id: 'dashboard',
        label: 'Dashboard',
        icon: 'grid',
        desc: 'Production Verification Electric . Urgent─Important triage',
      },
      { id: 'statistic', label: 'Statistic', icon: 'chart' },
      { id: 'analyse', label: 'Analyse', icon: 'analyse' },
      { id: 'not-available', label: 'Not Available', icon: 'none' },
      { id: 'statistic-2', label: 'Statistic', icon: 'chart' }, // TODO: ganti label/id sesuai maksud aslinya
    ],
  },
  {
    label: 'Team',
    items: [
      { id: 'team-1', label: 'Team Item 1', icon: 'team' },
      { id: 'team-2', label: 'Team Item 2', icon: 'team' },
    ],
  },
];

const FOOTER_ITEMS = [{ id: 'settings', label: 'Pengaturan', icon: 'settings' }];

// ---- State ----
let openMenu = null;
let active = 'dashboard';
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

      const btn = document.createElement('button');
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

      // Dropdown/submenu: disimpan, belum dipakai (tidak ada item ber-children saat ini)
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

// ---- Render menu footer (tidak diubah dulu) ----
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

// ---- Cari item aktif beserta grup & (kalau ada) parent-nya ----
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

// ---- Update topbar: judul & breadcrumb ikut tombol aktif ----
function updateTopbar() {
  const found = findActiveItem();
  if (!found) return;

  const pathEl = document.getElementById('topbarPath');
  const titleEl = document.getElementById('topbarTitle');
  const descEl = document.getElementById('topbarDesc');

  pathEl.textContent = `RnD Portal > ${found.group.label}`;
  titleEl.textContent = found.item.label;
  descEl.textContent = found.item.desc || '';
}

function renderAll() {
  renderNav();
  renderFooter();
  updateTopbar();
}

// ---- Collapse / expand ----
const sidebar = document.getElementById('sidebar');
const toggleBtn = document.getElementById('toggleBtn');

toggleBtn.addEventListener('click', () => {
  collapsed = !collapsed;
  sidebar.classList.toggle('is-collapsed', collapsed);
  toggleBtn.title = collapsed ? 'Expand' : 'Collapse';
  renderAll();
});

// ---- Inisialisasi ----
renderAll();

// ---- Logout ----
document.getElementById('logoutBtn').addEventListener('click', async () => {
  await fetch('/logout', { method: 'POST' });
  window.location.href = '/';
});
