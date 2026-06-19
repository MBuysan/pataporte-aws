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


const togglePassword = document.getElementById("togglePassword");
const eyeIcon = document.getElementById("eyeIcon");
const passwordInput = document.getElementById("password");

if (togglePassword && eyeIcon && passwordInput) {
    togglePassword.addEventListener("click", function () {
        if (passwordInput.type === "password") {
            passwordInput.type = "text";
            // Icono Ojo tachado (Ocultar)
            eyeIcon.innerHTML = `
                <path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19m-6.72-1.07a3 3 0 1 1-4.24-4.24"></path>
                <line x1="1" y1="1" x2="23" y2="23"></line>
            `;
            this.setAttribute("aria-label", "Ocultar contraseña");
        } else {
            passwordInput.type = "password";
            // Icono Ojo estándar (Mostrar)
            eyeIcon.innerHTML = `
                <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"></path>
                <circle cx="12" cy="12" r="3"></circle>
            `;
            this.setAttribute("aria-label", "Mostrar contraseña");
        }
    });
}