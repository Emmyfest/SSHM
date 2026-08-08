(async function () {
  document.getElementById("page-content").innerHTML =
    document.getElementById("content-template").innerHTML;

  let buildings = [];
  try {
    buildings = await Api.getBuildings();
  } catch (err) {
    document.getElementById("buildings-table").innerHTML =
      `<tr><td colspan="8" class="text-faint">Could not load buildings: ${err.message}</td></tr>`;
    return;
  }

  const counts = { SAFE: 0, WARNING: 0, CRITICAL: 0 };
  buildings.forEach(b => { counts[(b.status || "SAFE").toUpperCase()] = (counts[(b.status || "SAFE").toUpperCase()] || 0) + 1; });

  document.getElementById("kpi-total").textContent = buildings.length;
  document.getElementById("kpi-safe").textContent = counts.SAFE || 0;
  document.getElementById("kpi-warning").textContent = counts.WARNING || 0;
  document.getElementById("kpi-danger").textContent = counts.CRITICAL || 0;

  // ---- Map ----
  const map = L.map("map", { zoomControl: true, attributionControl: false }).setView([9.0765, 7.3986], 6);
  L.tileLayer("https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png", { maxZoom: 19 }).addTo(map);

  const statusColor = { SAFE: "#10B981", WARNING: "#F59E0B", CRITICAL: "#EF4444" };
  buildings.forEach(b => {
    if (b.gps_lat == null || b.gps_lng == null) return;
    const color = statusColor[(b.status || "SAFE").toUpperCase()] || statusColor.SAFE;
    const marker = L.circleMarker([b.gps_lat, b.gps_lng], {
      radius: 9, fillColor: color, color: color, weight: 2, fillOpacity: 0.55,
    }).addTo(map);
    marker.bindPopup(`<b>${b.name || b.buildingID}</b><br>${b.city || ""}<br>Status: ${b.status}`);
    marker.on("click", () => window.location.href = `building-detail.html?id=${b.buildingID}`);
  });

  // ---- Buildings table ----
  const tbody = document.getElementById("buildings-table");
  if (buildings.length === 0) {
    tbody.innerHTML = `<tr><td colspan="8" class="text-faint">No buildings registered yet.</td></tr>`;
  } else {
    tbody.innerHTML = buildings.map(b => `
      <tr>
        <td><strong>${b.name || b.buildingID}</strong><div class="text-faint mono" style="font-size:11px;">${b.buildingID}</div></td>
        <td>${b.city || "—"}</td>
        <td>${statusBadge(b.status)}</td>
        <td class="mono">${b.health_index ?? "—"}</td>
        <td class="mono">${b.strain ?? "—"}</td>
        <td class="mono">${b.tilt ?? "—"}&deg;</td>
        <td class="mono">${b.vibration ?? "—"}g</td>
        <td><a href="building-detail.html?id=${b.buildingID}" class="btn btn-sm">Details</a></td>
      </tr>`).join("");
  }

  // ---- Recent alerts ----
  try {
    const alerts = await Api.getAlerts("?limit=5");
    const el = document.getElementById("recent-alerts");
    if (alerts.length === 0) {
      el.innerHTML = `<div class="empty-state">No alerts in the last 24 hours.</div>`;
    } else {
      el.innerHTML = `<ul>` + alerts.map(a => `
        <li style="padding:10px 0; border-bottom:1px solid var(--border);">
          <div style="display:flex; justify-content:space-between;">
            <strong style="font-size:13px;">${a.building_name || a.buildingID}</strong>
            ${statusBadge(a.severity)}
          </div>
          <div class="text-dim" style="font-size:12.5px; margin-top:3px;">${a.reason}</div>
          <div class="text-faint" style="font-size:11.5px; margin-top:3px;">${timeAgo(a.timestamp)}</div>
        </li>`).join("") + `</ul>`;
    }
  } catch (err) {
    document.getElementById("recent-alerts").innerHTML = `<div class="text-faint">Could not load alerts.</div>`;
  }

  // ---- Crack reports (Raspberry Pi camera feed) ----
  initCrackReports();
})();

let crackReports = [];
let crackSeverityFilter = "all";

function crackSeverityOf(r) {
  return (r.summary && (r.summary.max_severity || r.summary.severity)) || "none";
}
function crackCountOf(r) {
  return (r.summary && r.summary.crack_count) ?? (r.cracks ? r.cracks.length : 0);
}
function crackMaxWidth(r) {
  if (!r.cracks || !r.cracks.length) return null;
  const widths = r.cracks.map(c => c.width_mm ?? c.width_px ?? 0);
  const unit = r.cracks[0].width_mm != null ? "mm" : "px";
  return `${Math.max(...widths)} ${unit}`;
}
function crackSeverityBadgeClass(sev) {
  return sev === "severe" ? "danger" : sev === "moderate" ? "warning" : "safe";
}

