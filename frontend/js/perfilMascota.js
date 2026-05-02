// perfilMascota.js
// Tres flujos:
// 1. Cargar mascota y su historial de consultas al entrar
// 2. Modal crear consulta — precarga tratamientos activos, permite editarlos
// 3. Modal detalle de consulta — muestra tratamiento vinculado a esa consulta

document.addEventListener("DOMContentLoaded", async () => {

  const params    = new URLSearchParams(window.location.search);
  const idMascota = params.get("id");

  const nombreEl      = document.getElementById("nombre-mascota");
  const detalleEl     = document.getElementById("detalle-mascota");
  const fotoEl        = document.getElementById("foto-mascota");
  const listaEl       = document.getElementById("lista-consultas");
  const mensajePagina = document.getElementById("mensaje-pagina");

  const modalCrear    = document.getElementById("modal-crear");
  const formCrear     = document.getElementById("form-crear-consulta");
  const btnAgregar    = document.getElementById("btn-agregar-consulta");
  const cerrarCrear   = document.getElementById("cerrar-modal-crear");
  const cancelarCrear = document.getElementById("cancelar-crear");
  const btnGuardar    = document.getElementById("btn-guardar");
  const mensajeCrear  = document.getElementById("mensaje-modal-crear");

  const modalDetalle     = document.getElementById("modal-detalle");
  const contenidoDetalle = document.getElementById("contenido-detalle");
  const cerrarDetalle    = document.getElementById("cerrar-modal-detalle");
  const cerrarDetallBtn  = document.getElementById("cerrar-detalle-btn");

  // guarda los tratamientos activos cargados al abrir el modal
  let tratamientosActivos = [];

  if (!idMascota) {
    mostrarMensaje(mensajePagina, "No se especificó una mascota.", "error");
    nombreEl.textContent = "Mascota no encontrada";
    listaEl.innerHTML = "";
    return;
  }

  await Promise.all([cargarMascota(), cargarConsultas()]);


  // ── Carga de datos ─────────────────────────────────────

  async function cargarMascota() {
    try {
      const mascota = await api.get(`/mascotas/${idMascota}`);
      nombreEl.textContent  = mascota.nombre;
      detalleEl.textContent = [mascota.especie, mascota.raza].filter(Boolean).join(" · ");

      if (mascota.foto_url) {
        fotoEl.outerHTML = `<img src="${mascota.foto_url}" alt="${mascota.nombre}" class="foto-mascota" />`;
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


  function renderizarConsultas(consultas) {
    if (consultas.length === 0) {
      listaEl.innerHTML = `<p class="sin-consultas">No hay consultas registradas.</p>`;
      return;
    }

    listaEl.innerHTML = consultas.map(c => {
      const fecha = new Date(c.fecha_hora);
      const fechaTexto = fecha.toLocaleDateString("es-UY", {
        day: "numeric", month: "short", year: "numeric",
      }) + ", " + fecha.toLocaleTimeString("es-UY", {
        hour: "2-digit", minute: "2-digit",
      });

      return `
        <button class="fila-consulta" data-id="${c.id_consulta}">
          <span class="consulta-fecha">${fechaTexto}</span>
          <span class="consulta-motivo">${c.motivo}</span>
          <span class="consulta-flecha">›</span>
        </button>
      `;
    }).join("");
  }


  // ── Modal crear consulta ───────────────────────────────

  btnAgregar.addEventListener("click",    () => abrirModalCrear());
  cerrarCrear.addEventListener("click",   () => cerrarModalCrear());
  cancelarCrear.addEventListener("click", () => cerrarModalCrear());
  modalCrear.addEventListener("click", (e) => {
    if (e.target === modalCrear) cerrarModalCrear();
  });


  async function abrirModalCrear() {
    formCrear.reset();
    ocultarMensaje(mensajeCrear);

    const contenedorTrat = document.getElementById("contenedor-tratamiento");
    contenedorTrat.innerHTML = `<p class="cargando-trat">Cargando tratamientos...</p>`;
    modalCrear.classList.add("activo");

    try {
      tratamientosActivos = await api.get(`/tratamientos/${idMascota}/activos`);
      renderizarTratamientosEnModal(tratamientosActivos);
    } catch {
      contenedorTrat.innerHTML = `<p class="sin-trat">No se pudieron cargar los tratamientos.</p>`;
    }
  }


  function renderizarTratamientosEnModal(tratamientos) {
    const contenedor = document.getElementById("contenedor-tratamiento");

    if (tratamientos.length === 0) {
      contenedor.innerHTML = `<p class="sin-trat">Sin tratamientos activos.</p>`;
      return;
    }

    // si hay más de un tratamiento activo muestra radios para elegir cuál editar,
    // si hay solo uno lo preselecciona con un input hidden
    const selectorTrat = tratamientos.length > 1
      ? tratamientos.map(t => `
          <label class="campo-check">
            <input type="radio" name="trat-seleccionado" value="${t.id_tratamiento}" />
            <span>${t.nombre}<small>${t.descripcion || ""}</small></span>
          </label>`).join("")
      : `<input type="hidden" name="trat-seleccionado" value="${tratamientos[0].id_tratamiento}" />`;

    const trat0 = tratamientos.length === 1 ? tratamientos[0] : null;

    contenedor.innerHTML = `
      <label class="campo-check">
        <input type="checkbox" id="check-tratamiento" />
        <span>
          Editar tratamiento activo
          <small>Modificá el tratamiento durante esta consulta</small>
        </span>
      </label>

      <div id="form-editar-trat" style="display:none; margin-top:12px;">
        ${tratamientos.length > 1
          ? `<p style="font-size:13px;color:#666;margin-bottom:8px;">Seleccioná el tratamiento a editar:</p>${selectorTrat}`
          : selectorTrat}

        <div class="campo" style="margin-top:10px;">
          <label for="trat-nombre">Nombre</label>
          <input type="text" id="trat-nombre"
            value="${trat0 ? trat0.nombre : ""}"
            placeholder="Nombre del tratamiento" />
        </div>

        <div class="campo">
          <label for="trat-descripcion">Descripción</label>
          <textarea id="trat-descripcion" rows="2"
            placeholder="Indicaciones, dosis, frecuencia...">${trat0 ? (trat0.descripcion || "") : ""}</textarea>
        </div>
      </div>
    `;

    // muestra el formulario de edición al marcar el checkbox
    document.getElementById("check-tratamiento").addEventListener("change", (e) => {
      document.getElementById("form-editar-trat").style.display = e.target.checked ? "block" : "none";

      // si hay más de un tratamiento, preselecciona el primero al abrir
      if (e.target.checked && tratamientos.length > 1) {
        const primero = document.querySelector("input[name='trat-seleccionado']");
        if (primero) primero.checked = true;
        rellenarCamposTratamiento(tratamientos[0]);
      }
    });

    // cuando cambia el radio seleccionado, rellena los campos con los datos de ese tratamiento
    if (tratamientos.length > 1) {
      contenedor.querySelectorAll("input[name='trat-seleccionado']").forEach(radio => {
        radio.addEventListener("change", () => {
          const trat = tratamientos.find(t => t.id_tratamiento === radio.value);
          if (trat) rellenarCamposTratamiento(trat);
        });
      });
    }
  }


  function rellenarCamposTratamiento(trat) {
    const nombreInput = document.getElementById("trat-nombre");
    const descInput   = document.getElementById("trat-descripcion");
    if (nombreInput) nombreInput.value = trat.nombre;
    if (descInput)   descInput.value   = trat.descripcion || "";
  }


  function cerrarModalCrear() {
    modalCrear.classList.remove("activo");
    tratamientosActivos = [];
  }


  formCrear.addEventListener("submit", async (e) => {
    e.preventDefault();

    const motivo = document.getElementById("input-motivo").value.trim();
    if (!motivo) {
      mostrarMensaje(mensajeCrear, "El motivo es obligatorio.", "error");
      return;
    }

    const checkTrat  = document.getElementById("check-tratamiento");
    const editarTrat = checkTrat ? checkTrat.checked : false;

    const body = {
      id_mascota:         idMascota,
      motivo,
      diagnostico:        document.getElementById("input-diagnostico").value.trim() || null,
      agregar_dosis:      document.getElementById("check-dosis").checked,
      editar_tratamiento: editarTrat,
    };

    if (editarTrat) {
      const radioSeleccionado = document.querySelector("input[name='trat-seleccionado']:checked")
        || document.querySelector("input[name='trat-seleccionado'][type='hidden']");

      if (!radioSeleccionado) {
        mostrarMensaje(mensajeCrear, "Seleccioná el tratamiento a editar.", "error");
        return;
      }

      body.id_tratamiento    = radioSeleccionado.value;
      body.datos_tratamiento = {
        nombre:      document.getElementById("trat-nombre")?.value.trim()      || null,
        descripcion: document.getElementById("trat-descripcion")?.value.trim() || null,
      };
    }

    btnGuardar.disabled    = true;
    btnGuardar.textContent = "Guardando...";

    try {
      await api.post("/historial/consultas", body);
      cerrarModalCrear();
      await cargarConsultas();
    } catch (error) {
      mostrarMensaje(mensajeCrear, error.message, "error");
    } finally {
      btnGuardar.disabled    = false;
      btnGuardar.textContent = "Guardar consulta";
    }
  });


  // ── Modal detalle de consulta ──────────────────────────

  listaEl.addEventListener("click", async (e) => {
    const fila = e.target.closest(".fila-consulta");
    if (!fila) return;
    await abrirModalDetalle(fila.dataset.id);
  });

  cerrarDetalle.addEventListener("click",   () => cerrarModalDetalle());
  cerrarDetallBtn.addEventListener("click", () => cerrarModalDetalle());
  modalDetalle.addEventListener("click", (e) => {
    if (e.target === modalDetalle) cerrarModalDetalle();
  });


  async function abrirModalDetalle(idConsulta) {
    contenidoDetalle.innerHTML = `<p style="color:#aaa;text-align:center;padding:20px 0">Cargando...</p>`;
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

    const seccionTratamientos = c.tratamientos && c.tratamientos.length > 0
      ? `<hr class="separador" />
         <p class="detalle-etiqueta">Tratamientos</p>
         <div class="lista-items">
           ${c.tratamientos.map(t => `
             <div class="item-card">
               <strong>${t.nombre}</strong>
               <small>${t.descripcion || "Sin descripción"}</small>
               ${t.finalizacion ? `<small>Fin: ${t.finalizacion}</small>` : ""}
             </div>`).join("")}
         </div>`
      : "";

    const seccionDosis = c.dosis && c.dosis.length > 0
      ? `<hr class="separador" />
         <p class="detalle-etiqueta">Vacunas aplicadas</p>
         <div class="lista-items">
           ${c.dosis.map(d => `
             <div class="item-card">
               <strong>${d.nombre_vacuna}</strong>
               <small>Dosis ${d.numero_dosis} — ${d.fecha_aplicacion}</small>
             </div>`).join("")}
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
      ${seccionTratamientos}
      ${seccionDosis}
    `;
  }


  // ── Utilidades ────────────────────────────────────────

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