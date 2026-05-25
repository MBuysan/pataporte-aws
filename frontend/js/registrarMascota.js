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

  const nombreRaw = document.getElementById("nombre").value.trim();
  const especie = document.getElementById("especie").value;

  if (!nombreRaw || !especie) {
    mensaje.innerText = "Por favor complete todos los campos obligatorios.";
    mensaje.style.color = "red";
    return;
  }

  const capitalizar = (str) => {
    if (!str || !str.trim()) return null;
    const s = str.trim();
    return s.charAt(0).toUpperCase() + s.slice(1).toLowerCase();
  };

  const data = {
    id_tutor: tutor.id_tutor,
    foto_url: document.getElementById("foto_url").value.trim() || null,
    nombre: capitalizar(nombreRaw),
    especie: especie,
    raza: capitalizar(document.getElementById("raza").value),
    fecha_de_nacimiento: document.getElementById("fecha_de_nacimiento").value || null,
    sexo: capitalizar(document.getElementById("sexo").value) || "Desconocido",
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
