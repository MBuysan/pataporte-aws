document.addEventListener("DOMContentLoaded", async () => {
  await verificarConexionAPI();
  inicializarPantallaLogin();
});

// Verifica que la API esté disponible al arrancar
async function verificarConexionAPI() {
  try {
    await api.get("/");
    console.log("API conectada correctamente.");
  } catch (error) {
    console.error("No se pudo conectar con la API:", error.message);
  }
}

// Inicializa la pantalla de login solo si existe el formulario
function inicializarPantallaLogin() {
  const loginForm = document.getElementById("loginForm");
  const identificadorInput = document.getElementById("identificador");
  const passwordInput = document.getElementById("password");
  const errorMessage = document.getElementById("error");

  if (!loginForm || !identificadorInput || !passwordInput || !errorMessage) {
    return;
  }

  loginForm.addEventListener("submit", async (event) => {
    event.preventDefault();

    const identificador = identificadorInput.value.trim();
    const password = passwordInput.value.trim();

    errorMessage.textContent = "";

    if (!identificador || !password) {
      errorMessage.textContent = "Completá todos los campos.";
      return;
    }

    try {
      const response = await api.post("/auth/login", {
        identificador,
        password,
      });

      localStorage.setItem("access_token", response.access_token);
      const tutor = await api.get(`/tutores/${response.user.id_tutor}`);
      localStorage.setItem("tutor", JSON.stringify(tutor));

      window.location.href = "dashboard.html";
    } catch (error) {
      console.error("Error al iniciar sesión:", error.message);
      errorMessage.textContent = "Credenciales inválidas.";
    }
  });
}