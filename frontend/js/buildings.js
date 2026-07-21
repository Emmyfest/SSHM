(async function () {
  document.getElementById("page-content").innerHTML =
    document.getElementById("content-template").innerHTML;

  async function load() {
    const tbody = document.getElementById("buildings-table");
    try {
      const buildings = await Api.getBuildings();
      if (buildings.length === 0) {
        tbody.innerHTML = `<tr><td colspan="7" class="text-faint">No buildings registered yet. Add one to get started.</td></tr>`;
        return;
      }
      tbody.innerHTML = buildings.map(b => `
        <tr>
          <td><strong>${b.name || b.buildingID}</strong><div class="text-faint mono" style="font-size:11px;">${b.buildingID}</div></td>
          <td>${b.owner || "—"}</td>
          <td>${b.city || "—"}</td>
          <td>${statusBadge(b.status)}</td>
          <td class="mono">${b.health_index ?? "—"}</td>
          <td class="text-dim">${b.installation_date || "—"}</td>
          <td style="display:flex; gap:6px;">
            <a href="building-detail.html?id=${b.buildingID}" class="btn btn-sm">View</a>
            <button class="btn btn-sm btn-danger" onclick="deleteBuilding('${b.buildingID}')">Delete</button>
          </td>
        </tr>`).join("");
    } catch (err) {
      tbody.innerHTML = `<tr><td colspan="7" class="text-faint">Could not load buildings: ${err.message}</td></tr>`;
    }
  }

  window.deleteBuilding = async (id) => {
    if (!confirm(`Remove building ${id}? This cannot be undone.`)) return;
    try { await Api.deleteBuilding(id); load(); } catch (err) { alert(err.message); }
  };

  document.getElementById("add-btn").onclick = () => {
    document.getElementById("add-form-wrap").style.display = "block";
  };
  document.getElementById("cancel-btn").onclick = () => {
    document.getElementById("add-form-wrap").style.display = "none";
  };
  document.getElementById("save-btn").onclick = async () => {
    const payload = {
      buildingID: document.getElementById("f-id").value.trim(),
      name: document.getElementById("f-name").value.trim(),
      owner: document.getElementById("f-owner").value.trim(),
      city: document.getElementById("f-city").value.trim(),
      engineer: document.getElementById("f-engineer").value.trim(),
      installation_date: document.getElementById("f-install").value,
      gps_lat: parseFloat(document.getElementById("f-lat").value) || null,
      gps_lng: parseFloat(document.getElementById("f-lng").value) || null,
    };
    if (!payload.buildingID) { alert("Building ID is required"); return; }
    try {
      await Api.createBuilding(payload);
      document.getElementById("add-form-wrap").style.display = "none";
      load();
    } catch (err) { alert(err.message); }
  };

  load();
})();
