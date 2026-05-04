document.addEventListener("DOMContentLoaded", () => {
    inicializarPantallaLogin();
});

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
            errorMessage.textContent = "Por favor, completa todos los campos.";
            return;
        }

        try {
            const response = await api.post("/auth/login/veterinaria", {
                identificador,
                password,
            });

            // Guardar token y datos en localStorage
            localStorage.setItem("access_token", response.access_token);
            if (response.user) {
                localStorage.setItem("user", JSON.stringify(response.user));
                localStorage.setItem("rol", "veterinaria");
            }

            // Redirigir al dashboard
            window.location.href = "dashboard.html";
        } catch (error) {
            console.error("Error al iniciar sesión:", error.message);
            // El backend ya devuelve "Su cuenta está pendiente de aprobación" o "Credenciales inválidas" en el error.detail
            errorMessage.textContent = error.message || "Credenciales inválidas.";
        }
    });
}
