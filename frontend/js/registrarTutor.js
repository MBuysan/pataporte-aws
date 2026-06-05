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

/**
 * Actualiza los indicadores visuales de requisitos en tiempo real.
 */
function actualizarIndicadores(password) {
    const requisitos = [
        { id: "req-largo",     cumple: password.length >= 6 },
        { id: "req-mayuscula", cumple: /[A-Z]/.test(password) },
        { id: "req-minuscula", cumple: /[a-z]/.test(password) },
        { id: "req-numero",    cumple: /\d/.test(password) },
        { id: "req-especial",  cumple: /[!@#$%^&*?]/.test(password) },
    ];

    requisitos.forEach(({ id, cumple }) => {
        const el = document.getElementById(id);
        if (!el) return;
        if (password.length === 0) {
            // sin input todavía: estado neutro
            el.classList.remove("cumplido", "pendiente");
        } else if (cumple) {
            el.classList.add("cumplido");
            el.classList.remove("pendiente");
        } else {
            el.classList.add("pendiente");
            el.classList.remove("cumplido");
        }
    });
}


/**
 * Valida la contraseña contra los requisitos del sistema.
 */
function validarPassword(password) {
    if (password.length < 6)
        return "La contraseña debe tener al menos 6 caracteres.";
    if (!/[A-Z]/.test(password))
        return "La contraseña debe tener al menos una mayúscula.";
    if (!/[a-z]/.test(password))
        return "La contraseña debe tener al menos una minúscula.";
    if (!/\d/.test(password))
        return "La contraseña debe tener al menos un número.";
    if (!/[!@#$%^&*?]/.test(password))
        return "La contraseña debe tener al menos un carácter especial. (!@#$%^&*?)";
    return null;
}