(function () {
  document.getElementById("page-content").innerHTML =
    document.getElementById("content-template").innerHTML;

  const rowsByBuilding = new Map();
  let pollTimer = null;
  let socket = null;

  function render() {
    const tbody = document.getElementById("live-table");
    const rows = Array.from(rowsByBuilding.values());
    if (rows.length === 0) {
      tbody.innerHTML = `<tr><td colspan="8" class="text-faint">No live readings yet -- waiting on devices to report in.</td></tr>`;
      return;
    }
    tbody.innerHTML = rows.map(r => `
      <tr>
        <td><strong>${r.name || r.buildingID}</strong></td>
        <td>${statusBadge(r.status)}</td>
        <td class="mono">${r.strain ?? "—"}</td>
        <td class="mono">${r.tilt ?? "—"}&deg;</td>
        <td class="mono">${r.vibration ?? "—"}g</td>
        <td class="mono">${r.battery ?? "—"}V</td>
        <td class="mono">${r.gsm_signal ?? "—"}</td>
        <td class="text-faint">${timeAgo(r.timestamp)}</td>
      </tr>`).join("");
  }

  function setLiveIndicator(connected) {
    const label = document.getElementById("last-update");
    label.textContent = connected
      ? ` · live · updated ${new Date().toLocaleTimeString()}`
      : ` · reconnecting... last updated ${new Date().toLocaleTimeString()}`;
  }

  async function initialLoad() {
    try {
      const rows = await Api.getLiveReadings();
      rows.forEach(r => rowsByBuilding.set(r.buildingID, r));
      render();
    } catch (err) {
      document.getElementById("live-table").innerHTML =
        `<tr><td colspan="8" class="text-faint">Could not load live readings: ${err.message}</td></tr>`;
    }
  }

  // ---- Polling fallback (only used if the WebSocket can't connect) ----
  function startPollingFallback() {
    if (pollTimer) return;
    pollTimer = setInterval(async () => {
      try {
        const rows = await Api.getLiveReadings();
        rows.forEach(r => rowsByBuilding.set(r.buildingID, r));
        render();
        setLiveIndicator(false);
      } catch { /* keep retrying silently */ }
    }, 5000);
  }

  function stopPollingFallback() {
    if (pollTimer) { clearInterval(pollTimer); pollTimer = null; }
  }

  // ---- WebSocket live push ----
  function connectSocket() {
    socket = new WebSocket(getLiveSocketUrl());

    socket.onopen = () => {
      stopPollingFallback();
      setLiveIndicator(true);
    };

    socket.onmessage = (event) => {
      try {
        const reading = JSON.parse(event.data);
        rowsByBuilding.set(reading.buildingID, reading);
        render();
        setLiveIndicator(true);
      } catch { /* ignore malformed messages */ }
    };

    socket.onclose = () => {
      setLiveIndicator(false);
      startPollingFallback();        // don't leave the dashboard silently stale
      setTimeout(connectSocket, 3000); // keep trying to restore the live connection
    };

    socket.onerror = () => {
      socket.close();
    };
  }

  initialLoad();
  connectSocket();

  window.addEventListener("beforeunload", () => {
    if (socket) socket.close();
    stopPollingFallback();
  });
})();