async function initCrackReports() {
  const grid = document.getElementById("crack-grid");

  try {
    crackReports = await Api.getCrackReports(50);
    crackReports.sort((a, b) => new Date(b.timestamp) - new Date(a.timestamp));
    renderCrackGrid();
  } catch (err) {
    grid.innerHTML = `<div class="empty-state">Could not load crack reports: ${err.message}</div>`;
  }

  document.querySelectorAll("#crack-severity-tabs .tab").forEach(tab => {
    tab.addEventListener("click", () => {
      document.querySelectorAll("#crack-severity-tabs .tab").forEach(t => t.classList.remove("active"));
      tab.classList.add("active");
      crackSeverityFilter = tab.dataset.severity;
      renderCrackGrid();
    });
  });

  document.getElementById("crack-modal-close").onclick = closeCrackModal;
  document.getElementById("crack-modal-overlay").addEventListener("click", (e) => {
    if (e.target.id === "crack-modal-overlay") closeCrackModal();
  });
  document.addEventListener("keydown", (e) => { if (e.key === "Escape") closeCrackModal(); });

  connectCrackLiveFeed();
}

function renderCrackGrid() {
  const grid = document.getElementById("crack-grid");
  const filtered = crackSeverityFilter === "all"
    ? crackReports
    : crackReports.filter(r => crackSeverityOf(r) === crackSeverityFilter);

  if (filtered.length === 0) {
    grid.innerHTML = `<div class="empty-state">No crack reports${crackSeverityFilter === "all" ? " yet" : " match this filter"}.</div>`;
    return;
  }

  grid.innerHTML = filtered.map(r => {
    const sev = crackSeverityOf(r);
    const imgUrl = Api.getCrackReportImageUrl(r.image_url);
    const media = imgUrl
      ? `<img src="${imgUrl}" alt="Crack report" loading="lazy" onerror="this.parentElement.innerHTML='<div class=&quot;crack-no-image&quot;>No image</div>'">`
      : `<div class="crack-no-image">No image</div>`;
    return `
      <div class="crack-card" data-id="${r.id || ""}">
        <div class="crack-card-media">
          <span class="crack-severity-pill ${sev}">${sev}</span>
          ${media}
        </div>
        <div class="crack-card-body">
          <strong style="font-size:13px;">${r.device_id || "Unknown device"}</strong>
          <div class="text-faint mono" style="font-size:11.5px; margin-top:2px;">${timeAgo(r.timestamp)}</div>
          <div class="text-dim" style="font-size:12.5px; margin-top:4px;">${crackCountOf(r)} crack(s) detected</div>
        </div>
      </div>`;
  }).join("");

  grid.querySelectorAll(".crack-card").forEach(card => {
    card.addEventListener("click", () => {
      const report = crackReports.find(r => (r.id || "") === card.dataset.id);
      if (report) openCrackModal(report);
    });
  });
}

function openCrackModal(r) {
  const sev = crackSeverityOf(r);
  const imgUrl = Api.getCrackReportImageUrl(r.image_url);
  const img = document.getElementById("crack-modal-img");
  img.src = imgUrl || "";
  img.style.display = imgUrl ? "block" : "none";

  document.getElementById("crack-modal-badge").innerHTML =
    `<span class="badge ${crackSeverityBadgeClass(sev)}"><span class="pulse-dot ${crackSeverityBadgeClass(sev)}"></span>${sev.toUpperCase()}</span>`;
  document.getElementById("crack-modal-device").textContent = r.device_id || "—";
  document.getElementById("crack-modal-building").textContent = r.buildingID || r.building_name || "—";
  document.getElementById("crack-modal-time").textContent = r.timestamp ? new Date(r.timestamp).toLocaleString() : "—";
  document.getElementById("crack-modal-count").textContent = crackCountOf(r);
  document.getElementById("crack-modal-width").textContent = crackMaxWidth(r) || "—";

  document.getElementById("crack-modal-overlay").classList.add("open");
}

function closeCrackModal() {
  document.getElementById("crack-modal-overlay").classList.remove("open");
}

function connectCrackLiveFeed() {
  try {
    const ws = new WebSocket(getLiveSocketUrl());
    ws.onopen = () => { document.getElementById("crack-live-indicator").style.display = "inline-flex"; };
    ws.onclose = () => { document.getElementById("crack-live-indicator").style.display = "none"; };
    ws.onmessage = (event) => {
      let data;
      try { data = JSON.parse(event.data); } catch { return; }
      if (data.type === "crack_report") {
        crackReports.unshift(data);
        renderCrackGrid();
      }
    };
  } catch { /* live updates optional -- history already loaded */ }
}
