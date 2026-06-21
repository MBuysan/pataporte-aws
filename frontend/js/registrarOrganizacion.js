document.addEventListener("DOMContentLoaded", () => {
    const form = document.getElementById("formOrganizacion");
    const mensajeP = document.getElementById("mensaje");
    const passwordInput = document.getElementById("password");
    const togglePassword = document.getElementById("togglePassword");
    const eyeIcon = document.getElementById("eyeIcon");

    // Indicadores de requisitos de contraseña en tiempo real
    document.getElementById("password").addEventListener("input", function () {
        actualizarIndicadores(this.value);
    });

    if (togglePassword && eyeIcon && passwordInput) {
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

    form.addEventListener("submit", async (e) => {
        e.preventDefault();

        const rut = document.getElementById("rut_organizacion").value.trim();
        const nombre = document.getElementById("nombre").value.trim();
        const matricula = document.getElementById("matricula").value.trim();
        const email = document.getElementById("email").value.trim();
        const password = document.getElementById("password").value;

        if (!rut || !nombre || !email || !password) {
            mensajeP.textContent = "Por favor complete todos los campos obligatorios.";
            mensajeP.style.color = "red";
            return;
        }

        if (!validarRutUruguayo(rut)) {
            mensajeP.textContent = "El RUT ingresado no es válido.";
            mensajeP.style.color = "red";
            return;
        }

        if (!/^\d{1,4}$/.test(matricula)) {
            mensajeP.textContent = "La matrícula debe ser un número de hasta 4 dígitos.";
            mensajeP.style.color = "red";
            return;
        }
        
        const errorPassword = validarPassword(password);
        if (errorPassword) {
            mensajeP.textContent = errorPassword;
            mensajeP.style.color = "red";
            return;
        }

        mensajeP.textContent = "Registrando...";
        mensajeP.style.color = "blue";

        try {
            await api.post("/veterinarios/", {
                rut_organizacion: limpiarDocumento(rut),
                nombre,
                matricula,
                email,
                password
            });

            mensajeP.textContent = "¡Registro exitoso! Te enviamos un código por email. Redirigiendo a verificación...";
            mensajeP.style.color = "green";
            form.reset();
            actualizarIndicadores("");
            setTimeout(() => {
                window.location.href = `verificar-correo.html?email=${encodeURIComponent(email)}&tipo=veterinario`;
            }, 1500);

        } catch (error) {
            mensajeP.textContent = error.message || "Error al registrar organización";
            mensajeP.style.color = "red";
        }
    });
});