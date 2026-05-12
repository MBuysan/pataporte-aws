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

            mensajeP.textContent = "Organización registrada exitosamente!";
            mensajeP.style.color = "green";
            
            // Opcional: limpiar formulario
            form.reset();
            
            // Opcional: redirigir al login
            // window.location.href = "login.html";

        } catch (error) {
            mensajeP.textContent = error.message || "Error al registrar organización";
            mensajeP.style.color = "red";
        }
    });
});
