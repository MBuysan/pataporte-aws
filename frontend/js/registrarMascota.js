const form = document.getElementById("formMascota");
const mensaje = document.getElementById("mensaje");

function capitalizar(str) {
  if (!str) return "";
  return str.charAt(0).toUpperCase() + str.slice(1);
}

form.addEventListener("submit", async (e) => {
  e.preventDefault();

  const tutor = JSON.parse(localStorage.getItem("tutor"));
  if (!tutor) {
    mensaje.innerText = "Debes iniciar sesión primero";
    mensaje.style.color = "red";
    return;
  }

  const nombreRaw = document.getElementById("nombre").value.trim();
  const especie = document.getElementById("especie").value;
  const fechaNacimiento = document.getElementById("fecha_de_nacimiento").value;

  if (!nombreRaw || !especie) {
    mensaje.innerText = "Por favor complete todos los campos obligatorios.";
    mensaje.style.color = "red";
    return;
  }

  if (fechaNacimiento) {
    const hoy = new Date();
    const fechaIngresada = new Date(fechaNacimiento);

    // quitar horas para comparar solo fechas
    hoy.setHours(0, 0, 0, 0);

    if (fechaIngresada > hoy) {
      mensaje.innerText = "La fecha de nacimiento no puede ser futura";

      mensaje.style.color = "red";

      return;
    }
  }

  const data = {
    id_tutor: tutor.id_tutor,
    foto_url: document.getElementById("foto_url").value.trim() || null,
    nombre: capitalizar(nombreRaw),
    especie: especie,
    raza: document.getElementById("raza").value,
    fecha_de_nacimiento:
      document.getElementById("fecha_de_nacimiento").value || null,
    sexo: document.getElementById("sexo").value || "desconocido",
  };

  try {
    const result = await api.post("/mascotas/", data);

    mensaje.innerText = `Mascota registrada. ID: ${result.id_mascota}`;
    mensaje.style.color = "green";

    form.reset();

    setTimeout(() => {
      window.location.href = `perfil-mascota-tutor.html?id=${result.id_mascota}`;
    }, 1000);
  } catch (error) {
    mensaje.innerText = "Error: " + error.message;
    mensaje.style.color = "red";
  }
});
