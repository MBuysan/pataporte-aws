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

  const archivoFoto = document.getElementById("foto_archivo").files[0];
  if (archivoFoto) {
    const extensionesPermitidas = ["image/jpeg", "image/png", "image/webp"];
    if (!extensionesPermitidas.includes(archivoFoto.type)) {
      mensaje.innerText = "La foto debe ser JPG, PNG o WEBP";
      mensaje.style.color = "red";
      return;
    }
    if (archivoFoto.size > 5 * 1024 * 1024) {
      mensaje.innerText = "La foto no puede superar los 5MB";
      mensaje.style.color = "red";
      return;
    }
  }

  const formData = new FormData();
  formData.append("id_tutor", tutor.id_tutor);
  formData.append("nombre", capitalizar(nombreRaw));
  formData.append("especie", especie);
  formData.append("raza", document.getElementById("raza").value.trim());
  formData.append("fecha_de_nacimiento", fechaNacimiento);
  formData.append("sexo", document.getElementById("sexo").value || "desconocido");

  if (archivoFoto) { 
    formData.append("foto", archivoFoto);
  }



  try {
    const result = await api.postForm("/mascotas/", formData);

    mensaje.innerText = `Mascota registrada!`;
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
