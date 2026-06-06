document.addEventListener("DOMContentLoaded", () => {
    const form = document.getElementById("formOrganizacion");
    const mensajeP = document.getElementById("mensaje");

    // Indicadores de requisitos de contraseña en tiempo real
    document.getElementById("password").addEventListener("input", function () {
        actualizarIndicadores(this.value);
    });

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