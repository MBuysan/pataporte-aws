const API_URL = "http://localhost:8000";

async function apiRequest(method, endpoint, body = null, customOptions = {}) {

  const options = {
    method,
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${localStorage.getItem("access_token") || ""}`,
      ...(customOptions.headers || {})
    },
  };

  if (body) {
    options.body = JSON.stringify(body);
  }

  const response = await fetch(`${API_URL}${endpoint}`, options);

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