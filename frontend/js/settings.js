(async function () {
  document.getElementById("page-content").innerHTML =
    document.getElementById("content-template").innerHTML;

  const statusEl = document.getElementById("settings-status");
  const user = Auth.getUser();
  if (user) document.getElementById("s-username").value = user.username;

  try {
    const settings = await Api.getSettings();
    document.getElementById("s-strain").value = settings.strain_threshold ?? 1000;
    document.getElementById("s-vibration").value = settings.vibration_threshold ?? 1.5;
    document.getElementById("s-tilt").value = settings.tilt_threshold ?? 5;
    document.getElementById("s-battery").value = settings.battery_threshold ?? 3.3;
  } catch { /* defaults already shown in the inputs' placeholders */ }

  document.getElementById("save-thresholds").onclick = async () => {
    try {
      await Api.updateSettings({
        strain_threshold: parseFloat(document.getElementById("s-strain").value),
        vibration_threshold: parseFloat(document.getElementById("s-vibration").value),
        tilt_threshold: parseFloat(document.getElementById("s-tilt").value),
        battery_threshold: parseFloat(document.getElementById("s-battery").value),
      });
      statusEl.textContent = "Thresholds saved.";
    } catch (err) {
      statusEl.textContent = `Could not save: ${err.message}`;
    }
  };

  document.getElementById("save-profile").onclick = async () => {
    statusEl.textContent = "Profile updates go through the Users page for other accounts, or contact an admin to change your own password.";
  };
})();
