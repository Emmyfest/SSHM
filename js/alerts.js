(function () {
  document.getElementById("page-content").innerHTML =
    document.getElementById("content-template").innerHTML;

  async function load(filter = "") {
    const tbody = document.getElementById("alerts-table");
    try {
      const alerts = await Api.getAlerts(filter ? `?status=${filter}` : "");
      if (alerts.length === 0) {
        tbody.innerHTML = `<tr><td colspan="6" class="text-faint">No alerts to show.</td></tr>`;
        return;
      }
      tbody.innerHTML = alerts.map(a => `
        <tr>
          <td><strong>${a.building_name || a.buildingID}</strong></td>
          <td>${statusBadge(a.severity)}</td>
          <td class="text-dim">${a.reason}</td>
          <td class="text-faint">${timeAgo(a.timestamp)}</td>
          <td>${a.status === "resolved" ? '<span class="text-dim">Resolved</span>' : '<span style="color:var(--warning);">Open</span>'}</td>
          <td>${a.status !== "resolved" ? `<button class="btn btn-sm" onclick="resolve('${a._id}')">Mark resolved</button>` : ""}</td>
        </tr>`).join("");
    } catch (err) {
      tbody.innerHTML = `<tr><td colspan="6" class="text-faint">Could not load alerts: ${err.message}</td></tr>`;
    }
  }

  window.resolve = async (id) => {
    try { await Api.resolveAlert(id); load(currentFilter); } catch (err) { alert(err.message); }
  };

  let currentFilter = "";
  document.querySelectorAll("#filter-tabs .tab").forEach(tab => {
    tab.addEventListener("click", () => {
      document.querySelectorAll("#filter-tabs .tab").forEach(t => t.classList.remove("active"));
      tab.classList.add("active");
      currentFilter = tab.dataset.filter;
      load(currentFilter);
    });
  });

  load();
})();
