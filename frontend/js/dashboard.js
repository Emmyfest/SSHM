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
})();
