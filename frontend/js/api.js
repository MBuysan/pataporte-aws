const API_URL = "http://localhost:8000";

async function apiRequest(method, endpoint, body = null) {
  const options = {
    method,
    headers: {
      "Content-Type": "application/json",
      // reemplazar por extracción desde JWT cuando esté implementado
      "X-Veterinario-Id": localStorage.getItem("veterinario_id") ?? "",
    },
  };
  if (body) options.body = JSON.stringify(body);

  const response = await fetch(`${API_URL}${endpoint}`, options);

  if (!response.ok) {
    const error = await response.json().catch(() => ({}));
    throw new Error(error.detail || `Error ${response.status}`);
  }

  if (response.status === 204) return null;
  return response.json();
}

const api = {
  get:    (endpoint)       => apiRequest("GET",    endpoint),
  post:   (endpoint, body) => apiRequest("POST",   endpoint, body),
  put:    (endpoint, body) => apiRequest("PUT",    endpoint, body),
  patch:  (endpoint, body) => apiRequest("PATCH",  endpoint, body),
  delete: (endpoint)       => apiRequest("DELETE", endpoint),
};


// Funcion central para hablar con FastAPI. Todo el frontend usa este archivo para hacer pedidos HTTP.
// Maneja errores en un solo lugar. Si la API devuelve error, lo lanza como excepcion.