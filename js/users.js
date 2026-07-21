(function () {
  document.getElementById("page-content").innerHTML =
    document.getElementById("content-template").innerHTML;

  async function load() {
    const tbody = document.getElementById("users-table");
    try {
      const users = await Api.getUsers();
      tbody.innerHTML = users.map(u => `
        <tr>
          <td><strong>${u.username}</strong></td>
          <td class="text-dim" style="text-transform:capitalize;">${u.role}</td>
          <td class="text-faint">${u.created_at ? new Date(u.created_at).toLocaleDateString() : "—"}</td>
          <td><button class="btn btn-sm btn-danger" onclick="removeUser('${u._id}')">Remove</button></td>
        </tr>`).join("");
    } catch (err) {
      tbody.innerHTML = `<tr><td colspan="4" class="text-faint">Could not load users: ${err.message}</td></tr>`;
    }
  }

  window.removeUser = async (id) => {
    if (!confirm("Remove this user?")) return;
    try { await Api.deleteUser(id); load(); } catch (err) { alert(err.message); }
  };

  document.getElementById("add-btn").onclick = () => document.getElementById("add-form-wrap").style.display = "block";
  document.getElementById("cancel-btn").onclick = () => document.getElementById("add-form-wrap").style.display = "none";
  document.getElementById("save-btn").onclick = async () => {
    const payload = {
      username: document.getElementById("f-username").value.trim(),
      password: document.getElementById("f-password").value,
      role: document.getElementById("f-role").value,
    };
    if (!payload.username || !payload.password) { alert("Username and password are required"); return; }
    try {
      await Api.createUser(payload);
      document.getElementById("add-form-wrap").style.display = "none";
      load();
    } catch (err) { alert(err.message); }
  };

  load();
})();
