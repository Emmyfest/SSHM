(async function () {
  document.getElementById("page-content").innerHTML =
    document.getElementById("content-template").innerHTML;

  const params = new URLSearchParams(window.location.search);
  const id = params.get("id");
  let chart = null;

  if (!id) {
    document.getElementById("building-title").textContent = "No building selected";
    return;
  }

  async function loadInfo() {
    try {
      const b = await Api.getBuilding(id);
      document.getElementById("building-title").textContent = `${b.name || b.buildingID} · ${b.city || ""}`;
      document.getElementById("building-status").innerHTML = statusBadge(b.status);
      document.getElementById("d-health").textContent = b.health_index ?? "—";
      document.getElementById("d-strain").textContent = b.strain ?? "—";
      document.getElementById("d-tilt").textContent = (b.tilt ?? "—") + "°";
      document.getElementById("d-vibration").textContent = (b.vibration ?? "—") + "g";
      document.getElementById("d-battery").textContent = (b.battery ?? "—") + "V";
      document.getElementById("d-gsm").textContent = b.gsm_signal ?? "—";
      document.getElementById("d-owner").textContent = b.owner || "—";
      document.getElementById("d-engineer").textContent = b.engineer || "—";
      document.getElementById("d-install").textContent = b.installation_date || "—";
      document.getElementById("d-firmware").textContent = b.firmware_version || "—";
    } catch (err) {
      document.getElementById("building-title").textContent = `Could not load: ${err.message}`;
    }
  }

  async function loadTrend(range) {
    try {
      const history = await Api.getBuildingHistory(id, range);
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

  document.querySelectorAll("#range-tabs .tab").forEach(tab => {
    tab.addEventListener("click", () => {
      document.querySelectorAll("#range-tabs .tab").forEach(t => t.classList.remove("active"));
      tab.classList.add("active");
      loadTrend(tab.dataset.range);
    });
  });

  loadInfo();
  loadTrend("24h");
})();
