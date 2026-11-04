// El veterinario ingresa la cédula del tutor, presiona Buscar,
// y ve directamente el nombre del tutor y la lista de sus mascotas.

document.addEventListener("DOMContentLoaded", () => {

  const rol = localStorage.getItem("rol");
  const token = localStorage.getItem("access_token");
  if (!token || rol !== "veterinario") {
    window.location.href = "login-veterinario.html";
    return;
  }

  const form = document.getElementById("form-busqueda");
  const inputCedula = document.getElementById("input-cedula");
  const btnBuscar = document.getElementById("btn-buscar");
  const mensajeEl = document.getElementById("mensaje-buscar");
  const resultadoEl = document.getElementById("resultado");
  const btnLogout = document.getElementById("btn-logout");
  const btnUserMenu = document.getElementById("btn-user-menu");
  const userDropdown = document.getElementById("user-dropdown");

  btnLogout.addEventListener("click", (e) => {
    e.preventDefault();

    localStorage.removeItem("access_token");
    localStorage.removeItem("rol");
    window.location.href = "../index.html";
  });

  if (btnUserMenu && userDropdown) {
  btnUserMenu.addEventListener("click", function (e) {
    e.stopPropagation();

    const abierto = userDropdown.classList.toggle("activo");
    btnUserMenu.setAttribute("aria-expanded", abierto);
  });

  document.addEventListener("click", function () {
    userDropdown.classList.remove("activo");
    btnUserMenu.setAttribute("aria-expanded", "false");
  });

  document.addEventListener("keydown", function (e) {
    if (e.key === "Escape") {
      userDropdown.classList.remove("activo");
      btnUserMenu.setAttribute("aria-expanded", "false");
    }
  });
  }

  form.addEventListener("submit", async (e) => {
    e.preventDefault();

    const cedula = inputCedula.value.trim();
    if (!cedula) {
      mostrarMensaje(mensajeEl, "Por favor ingresá una cédula.", "error");
      return;
    }

    btnBuscar.disabled = true;
    btnBuscar.textContent = "Buscando...";
    ocultarResultado(resultadoEl);
    ocultarMensaje(mensajeEl);

    try {
      // devuelve { nombre_tutor, mascotas: [ {id_mascota, nombre, especie, foto_url, edad}, ... ] }
      const data = await api.get(`/veterinarios/buscar/${encodeURIComponent(cedula)}`);
      renderizarResultado(resultadoEl, data);

    } catch (error) {
      mostrarMensaje(mensajeEl, error.message, "error");

    } finally {
      btnBuscar.disabled = false;
      btnBuscar.textContent = "Buscar";
    }
  });


  /**
   * Construye y muestra el resultado completo: nombre del tutor y filas de mascotas.
   * @param {HTMLElement} contenedor
   * @param {{ nombre_tutor: string, mascotas: Array }} data
   */
  function renderizarResultado(contenedor, data) {

    const filasMascotas = data.mascotas.length === 0
      ? `<p class="sin-mascotas">Este tutor no tiene mascotas registradas.</p>`
      : data.mascotas.map(m => filaMascota(m)).join("");

    contenedor.innerHTML = `
      <p class="nombre-tutor">${data.nombre_tutor}</p>
      <div class="lista-mascotas">${filasMascotas}</div>
    `;

    contenedor.style.display = "block";
  }


  /**
   * Genera el HTML de una fila para una mascota.
   * Cada fila es un enlace al perfil completo de la mascota.
   * @param {{ id_mascota, nombre, especie, raza, foto_url, edad }} mascota
   * @returns {string}
   */
  function filaMascota(mascota) {

    // construye el texto de detalle combinando especie, raza y edad
    // filter(Boolean) descarta los null antes de unir con " · "
    const detalle = [
      mascota.especie,
      mascota.raza || null,
      mascota.edad != null
        ? `${mascota.edad} ${mascota.edad === 1 ? "año" : "años"}`
        : null,
    ].filter(Boolean).join(" | ");

    const foto = mascota.foto_url
      ? `<img src="${petPhotoUrl(mascota.foto_url)}" alt="${mascota.nombre}" class="foto-mascota" />`
      : `<div class="foto-placeholder">${mascota.nombre.charAt(0).toUpperCase()}</div>`;

    return `
      <a href="perfil-mascota-vet.html?id=${mascota.id_mascota}" class="fila-mascota">
        ${foto}
        <div class="info-mascota">
          <span class="nombre-mascota">${mascota.nombre}</span>
          <span class="detalle-mascota">${detalle}</span>
        </div>
        <span class="flecha">›</span>
      </a>
    `;
  }


  function mostrarMensaje(elemento, texto, tipo) {
    elemento.textContent = texto;
    elemento.classList.remove("mensaje-exito", "mensaje-error");
    elemento.classList.add(tipo === "exito" ? "mensaje-exito" : "mensaje-error");
    elemento.style.display = "block";
  }

  function ocultarMensaje(elemento) {
    elemento.style.display = "none";
    elemento.textContent = "";
  }

  function ocultarResultado(elemento) {
    elemento.style.display = "none";
    elemento.innerHTML = "";
  }

});