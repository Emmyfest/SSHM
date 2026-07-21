(async function () {
  document.getElementById("page-content").innerHTML =
    document.getElementById("content-template").innerHTML;

  const chartColors = { grid: "#2C3B52", ticks: "#64748B", legend: "#94A3B8" };
  let healthChart = null;

  async function loadHealthTrend(range) {
    try {
      const data = await Api.getAnalytics(range);
      const ctx = document.getElementById("health-chart").getContext("2d");
      if (healthChart) healthChart.destroy();
      healthChart = new Chart(ctx, {
        type: "line",
        data: {
          labels: data.timeline.map(p => new Date(p.timestamp).toLocaleString()),
          datasets: [{ label: "Avg health index", data: data.timeline.map(p => p.avg_health), borderColor: "#3B82F6", backgroundColor: "rgba(59,130,246,0.1)", fill: true, tension: 0.3, pointRadius: 0 }],
        },
        options: {
          responsive: true,
          plugins: { legend: { labels: { color: chartColors.legend } } },
          scales: {
            x: { ticks: { color: chartColors.ticks, maxTicksLimit: 8 }, grid: { color: chartColors.grid } },
            y: { min: 0, max: 100, ticks: { color: chartColors.ticks }, grid: { color: chartColors.grid } },
          },
        },
      });

      new Chart(document.getElementById("status-chart").getContext("2d"), {
        type: "doughnut",
        data: {
          labels: ["Safe", "Warning", "Critical"],
          datasets: [{ data: [data.status_counts.SAFE || 0, data.status_counts.WARNING || 0, data.status_counts.CRITICAL || 0], backgroundColor: ["#10B981", "#F59E0B", "#EF4444"], borderWidth: 0 }],
        },
        options: { plugins: { legend: { position: "bottom", labels: { color: chartColors.legend } } } },
      });

      new Chart(document.getElementById("alerts-chart").getContext("2d"), {
        type: "bar",
        data: {
          labels: data.alerts_by_building.map(b => b.name),
          datasets: [{ label: "Alerts", data: data.alerts_by_building.map(b => b.count), backgroundColor: "#3B82F6" }],
        },
        options: {
          plugins: { legend: { display: false } },
          scales: {
            x: { ticks: { color: chartColors.ticks }, grid: { display: false } },
            y: { ticks: { color: chartColors.ticks }, grid: { color: chartColors.grid } },
          },
        },
      });
    } catch (err) {
      console.error("Analytics load failed:", err.message);
    }
  }

  document.querySelectorAll("#range-tabs .tab").forEach(tab => {
    tab.addEventListener("click", () => {
      document.querySelectorAll("#range-tabs .tab").forEach(t => t.classList.remove("active"));
      tab.classList.add("active");
      loadHealthTrend(tab.dataset.range);
    });
  });

  loadHealthTrend("24h");
})();
