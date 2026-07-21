// Renders the sidebar + topbar shell used on every authenticated page.
const ICONS = {
  dashboard: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><rect x="3" y="3" width="7" height="9" rx="1.5"/><rect x="14" y="3" width="7" height="5" rx="1.5"/><rect x="14" y="12" width="7" height="9" rx="1.5"/><rect x="3" y="16" width="7" height="5" rx="1.5"/></svg>',
  buildings: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M4 21V6l7-3 7 3v15"/><path d="M4 21h16"/><path d="M9 9h1M9 13h1M14 9h1M14 13h1"/><path d="M10 21v-5h4v5"/></svg>',
  monitoring: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M3 12h4l2 7 4-14 2 7h6"/></svg>',
  alerts: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M12 3l9 16H3z"/><path d="M12 10v4M12 17h.01"/></svg>',
  analytics: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M4 20V10M12 20V4M20 20v-7"/></svg>',
  reports: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M6 2h9l3 3v17H6z"/><path d="M14 2v4h4"/><path d="M9 13h6M9 17h6M9 9h2"/></svg>',
  users: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><circle cx="9" cy="8" r="3.2"/><path d="M3 20c0-3.3 2.7-5.5 6-5.5s6 2.2 6 5.5"/><circle cx="17.5" cy="9" r="2.4"/><path d="M15.8 14.8c2.4.4 4.2 2.3 4.2 5.2"/></svg>',
  settings: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><circle cx="12" cy="12" r="3"/><path d="M19.4 13a1.7 1.7 0 000-2l1.1-1.5-1.6-2.8-1.8.4a1.7 1.7 0 00-1.7-1L14.7 4h-3.4l-.7 1.9a1.7 1.7 0 00-1.7 1l-1.8-.4-1.6 2.8L6.6 11a1.7 1.7 0 000 2l-1.1 1.5 1.6 2.8 1.8-.4a1.7 1.7 0 001.7 1l.7 2h3.4l.7-1.9a1.7 1.7 0 001.7-1l1.8.4 1.6-2.8z"/></svg>',
  bell: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M6 8a6 6 0 1112 0c0 5 2 6 2 6H4s2-1 2-6z"/><path d="M10 21a2 2 0 004 0"/></svg>',
  logout: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M9 21H5a2 2 0 01-2-2V5a2 2 0 012-2h4"/><path d="M16 17l5-5-5-5"/><path d="M21 12H9"/></svg>',
};

const NAV_ITEMS = [
  { key: "dashboard", label: "Dashboard", href: "dashboard.html", icon: "dashboard" },
  { key: "buildings", label: "Buildings", href: "buildings.html", icon: "buildings" },
  { key: "monitoring", label: "Monitoring", href: "monitoring.html", icon: "monitoring" },
  { key: "alerts", label: "Alerts", href: "alerts.html", icon: "alerts" },
  { key: "analytics", label: "Analytics", href: "analytics.html", icon: "analytics" },
  { key: "reports", label: "Reports", href: "reports.html", icon: "reports" },
  { key: "devices", label: "Devices", href: "devices.html", icon: "monitoring" },
  { key: "users", label: "Users", href: "users.html", icon: "users" },
  { key: "settings", label: "Settings", href: "settings.html", icon: "settings" },
];

function renderLayout({ activePage, title, subtitle }) {
  Auth.requireLogin();
  const user = Auth.getUser() || { username: "admin", role: "admin" };

  const navHtml = NAV_ITEMS.map(item => `
    <a href="${item.href}" class="${item.key === activePage ? 'active' : ''}">
      ${ICONS[item.icon]}<span>${item.label}</span>
    </a>`).join("");

  document.body.insertAdjacentHTML("afterbegin", `
    <div class="app-shell">
      <aside class="sidebar">
        <div class="sidebar-brand">
          <span class="pulse-dot safe live"></span>
          <div>
            <div class="sidebar-brand-text">S-SHM</div>
            <div class="sidebar-brand-sub">STRUCTURAL HEALTH</div>
          </div>
        </div>
        <nav class="sidebar-nav">${navHtml}</nav>
        <div class="sidebar-footer">
          <div class="sidebar-user">
            <div class="sidebar-avatar">${(user.username || "A")[0].toUpperCase()}</div>
            <div>
              <div class="sidebar-user-name">${user.username}</div>
              <div class="sidebar-user-role">${user.role || "admin"}</div>
            </div>
            <button class="logout-btn" title="Log out" onclick="Auth.logout()">${ICONS.logout}</button>
          </div>
        </div>
      </aside>
      <div class="main">
        <div class="topbar">
          <div class="topbar-title">${title}<span>${subtitle || ""}</span></div>
          <div class="topbar-actions">
            <button class="bell-btn" id="bell-btn" title="Alerts">
              ${ICONS.bell}<span class="bell-dot" id="bell-dot" style="display:none;"></span>
            </button>
          </div>
        </div>
        <div class="content" id="page-content"></div>
      </div>
    </div>
  `);

  document.getElementById("bell-btn").onclick = () => window.location.href = "alerts.html";
  refreshBellIndicator();
}

async function refreshBellIndicator() {
  try {
    const alerts = await Api.getAlerts("?status=open");
    const dot = document.getElementById("bell-dot");
    if (dot) dot.style.display = alerts.length > 0 ? "block" : "none";
  } catch { /* silent -- bell is a nice-to-have, not critical path */ }
}

function statusBadge(status) {
  const s = (status || "SAFE").toUpperCase();
  const cls = s === "SAFE" ? "safe" : s === "WARNING" ? "warning" : "danger";
  return `<span class="badge ${cls}"><span class="pulse-dot ${cls}"></span>${s}</span>`;
}

function timeAgo(iso) {
  if (!iso) return "—";
  const diff = (Date.now() - new Date(iso).getTime()) / 1000;
  if (diff < 60) return "just now";
  if (diff < 3600) return `${Math.floor(diff / 60)}m ago`;
  if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`;
  return `${Math.floor(diff / 86400)}d ago`;
}
