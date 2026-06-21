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

  const togglePassword = document.getElementById("togglePassword");
  const eyeIcon = document.getElementById("eyeIcon");

  if (!loginForm || !identificadorInput || !passwordInput || !errorMessage) {
    return;
  }

  // Mostrar / ocultar contraseña
  if (togglePassword && eyeIcon) {
    togglePassword.addEventListener("click", () => {
      const mostrando = passwordInput.type === "password";

      passwordInput.type = mostrando ? "text" : "password";

      eyeIcon.innerHTML = mostrando
        ? `
          <path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19m-6.72-1.07a3 3 0 1 1-4.24-4.24"></path>
          <line x1="1" y1="1" x2="23" y2="23"></line>
        `
        : `
          <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"></path>
          <circle cx="12" cy="12" r="3"></circle>
        `;

      togglePassword.setAttribute(
        "aria-label",
        mostrando ? "Ocultar contraseña" : "Mostrar contraseña"
      );
    });
  }

  // Login
  loginForm.addEventListener("submit", async (event) => {
    event.preventDefault();

    const identificador = identificadorInput.value.trim();
    const password = passwordInput.value.trim();
    const esEmail = identificador.includes("@");

    errorMessage.textContent = "";

    if (!identificador || !password) {
      errorMessage.textContent = "Completá todos los campos.";
      return;
    }

    if (!esEmail && !validarCedulaUruguaya(identificador)) {
      errorMessage.textContent = "La cédula ingresada no es válida.";
      return;
    }

    try {
      const response = await api.post("/auth/login", {
        identificador: esEmail
          ? identificador
          : limpiarDocumento(identificador),
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