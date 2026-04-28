// perfilMascota.js
// Maneja tres funcionalidades en la misma página:
// 1. Cargar datos básicos de la mascota y su historial al entrar
// 2. Modal de crear consulta
// 3. Modal de detalle de una consulta al hacer click

document.addEventListener("DOMContentLoaded", async () => {

  // Lee el id de la mascota desde la URL: perfil-mascota.html?id=uuid-123
  const params     = new URLSearchParams(window.location.search);
  const idMascota  = params.get("id");

  // Elementos de la página
  const nombreEl      = document.getElementById("nombre-mascota");
  const detalleEl     = document.getElementById("detalle-mascota");
  const fotoEl        = document.getElementById("foto-mascota");
  const listaEl       = document.getElementById("lista-consultas");
  const mensajePagina = document.getElementById("mensaje-pagina");

  // Elementos del modal crear
  const modalCrear      = document.getElementById("modal-crear");
  const formCrear       = document.getElementById("form-crear-consulta");
  const btnAgregar      = document.getElementById("btn-agregar-consulta");
  const cerrarCrear     = document.getElementById("cerrar-modal-crear");
  const cancelarCrear   = document.getElementById("cancelar-crear");
  const btnGuardar      = document.getElementById("btn-guardar");
  const mensajeCrear    = document.getElementById("mensaje-modal-crear");

  // Elementos del modal detalle
  const modalDetalle    = document.getElementById("modal-detalle");
  const contenidoDetalle = document.getElementById("contenido-detalle");
  const cerrarDetalle   = document.getElementById("cerrar-modal-detalle");
  const cerrarDetallBtn = document.getElementById("cerrar-detalle-btn");

  // Si no hay id en la URL no se puede hacer nada útil
  if (!idMascota) {
    mostrarMensaje(mensajePagina, "No se especificó una mascota.", "error");
    nombreEl.textContent = "Mascota no encontrada";
    listaEl.innerHTML = "";
    return;
  }

  // ── Carga inicial ──────────────────────────────────────────────────────────

  await Promise.all([
    cargarMascota(),
    cargarConsultas(),
  ]);


  // ── Funciones de carga ─────────────────────────────────────────────────────

  async function cargarMascota() {
    try {
      const mascota = await api.get(`/mascotas/${idMascota}`);

      nombreEl.textContent = mascota.nombre;

      // construye la línea de detalle: especie · raza · edad
      const partes = [
        mascota.especie,
        mascota.raza || null,
      ].filter(Boolean).join(" · ");
      detalleEl.textContent = partes;

      // foto o inicial como placeholder
      if (mascota.foto_url) {
        fotoEl.outerHTML = `<img src="${mascota.foto_url}" alt="${mascota.nombre}" class="foto-mascota" id="foto-mascota" />`;
      } else {
        fotoEl.textContent = mascota.nombre.charAt(0).toUpperCase();
      }

    } catch (error) {
      mostrarMensaje(mensajePagina, `No se pudo cargar la mascota: ${error.message}`, "error");
    }
  }


  async function cargarConsultas() {
    try {
      const consultas = await api.get(`/historial/${idMascota}/consultas`);
      renderizarConsultas(consultas);

    } catch (error) {
      listaEl.innerHTML = `<p class="sin-consultas">${error.message}</p>`;
    }
  }


  // ── Renderizado de consultas ───────────────────────────────────────────────

  function renderizarConsultas(consultas) {
    if (consultas.length === 0) {
      listaEl.innerHTML = `<p class="sin-consultas">No hay consultas registradas.</p>`;
      return;
    }

    listaEl.innerHTML = consultas.map(c => {
      // formatea la fecha: "15 jun 2024, 10:30"
      const fecha = new Date(c.fecha_hora);
      const fechaTexto = fecha.toLocaleDateString("es-UY", {
        day:   "numeric",
        month: "short",
        year:  "numeric",
      }) + ", " + fecha.toLocaleTimeString("es-UY", {
        hour:   "2-digit",
        minute: "2-digit",
      });

      // data-id guarda el id de la consulta para usarlo en el click
      return `
        <button class="fila-consulta" data-id="${c.id_consulta}">
          <span class="consulta-fecha">${fechaTexto}</span>
          <span class="consulta-motivo">${c.motivo}</span>
          <span class="consulta-flecha">›</span>
        </button>
      `;
    }).join("");
  }


  // ── Modal crear consulta ───────────────────────────────────────────────────

  // Abre el modal al hacer click en "+ Agregar consulta"
  btnAgregar.addEventListener("click", () => abrirModalCrear());

  // Cierra el modal con la X o el botón cancelar
  cerrarCrear.addEventListener("click",   () => cerrarModalCrear());
  cancelarCrear.addEventListener("click", () => cerrarModalCrear());

  // Cierra si hace click fuera del modal (en el overlay)
  modalCrear.addEventListener("click", (e) => {
    if (e.target === modalCrear) cerrarModalCrear();
  });

  function abrirModalCrear() {
    formCrear.reset();              // limpia campos de un uso anterior
    ocultarMensaje(mensajeCrear);
    modalCrear.classList.add("activo");
  }

  function cerrarModalCrear() {
    modalCrear.classList.remove("activo");
  }

  formCrear.addEventListener("submit", async (e) => {
    e.preventDefault();

    const motivo = document.getElementById("input-motivo").value.trim();
    if (!motivo) {
      mostrarMensaje(mensajeCrear, "El motivo es obligatorio.", "error");
      return;
    }

    btnGuardar.disabled     = true;
    btnGuardar.textContent  = "Guardando...";

    try {
      await api.post("/historial/consultas", {
        id_mascota:           idMascota,
        motivo,
        diagnostico:          document.getElementById("input-diagnostico").value.trim()   || null,
        tratamiento_indicado: document.getElementById("input-tratamiento").value.trim()   || null,
        editar_tratamiento:   document.getElementById("check-tratamiento").checked,
        agregar_dosis:        document.getElementById("check-dosis").checked,
      });

      cerrarModalCrear();
      // recarga el historial para que aparezca la consulta recién creada
      await cargarConsultas();

    } catch (error) {
      mostrarMensaje(mensajeCrear, error.message, "error");

    } finally {
      btnGuardar.disabled    = false;
      btnGuardar.textContent = "Guardar consulta";
    }
  });


  // ── Modal detalle de consulta ──────────────────────────────────────────────

  // Delegación de eventos — las filas se crean dinámicamente
  // por lo que no se puede poner el listener directamente en cada una
  listaEl.addEventListener("click", async (e) => {
    const fila = e.target.closest(".fila-consulta");
    if (!fila) return;

    const idConsulta = fila.dataset.id;
    await abrirModalDetalle(idConsulta);
  });

  cerrarDetalle.addEventListener("click",   () => cerrarModalDetalle());
  cerrarDetallBtn.addEventListener("click", () => cerrarModalDetalle());

  modalDetalle.addEventListener("click", (e) => {
    if (e.target === modalDetalle) cerrarModalDetalle();
  });

  async function abrirModalDetalle(idConsulta) {
    contenidoDetalle.innerHTML = `<p style="color:#aaa; text-align:center; padding: 20px 0">Cargando...</p>`;
    modalDetalle.classList.add("activo");

    try {
      const consulta = await api.get(`/historial/${idMascota}/detalle/${idConsulta}`);
      renderizarDetalle(consulta);

    } catch (error) {
      contenidoDetalle.innerHTML = `<p style="color:#c0392b">${error.message}</p>`;
    }
  }

  function cerrarModalDetalle() {
    modalDetalle.classList.remove("activo");
  }

  function renderizarDetalle(c) {
    const fecha = new Date(c.fecha_hora).toLocaleString("es-UY", {
      day: "numeric", month: "long", year: "numeric",
      hour: "2-digit", minute: "2-digit",
    });

    // construye las secciones de tratamientos y dosis solo si tienen datos
    const seccionTratamientos = c.tratamientos && c.tratamientos.length > 0
      ? `<hr class="separador" />
         <p class="detalle-etiqueta">Tratamientos</p>
         <div class="lista-items">
           ${c.tratamientos.map(t => `
             <div class="item-card">
               <strong>${t.nombre}</strong>
               <small>${t.descripcion || "Sin descripción"}</small>
             </div>
           `).join("")}
         </div>`
      : "";

    const seccionDosis = c.dosis && c.dosis.length > 0
      ? `<hr class="separador" />
         <p class="detalle-etiqueta">Dosis aplicadas</p>
         <div class="lista-items">
           ${c.dosis.map(d => `
             <div class="item-card">
               <strong>Dosis ${d.numero_dosis}</strong>
               <small>${d.fecha_aplicacion}</small>
             </div>
           `).join("")}
         </div>`
      : "";

    contenidoDetalle.innerHTML = `
      <div class="detalle-campo">
        <p class="detalle-etiqueta">Fecha</p>
        <p class="detalle-valor">${fecha}</p>
      </div>

      <div class="detalle-campo">
        <p class="detalle-etiqueta">Motivo</p>
        <p class="detalle-valor">${c.motivo}</p>
      </div>

      <div class="detalle-campo">
        <p class="detalle-etiqueta">Diagnóstico</p>
        ${c.diagnostico
          ? `<p class="detalle-valor">${c.diagnostico}</p>`
          : `<p class="detalle-vacio">No registrado</p>`}
      </div>

      <div class="detalle-campo">
        <p class="detalle-etiqueta">Tratamiento indicado</p>
        ${c.tratamiento_indicado
          ? `<p class="detalle-valor">${c.tratamiento_indicado}</p>`
          : `<p class="detalle-vacio">No registrado</p>`}
      </div>

      ${seccionTratamientos}
      ${seccionDosis}
    `;
  }


  // ── Utilidades ────────────────────────────────────────────────────────────

  function mostrarMensaje(elemento, texto, tipo) {
    elemento.textContent = texto;
    elemento.classList.remove("mensaje-exito", "mensaje-error");
    elemento.classList.add(tipo === "exito" ? "mensaje-exito" : "mensaje-error");
    elemento.style.display = "block";
  }

  function ocultarMensaje(elemento) {
    elemento.style.display = "none";
    elemento.textContent   = "";
  }

});