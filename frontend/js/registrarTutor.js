const form = document.getElementById("formTutor");
const mensaje = document.getElementById("mensaje");

// indicadores de requisitos de cotraseña en tiempo real
document.getElementById("password").addEventListener("input", function () {
    actualizarIndicadores(this.value);
});


form.addEventListener("submit", async (e) => {
    e.preventDefault();

    const nombre = document.getElementById("nombre").value.trim();
    const cedula = document.getElementById("cedula").value.trim();
    const email = document.getElementById("email").value.trim();
    const password = document.getElementById("password").value;
    const telefono = document.getElementById("telefono").value.trim();

    if (!nombre || !cedula || !email || !password) {
        mensaje.innerText = "Por favor complete todos los campos obligatorios.";
        mensaje.style.color = "red";
        return;
    }

    if (!validarCedulaUruguaya(cedula)) {
        mensaje.innerText = "La cédula ingresada no es válida.";
        mensaje.style.color = "red";
        return;
    }

    const errorPassword = validarPassword(password);
    if (errorPassword) {
        mensaje.innerText = errorPassword;
        mensaje.style.color = "red";
        return;
    }

    const data = {
        nombre,
        cedula: limpiarDocumento(cedula),
        email,
        password,
        telefono: telefono || null
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
            actualizarIndicadores("");
            setTimeout(() => {
                window.location.href = `verificar-correo.html?email=${encodeURIComponent(data.email)}&tipo=tutor`;
            }, 1500);
        }
    } catch (error) {
        mensaje.innerText = "Error de conexión con el servidor";
        mensaje.style.color = "red";
    }
});