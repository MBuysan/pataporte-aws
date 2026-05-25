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
        const esEmail = identificador.includes("@");
        const password = passwordInput.value.trim();

        errorMessage.textContent = "";

        if (!identificador || !password) {
            errorMessage.textContent = "Por favor, completa todos los campos.";
            return;
        }
        if (!esEmail && !validarRutUruguayo(identificador)) {
            errorMessage.textContent = "El RUT ingresado no es válido.";
            return;
        }
        try {
            const response = await api.post("/auth/login/veterinario", {
                identificador: esEmail ? identificador : limpiarDocumento(identificador),
                password,
            });

            // Guardar token y datos en localStorage
            localStorage.setItem("access_token", response.access_token);
            if (response.user) {
                localStorage.setItem("user", JSON.stringify(response.user));
                localStorage.setItem("rol", "veterinario");
                const vetId = response.user?.id_veterinaria;

                if (!vetId) {
                    console.error("LOGIN RESPONSE:", response);
                    throw new Error("No se recibió id_veterinaria");
                }

                localStorage.setItem("veterinaria_id", vetId);
            }

            // Redirigir al dashboard
            window.location.href = "buscar-mascotas.html";
        } catch (error) {
            console.error("Error al iniciar sesión:", error.message);
            // El backend ya devuelve "Su cuenta está pendiente de aprobación" o "Credenciales inválidas" en el error.detail
            errorMessage.textContent = error.message || "Credenciales inválidas.";
        }
    });
}
