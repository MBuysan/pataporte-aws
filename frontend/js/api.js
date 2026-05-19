const API_URL = "http://localhost:8000";

async function apiRequest(method, endpoint, body = null, customOptions = {}) {

  const token = localStorage.getItem("access_token");

  const options = {
    method,
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...(customOptions.headers || {})
    },
  };

  if (body) {
    options.body = JSON.stringify(body);
  }

  const response = await fetch(`${API_URL}${endpoint}`, options);
  
  //Si el token expiró
  if (response.status === 401 || response.status === 403) {

    const rol = localStorage.getItem("rol");

    localStorage.removeItem("access_token");
    localStorage.removeItem("user");
    localStorage.removeItem("rol");
    localStorage.removeItem("veterinaria_id");
    localStorage.removeItem("tutor");

    const paginaActual = window.location.pathname;

    // Evitar redirect infinito
    if (
      !paginaActual.includes("login.html") &&
      !paginaActual.includes("login-veterinaria.html")
    ) {

      alert("Tu sesión expiró. Volvé a iniciar sesión.");

      if (rol === "veterinaria") {
        window.location.href = "login-veterinaria.html";
      } else {
        window.location.href = "login.html";
      }
    }

    return;
  }

  if (!response.ok) {
    const error = await response.json().catch(() => ({}));

    console.error("BACKEND ERROR:", error);

    throw new Error(error.detail || "Ocurrió un error");
  }

  if (response.status === 204) return null;

  return response.json();
}

const api = {
  get:    (endpoint, options)       => apiRequest("GET", endpoint, null, options),

  post:   (endpoint, body, options) =>
    apiRequest("POST", endpoint, body, options),

  put:    (endpoint, body, options) =>
    apiRequest("PUT", endpoint, body, options),

  patch:  (endpoint, body, options) =>
    apiRequest("PATCH", endpoint, body, options),

  delete: (endpoint, options) =>
    apiRequest("DELETE", endpoint, null, options),
};