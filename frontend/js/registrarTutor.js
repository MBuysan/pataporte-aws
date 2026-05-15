const form = document.getElementById("formTutor");
const mensaje = document.getElementById("mensaje");

form.addEventListener("submit", async (e) => {
    e.preventDefault();

    const data = {
        nombre: document.getElementById("nombre").value,
        cedula: document.getElementById("cedula").value,
        email: document.getElementById("email").value,
        password: document.getElementById("password").value,
        telefono: document.getElementById("telefono").value
    };

    try {
        const response = await fetch("http://localhost:8000/tutores/", {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify(data)
        });

        const result = await response.json();

        if (!response.ok) {
            mensaje.innerText = "Error: " + result.detail;
            mensaje.style.color = "red";
        } else {
            mensaje.innerText = "¡Registro exitoso! Te enviamos un código por email. Redirigiendo a verificación...";
            mensaje.style.color = "green";
            form.reset();
            
            // Esperar 1.5 segundos para que lean el mensaje de éxito y luego redirigir
            setTimeout(() => {
                window.location.href = `verificar-correo.html?email=${encodeURIComponent(data.email)}&tipo=tutor`;
            }, 1500);
        }
    } catch (error) {
        mensaje.innerText = "Error de conexión con el servidor";
        mensaje.style.color = "red";
    }
});