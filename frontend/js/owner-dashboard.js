(async function () {
  document.getElementById("page-content").innerHTML =
    document.getElementById("content-template").innerHTML;

  const user = Auth.getUser();
  if (!user || user.role !== "owner") {
    // Safety net -- if a non-owner somehow lands here, send them to the admin dashboard instead
    window.location.href = "dashboard.html";
    return;
  }

  let buildingID = null;
  let chart = null;

  async function loadInfo() {
    try {
      // The backend already filters this to just the owner's one building
      const buildings = await Api.getBuildings();
      const b = buildings[0];
      if (!b) {
        document.getElementById("building-title").textContent = "No building is linked to your account yet.";
        return;
      }
      buildingID = b.buildingID;

      document.getElementById("building-title").textContent = `${b.name || b.buildingID} · ${b.city || ""}`;
      document.getElementById("building-status").innerHTML = statusBadge(b.status);
      document.getElementById("d-health").textContent = b.health_index ?? "—";
      document.getElementById("d-strain").textContent = b.strain ?? "—";
      document.getElementById("d-tilt").textContent = (b.tilt ?? "—") + "°";
      document.getElementById("d-vibration").textContent = (b.vibration ?? "—") + "g";
      document.getElementById("d-last-reading").textContent = timeAgo(b.timestamp);

      loadTrend("24h");
    } catch (err) {
      document.getElementById("building-title").textContent = `Could not load: ${err.message}`;
    }
  }

  async function loadTrend(range) {
    if (!buildingID) return;
    try {
      const history = await Api.getBuildingHistory(buildingID, range);
      const labels = history.map(h => new Date(h.timestamp).toLocaleString());
      const ctx = document.getElementById("trend-chart").getContext("2d");
      if (chart) chart.destroy();
      chart = new Chart(ctx, {
        type: "line",
        data: {
          labels,
          datasets: [
            { label: "Strain", data: history.map(h => h.strain), borderColor: "#3B82F6", tension: 0.3, pointRadius: 0 },
            { label: "Tilt (°)", data: history.map(h => h.tilt), borderColor: "#F59E0B", tension: 0.3, pointRadius: 0 },
            { label: "Vibration (g)", data: history.map(h => h.vibration), borderColor: "#10B981", tension: 0.3, pointRadius: 0 },
          ],
        },
        options: {
          responsive: true,
          interaction: { mode: "index", intersect: false },
          plugins: { legend: { labels: { color: "#94A3B8" } } },
          scales: {
            x: { ticks: { color: "#64748B", maxTicksLimit: 8 }, grid: { color: "#2C3B52" } },
            y: { ticks: { color: "#64748B" }, grid: { color: "#2C3B52" } },
          },
        },
      });
    } catch (err) {
      console.error("Trend load failed:", err.message);
    }
  }

  async function loadAlerts() {
    try {
      // Backend auto-scopes this to the owner's building too
      const alerts = await Api.getAlerts("?limit=5");
      const el = document.getElementById("recent-alerts");
      if (alerts.length === 0) {
        el.innerHTML = `<div class="empty-state">No alerts for your building.</div>`;
      } else {
        el.innerHTML = `<ul>` + alerts.map(a => `
          <li style="padding:10px 0; border-bottom:1px solid var(--border);">
            <div style="display:flex; justify-content:space-between;">
              <strong style="font-size:13px;">${a.reason}</strong>
              ${statusBadge(a.severity)}
            </div>
            <div class="text-faint" style="font-size:11.5px; margin-top:3px;">${timeAgo(a.timestamp)}</div>
          </li>`).join("") + `</ul>`;
      }
    } catch (err) {
      document.getElementById("recent-alerts").innerHTML = `<div class="text-faint">Could not load alerts.</div>`;
    }
  }

  document.querySelectorAll("#range-tabs .tab").forEach(tab => {
    tab.addEventListener("click", () => {
      document.querySelectorAll("#range-tabs .tab").forEach(t => t.classList.remove("active"));
      tab.classList.add("active");
      loadTrend(tab.dataset.range);
    });
  });

  loadInfo();
  loadAlerts();
})();
