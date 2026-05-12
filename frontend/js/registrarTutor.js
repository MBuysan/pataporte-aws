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
            mensaje.innerText = "Tutor registrado correctamente";
            mensaje.style.color = "green";
            form.reset();
        }
        window.location.href = "dashboard.html";
    } catch (error) {
        mensaje.innerText = "Error de conexión con el servidor";
        mensaje.style.color = "red";
    }
});