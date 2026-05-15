document.addEventListener("DOMContentLoaded", () => {
    const form = document.getElementById("formOrganizacion");
    const mensajeP = document.getElementById("mensaje");

    form.addEventListener("submit", async (e) => {
        e.preventDefault();
        
        mensajeP.textContent = "Registrando...";
        mensajeP.style.color = "blue";

        const rut = document.getElementById("rut").value.trim();
        const nombre = document.getElementById("nombre").value.trim();
        const email = document.getElementById("email").value.trim();
        const password = document.getElementById("password").value;

        try {
            const data = await api.post("/veterinarios/", {
                rut: rut,
                nombre: nombre,
                email: email,
                password: password
            });

            mensajeP.textContent = "¡Registro exitoso! Te enviamos un código por email. Redirigiendo a verificación...";
            mensajeP.style.color = "green";
            
            // Limpiar formulario
            form.reset();
            
            // Esperar 1.5 segundos y redirigir a la verificación
            setTimeout(() => {
                window.location.href = `verificar-correo.html?email=${encodeURIComponent(email)}&tipo=veterinaria`;
            }, 1500);

        } catch (error) {
            mensajeP.textContent = error.message || "Error al registrar organización";
            mensajeP.style.color = "red";
        }
    });
});
