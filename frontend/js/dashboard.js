document.addEventListener("DOMContentLoaded", async () => {
  const saludoUsuario = document.getElementById("saludo-usuario");
  const btnLogout = document.getElementById("btnLogout");
  const contenedorMascotas = document.getElementById("contenedor-mascotas");
  const mensajeEl = document.getElementById("mensaje-dashboard");
  const btnEliminarCuenta = document.getElementById("btnEliminarCuenta");

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

  // 3. Configurar Eliminar Cuenta
  btnEliminarCuenta.addEventListener("click", async () => {
    const confirmacion = window.prompt(
      "Esta acción eliminará definitivamente tu cuenta y todas tus mascotas.\n\nEscribí exactamente:\neliminar mi cuenta"
    );

    if (confirmacion !== "eliminar mi cuenta") {
      alert("Confirmación incorrecta.");
      return;
    }

    alert(
      "Pataporte está generando la documentación de respaldo de tus mascotas para enviarla por correo electrónico. Luego se eliminará definitivamente tu cuenta y toda la información asociada."
    );

    try {

      await api.delete(
        `/tutores/${tutorData.id_tutor}`
      );

      localStorage.removeItem("access_token");
      localStorage.removeItem("tutor");

      alert(
        "Cuenta eliminada correctamente."
      );

      window.location.href = "../index.html";

    } catch (error) {

      alert(
        `No se pudo eliminar la cuenta: ${error.message}`
      );
    }
  }
  );

  // 4. Personalizar Saludo
  if (tutorData.nombre) {
    saludoUsuario.textContent = `Hola, ${tutorData.nombre}`;
  }

  // 5. Cargar Mascotas del Tutor
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

      // Calcular la edad a partir de la fecha de nacimiento
      const calcularEdad = (fechaNacimientoStr) => {
        if (!fechaNacimientoStr) return null;
        const hoy = new Date();
        const nacimiento = new Date(fechaNacimientoStr);
        if (isNaN(nacimiento.getTime())) return null;

        let edad = hoy.getFullYear() - nacimiento.getFullYear();
        const mes = hoy.getMonth() - nacimiento.getMonth();
        if (mes < 0 || (mes === 0 && hoy.getDate() < nacimiento.getDate())) {
          edad--;
        }

        if (edad > 0) {
          return edad === 1 ? "1 año" : `${edad} años`;
        }

        // Si es menor a un año, calcular en meses
        let meses = (hoy.getFullYear() - nacimiento.getFullYear()) * 12 + hoy.getMonth() - nacimiento.getMonth();
        if (hoy.getDate() < nacimiento.getDate()) {
          meses--;
        }
        if (meses > 0) {
          return meses === 1 ? "1 mes" : `${meses} meses`;
        }

        // Si es menor a un mes, calcular en días
        const unDia = 24 * 60 * 60 * 1000;
        const dias = Math.floor((hoy - nacimiento) / unDia);
        if (dias > 0) {
          return dias === 1 ? "1 día" : `${dias} días`;
        }
        return "0 días";
      };

      // Formatear detalles: Especie y Edad (Capitalizados y separados por barra vertical)
      const formatString = (str) => str ? str.charAt(0).toUpperCase() + str.slice(1) : "";
      const edadStr = calcularEdad(m.fecha_de_nacimiento);
      const detalle = [formatString(m.especie), edadStr].filter(Boolean).join(" | ");

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
