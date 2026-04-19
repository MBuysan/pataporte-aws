const form = document.getElementById("formMascota");
const mensaje = document.getElementById("mensaje");

form.addEventListener("submit", async (e) => {
  e.preventDefault();

  const tutor = JSON.parse(localStorage.getItem("tutor"));
  if (!tutor) {
    mensaje.innerText = "Debes iniciar sesión primero";
    mensaje.style.color = "red";
    return;
  }

  const capitalizar = (str) =>
    str.trim().charAt(0).toUpperCase() + str.trim().slice(1).toLowerCase();

  const data = {
    id_tutor: tutor.id_tutor,
    foto_url: document.getElementById("foto_url").value,
    nombre: capitalizar(document.getElementById("nombre").value),
    especie: capitalizar(document.getElementById("especie").value),
    raza: capitalizar(document.getElementById("raza").value),
    fecha_de_nacimiento: document.getElementById("fecha_de_nacimiento").value,
    sexo: capitalizar(document.getElementById("sexo").value),
  };

  try {
    const response = await fetch("http://localhost:8000/mascotas/", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(data),
    });

    const result = await response.json();

    if (!response.ok) {
      mensaje.innerText = "Error: " + result.detail;
      mensaje.style.color = "red";
    } else {
      mensaje.innerText = `Mascota registrada. ID: ${result.id_mascota}`;
      mensaje.style.color = "green";
      form.reset();
      setTimeout(() => { window.location.href = "dashboard.html"; }, 1000);
    }
  } catch (error) {
    mensaje.innerText = "Error de conexión con el servidor";
    mensaje.style.color = "red";
  }
});
