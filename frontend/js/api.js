// Central API client. Set API_BASE to your deployed FastAPI backend URL.
const API_BASE = window.location.hostname === "localhost" || window.location.hostname === "127.0.0.1"
  ? "http://localhost:8000/api"
  : "https://sshm-3k4s.onrender.com/api";

function getLiveSocketUrl() {
  const wsBase = API_BASE.replace(/^http/, "ws").replace(/\/api$/, "");
  return `${wsBase}/ws/live?token=${encodeURIComponent(Auth.getToken() || "")}`;
}

const Auth = {
  getToken() { return localStorage.getItem("shm_token"); },
  setToken(t) { localStorage.setItem("shm_token", t); },
  getUser() { try { return JSON.parse(localStorage.getItem("shm_user")); } catch { return null; } },
  setUser(u) { localStorage.setItem("shm_user", JSON.stringify(u)); },
  clear() { localStorage.removeItem("shm_token"); localStorage.removeItem("shm_user"); },
  requireLogin() {
    if (!this.getToken()) window.location.href = "index.html";
  },
  logout() { this.clear(); window.location.href = "index.html"; },
};

async function apiRequest(path, options = {}) {
  const headers = { "Content-Type": "application/json", ...(options.headers || {}) };
  const token = Auth.getToken();
  if (token) headers["Authorization"] = `Bearer ${token}`;

  const res = await fetch(`${API_BASE}${path}`, { ...options, headers });

  if (res.status === 401) {
    Auth.clear();
    window.location.href = "index.html";
    throw new Error("Unauthorized");
  }
  if (!res.ok) {
    let detail = "Request failed";
    try { detail = (await res.json()).detail || detail; } catch {}
    throw new Error(detail);
  }
  const contentType = res.headers.get("content-type") || "";
  if (contentType.includes("application/json")) return res.json();
  return res.blob();
}

const Api = {
  login: (username, password) =>
    apiRequest("/auth/login", { method: "POST", body: JSON.stringify({ username, password }) }),

  getBuildings: () => apiRequest("/buildings"),
  getBuilding: (id) => apiRequest(`/buildings/${id}`),
  getBuildingHistory: (id, range) => apiRequest(`/buildings/${id}/history?range=${range}`),
  createBuilding: (data) => apiRequest("/buildings", { method: "POST", body: JSON.stringify(data) }),
  updateBuilding: (id, data) => apiRequest(`/buildings/${id}`, { method: "PUT", body: JSON.stringify(data) }),
  deleteBuilding: (id) => apiRequest(`/buildings/${id}`, { method: "DELETE" }),

  getLiveReadings: () => apiRequest("/readings/live"),

  getAlerts: (params = "") => apiRequest(`/alerts${params}`),
  resolveAlert: (id) => apiRequest(`/alerts/${id}/resolve`, { method: "PATCH" }),

  getDevices: () => apiRequest("/devices"),
  createDevice: (data) => apiRequest("/devices", { method: "POST", body: JSON.stringify(data) }),
  updateDevice: (id, data) => apiRequest(`/devices/${id}`, { method: "PUT", body: JSON.stringify(data) }),
  deleteDevice: (id) => apiRequest(`/devices/${id}`, { method: "DELETE" }),

  getAnalytics: (range) => apiRequest(`/analytics?range=${range}`),

  getUsers: () => apiRequest("/users"),
  createUser: (data) => apiRequest("/users", { method: "POST", body: JSON.stringify(data) }),
  deleteUser: (id) => apiRequest(`/users/${id}`, { method: "DELETE" }),

  getReportUrl: (format, params) => `${API_BASE}/reports/${format}?${params}`,

  getSettings: () => apiRequest("/settings"),
  updateSettings: (data) => apiRequest("/settings", { method: "PUT", body: JSON.stringify(data) }),
};
