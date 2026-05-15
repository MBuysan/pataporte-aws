document.addEventListener("DOMContentLoaded", async () => {
  const saludoUsuario = document.getElementById("saludo-usuario");
  const btnLogout = document.getElementById("btnLogout");
  const contenedorMascotas = document.getElementById("contenedor-mascotas");
  const mensajeEl = document.getElementById("mensaje-dashboard");

  // 1. Verificar sesión
  const token = localStorage.getItem("access_token");
  const tutorData = JSON.parse(localStorage.getItem("tutor"));

  if (!token || !tutorData) {
    // Si no hay sesión válida, redirigir al login
    window.location.href = "login.html";
    return;
  }

  // 2. Configurar Cerrar Sesión
  btnLogout.addEventListener("click", () => {
    localStorage.removeItem("access_token");
    localStorage.removeItem("tutor");
    window.location.href = "../index.html";
  });

  // 3. Personalizar Saludo
  if (tutorData.nombre) {
    saludoUsuario.textContent = `Hola, ${tutorData.nombre}`;
  }

  // 4. Cargar Mascotas del Tutor
  try {
    const idTutor = tutorData.id_tutor;
    // Consumir endpoint de la API que devuelve las mascotas de este tutor específico
    const mascotas = await api.get(`/tutores/${idTutor}/mascotas`);

    renderizarMascotas(mascotas);
  } catch (error) {
    mostrarMensaje(mensajeEl, error.message || "No se pudieron cargar tus mascotas.", "error");
    contenedorMascotas.innerHTML = `<p style="color:#c0392b; text-align:center; font-size:14px;">Error al cargar datos del servidor.</p>`;
  }

  /**
   * Renderiza las tarjetas de mascotas en el contenedor principal.
   */
  function renderizarMascotas(lista) {
    if (!lista || lista.length === 0) {
      contenedorMascotas.innerHTML = `
        <div class="sin-mascotas">
          <p>Aún no tenés mascotas registradas en tu cuenta.</p>
          <p style="margin-top: 8px; font-size: 13px; color: #4a90e2;">
            ¡Hacé click en "Registrar nueva mascota" para empezar!
          </p>
        </div>
      `;
      return;
    }

    const listContainer = document.createElement("div");
    listContainer.className = "lista-mascotas";

    lista.forEach((m) => {
      const card = document.createElement("a");
      card.href = `perfil-mascota-tutor.html?id=${m.id_mascota}`;
      card.className = "fila-mascota";

      // Formatear detalles: Especie y Raza
      const detalle = [m.especie, m.raza].filter(Boolean).join(" · ");

      const fotoHtml = m.foto_url
        ? `<img src="${m.foto_url}" alt="${m.nombre}" class="foto-mascota" />`
        : `<div class="foto-placeholder">${m.nombre.charAt(0).toUpperCase()}</div>`;

      card.innerHTML = `
        ${fotoHtml}
        <div class="info-mascota">
          <span class="nombre-mascota">${m.nombre}</span>
          <span class="detalle-mascota">${detalle}</span>
        </div>
        <span class="flecha">›</span>
      `;

      listContainer.appendChild(card);
    });

    contenedorMascotas.innerHTML = "";
    contenedorMascotas.appendChild(listContainer);
  }

  function mostrarMensaje(elemento, texto, tipo) {
    elemento.textContent = texto;
    elemento.classList.remove("mensaje-error");
    if (tipo === "error") {
      elemento.classList.add("mensaje-error");
    }
    elemento.style.display = "block";
  }
});
