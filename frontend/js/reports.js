(async function () {
  document.getElementById("page-content").innerHTML =
    document.getElementById("content-template").innerHTML;

  try {
    const buildings = await Api.getBuildings();
    const select = document.getElementById("f-building");
    buildings.forEach(b => {
      const opt = document.createElement("option");
      opt.value = b.buildingID;
      opt.textContent = b.name || b.buildingID;
      select.appendChild(opt);
    });
  } catch { /* dropdown just falls back to "All buildings" */ }

  document.getElementById("download-btn").onclick = async () => {
    const buildingID = document.getElementById("f-building").value;
    const from = document.getElementById("f-from").value;
    const to = document.getElementById("f-to").value;
    const format = document.getElementById("f-format").value;
    const statusEl = document.getElementById("report-status");
    statusEl.textContent = "Generating report...";

    const params = new URLSearchParams();
    if (buildingID) params.set("buildingID", buildingID);
    if (from) params.set("from", from);
    if (to) params.set("to", to);
    params.set("token", Auth.getToken() || "");

    try {
      const url = Api.getReportUrl(format, params.toString());
      const link = document.createElement("a");
      link.href = url;
      link.download = `shm-report.${format === "excel" ? "xlsx" : format}`;
      document.body.appendChild(link);
      link.click();
      link.remove();
      statusEl.textContent = "Download started.";
    } catch (err) {
      statusEl.textContent = `Could not generate report: ${err.message}`;
    }
  };
})();
