document.addEventListener("DOMContentLoaded", () => {
    const form = document.getElementById("formOrganizacion");
    const mensajeP = document.getElementById("mensaje");

    form.addEventListener("submit", async (e) => {
        e.preventDefault();

        const rut = document.getElementById("rut").value.trim();

        if (!validarRutUruguayo(rut)) {
            mensajeP.textContent = "El RUT ingresado no es válido.";
            mensajeP.style.color = "red";
            return;
        }

        mensajeP.textContent = "Registrando...";
        mensajeP.style.color = "blue";

        const nombre = document.getElementById("nombre").value.trim();
        const email = document.getElementById("email").value.trim();
        const password = document.getElementById("password").value;

        try {
            await api.post("/veterinarios/", {
                rut: limpiarDocumento(rut),
                nombre,
                email,
                password
            });

            mensajeP.textContent = "¡Registro exitoso! Te enviamos un código por email. Redirigiendo a verificación...";
            mensajeP.style.color = "green";
            form.reset();
            setTimeout(() => {
                window.location.href = `verificar-correo.html?email=${encodeURIComponent(email)}&tipo=veterinaria`;
            }, 1500);

        } catch (error) {
            mensajeP.textContent = error.message || "Error al registrar organización";
            mensajeP.style.color = "red";
        }
    });
});
