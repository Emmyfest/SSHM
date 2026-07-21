(function () {
  document.getElementById("page-content").innerHTML =
    document.getElementById("content-template").innerHTML;

  async function load() {
    const tbody = document.getElementById("devices-table");
    try {
      const devices = await Api.getDevices();
      if (devices.length === 0) {
        tbody.innerHTML = `<tr><td colspan="7" class="text-faint">No devices registered yet.</td></tr>`;
        return;
      }
      tbody.innerHTML = devices.map(d => `
        <tr>
          <td class="mono">${d.device_id}</td>
          <td>${d.buildingID}</td>
          <td class="mono">${d.firmware_version || "—"}</td>
          <td class="mono">${d.battery ?? "—"}V</td>
          <td class="mono">${d.gsm_signal ?? "—"}</td>
          <td class="text-faint">${timeAgo(d.last_seen)}</td>
          <td><button class="btn btn-sm btn-danger" onclick="removeDevice('${d._id}')">Remove</button></td>
        </tr>`).join("");
    } catch (err) {
      tbody.innerHTML = `<tr><td colspan="7" class="text-faint">Could not load devices: ${err.message}</td></tr>`;
    }
  }

  window.removeDevice = async (id) => {
    if (!confirm("Remove this device?")) return;
    try { await Api.deleteDevice(id); load(); } catch (err) { alert(err.message); }
  };

  document.getElementById("add-btn").onclick = () => document.getElementById("add-form-wrap").style.display = "block";
  document.getElementById("cancel-btn").onclick = () => document.getElementById("add-form-wrap").style.display = "none";
  document.getElementById("save-btn").onclick = async () => {
    const payload = {
      device_id: document.getElementById("f-device-id").value.trim(),
      buildingID: document.getElementById("f-building-id").value.trim(),
      firmware_version: document.getElementById("f-firmware").value.trim(),
    };
    if (!payload.device_id || !payload.buildingID) { alert("Device ID and building ID are required"); return; }
    try {
      await Api.createDevice(payload);
      document.getElementById("add-form-wrap").style.display = "none";
      load();
    } catch (err) { alert(err.message); }
  };

  load();
})();
