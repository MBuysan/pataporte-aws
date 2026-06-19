document.addEventListener("DOMContentLoaded", () => {
    inicializarPantallaLogin();
});

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

    if (togglePassword && eyeIcon) {
    togglePassword.addEventListener("click", function () {
        if (passwordInput.type === "password") {
            passwordInput.type = "text";

            eyeIcon.innerHTML = `
                <path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19m-6.72-1.07a3 3 0 1 1-4.24-4.24"></path>
                <line x1="1" y1="1" x2="23" y2="23"></line>
            `;

            this.setAttribute("aria-label", "Ocultar contraseña");
        } else {
            passwordInput.type = "password";

            eyeIcon.innerHTML = `
                <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"></path>
                <circle cx="12" cy="12" r="3"></circle>
            `;

            this.setAttribute("aria-label", "Mostrar contraseña");
        }
    });
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
        try {
            const response = await api.post("/auth/login/veterinario", {
                identificador,
                password,
            });

            console.log("LOGIN RESPONSE:", response);
            
            // Guardar token y datos en localStorage
            localStorage.setItem("access_token", response.access_token);
            if (response.user) {
                localStorage.setItem("user", JSON.stringify(response.user));
                localStorage.setItem("rol", "veterinario");
                const vetId = response.user?.id_veterinario;

                if (!vetId) {
                    console.error("LOGIN RESPONSE:", response);
                    throw new Error("No se recibió id_veterinario");
                }

                localStorage.setItem("veterinario_id", vetId);
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
