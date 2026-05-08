// Vista del veterinario — puede ver info, tratamientos, historial y agregar consulta.
// Secciones desplegables: tratamientos e historial. Modal para nueva consulta y detalle.

document.addEventListener("DOMContentLoaded", async () => {

  const params    = new URLSearchParams(window.location.search);
  const idMascota = params.get("id");

  const nombreEl      = document.getElementById("nombre-mascota");
  const detalleEl     = document.getElementById("detalle-mascota");
  const fotoEl        = document.getElementById("foto-mascota");
  const mensajePagina = document.getElementById("mensaje-pagina");
  const seccionTrat   = document.getElementById("seccion-tratamientos");
  const seccionHist   = document.getElementById("seccion-historial");
  const btnTrat       = document.getElementById("btn-tratamientos");
  const btnHist       = document.getElementById("btn-historial");
  const btnAgregar    = document.getElementById("btn-agregar-consulta");
  const modalCrear    = document.getElementById("modal-crear");
  const formCrear     = document.getElementById("form-crear-consulta");
  const cerrarCrear   = document.getElementById("cerrar-modal-crear");
  const cancelarCrear = document.getElementById("cancelar-crear");
  const btnGuardar    = document.getElementById("btn-guardar");
  const mensajeCrear  = document.getElementById("mensaje-modal-crear");
  const modalDetalle     = document.getElementById("modal-detalle");
  const contenidoDetalle = document.getElementById("contenido-detalle");
  const cerrarDetalle    = document.getElementById("cerrar-modal-detalle");
  const cerrarDetallBtn  = document.getElementById("cerrar-detalle-btn");

  let tratamientosActivos  = [];
  let tratamientosCargados = false;
  let historialCargado     = false;

  if (!idMascota) {
    mostrarMensaje(mensajePagina, "No se especificó una mascota.", "error");
    return;
  }

  await cargarMascota();


  // ── Carga de datos ─────────────────────────────────────

  async function cargarMascota() {
    try {
      const m = await api.get(`/mascotas/${idMascota}`);
      nombreEl.textContent  = m.nombre;
      detalleEl.textContent = [m.especie, m.raza, m.sexo !== "desconocido" ? m.sexo : null].filter(Boolean).join(" · ");
      if (m.foto_url) {
        fotoEl.outerHTML = `<img src="${m.foto_url}" alt="${m.nombre}" class="foto-mascota" />`;
      } else {
        fotoEl.textContent = m.nombre.charAt(0).toUpperCase();
      }
    } catch (error) {
      mostrarMensaje(mensajePagina, `No se pudo cargar la mascota: ${error.message}`, "error");
    }
  }


  // ── Tratamientos desplegables ──────────────────────────

  btnTrat.addEventListener("click", async () => {
    const abierto = seccionTrat.style.display === "block";
    seccionTrat.style.display = abierto ? "none" : "block";
    btnTrat.textContent = abierto ? "Tratamientos" : "Cerrar tratamientos";

    if (!abierto && !tratamientosCargados) {
      seccionTrat.innerHTML = `<p class="cargando">Cargando...</p>`;
      try {
        const tratamientos   = await api.get(`/tratamientos/${idMascota}/activos`);
        tratamientosActivos  = tratamientos;
        tratamientosCargados = true;
        renderizarTratamientos(tratamientos);
      } catch (e) {
        seccionTrat.innerHTML = `<p class="error-seccion">${e.message}</p>`;
      }
    }
  });


  function renderizarTratamientos(list) {
    seccionTrat.innerHTML = list.length === 0
      ? `<p class="sin-datos">Sin tratamientos activos.</p>`
      : list.map(t => `
          <div class="item-card">
            <strong>${t.nombre}</strong>
            <small>${t.descripcion || "Sin descripción"}</small>
            ${t.finalizacion ? `<small>Finaliza: ${new Date(t.finalizacion).toLocaleDateString("es-UY")}</small>` : ""}
          </div>`).join("");
  }


  // ── Historial desplegable ──────────────────────────────

  btnHist.addEventListener("click", async () => {
    const abierto = seccionHist.style.display === "block";
    seccionHist.style.display = abierto ? "none" : "block";
    btnHist.textContent = abierto ? "Historial clínico" : "Cerrar historial";

    if (!abierto && !historialCargado) {
      seccionHist.innerHTML = `<p class="cargando">Cargando...</p>`;
      try {
        const consultas  = await api.get(`/historial/${idMascota}/consultas`);
        historialCargado = true;
        renderizarHistorial(consultas);
      } catch (e) {
        seccionHist.innerHTML = `<p class="error-seccion">${e.message}</p>`;
      }
    }
  });


  function renderizarHistorial(consultas) {
    seccionHist.innerHTML = consultas.length === 0
      ? `<p class="sin-datos">No hay consultas registradas.</p>`
      : consultas.map(c => {
          const f = new Date(c.fecha_hora);
          const fecha = f.toLocaleDateString("es-UY", { day: "numeric", month: "short", year: "numeric" })
                      + ", " + f.toLocaleTimeString("es-UY", { hour: "2-digit", minute: "2-digit" });
          return `
            <button class="fila-consulta" data-id="${c.id_consulta}">
              <span class="consulta-fecha">${fecha}</span>
              <span class="consulta-motivo">${c.motivo}</span>
              <span class="consulta-flecha">›</span>
            </button>`;
        }).join("");
  }

  // delegación en historial
  seccionHist.addEventListener("click", async (e) => {
    const fila = e.target.closest(".fila-consulta");
    if (fila) await abrirModalDetalle(fila.dataset.id);
  });


  // ── Modal agregar consulta ─────────────────────────────

  btnAgregar.addEventListener("click",    () => abrirModalCrear());
  cerrarCrear.addEventListener("click",   () => cerrarModalCrear());
  cancelarCrear.addEventListener("click", () => cerrarModalCrear());
  modalCrear.addEventListener("click", (e) => { if (e.target === modalCrear) cerrarModalCrear(); });


  async function abrirModalCrear() {
    formCrear.reset();
    ocultarMensaje(mensajeCrear);
    const ct = document.getElementById("contenedor-tratamiento");
    ct.innerHTML = `<p class="cargando">Cargando tratamientos...</p>`;
    modalCrear.classList.add("activo");
    try {
      tratamientosActivos = await api.get(`/tratamientos/${idMascota}/activos`);
      renderizarTratamientosEnModal(tratamientosActivos);
    } catch {
      ct.innerHTML = `<p class="sin-datos">No se pudieron cargar los tratamientos.</p>`;
    }
  }


  function renderizarTratamientosEnModal(trats) {
    const ct = document.getElementById("contenedor-tratamiento");
    if (trats.length === 0) { ct.innerHTML = `<p class="sin-datos">Sin tratamientos activos.</p>`; return; }

    const t0      = trats.length === 1 ? trats[0] : null;
    const selector = trats.length > 1
      ? trats.map(t => `<label class="campo-check"><input type="radio" name="trat-sel" value="${t.id_tratamiento}" /><span>${t.nombre}<small>${t.descripcion || ""}</small></span></label>`).join("")
      : `<input type="hidden" name="trat-sel" value="${trats[0].id_tratamiento}" />`;

    ct.innerHTML = `
      <label class="campo-check">
        <input type="checkbox" id="check-tratamiento" />
        <span>Editar tratamiento activo<small>Modificá el tratamiento durante esta consulta</small></span>
      </label>
      <div id="form-editar-trat" style="display:none;margin-top:12px;">
        ${trats.length > 1 ? `<p style="font-size:13px;color:#666;margin-bottom:8px;">Seleccioná el tratamiento a editar:</p>` : ""}
        ${selector}
        <div class="campo" style="margin-top:10px;">
          <label for="trat-nombre">Nombre</label>
          <input type="text" id="trat-nombre" value="${t0 ? t0.nombre : ""}" placeholder="Nombre del tratamiento" />
        </div>
        <div class="campo">
          <label for="trat-descripcion">Descripción</label>
          <textarea id="trat-descripcion" rows="2" placeholder="Indicaciones...">${t0 ? (t0.descripcion || "") : ""}</textarea>
        </div>
      </div>`;

    document.getElementById("check-tratamiento").addEventListener("change", (e) => {
      document.getElementById("form-editar-trat").style.display = e.target.checked ? "block" : "none";
      if (e.target.checked && trats.length > 1) {
        const r = document.querySelector("input[name='trat-sel']");
        if (r) { r.checked = true; rellenarCampos(trats[0]); }
      }
    });

    if (trats.length > 1) {
      ct.querySelectorAll("input[name='trat-sel']").forEach(r => {
        r.addEventListener("change", () => {
          const t = trats.find(x => x.id_tratamiento === r.value);
          if (t) rellenarCampos(t);
        });
      });
    }
  }

  function rellenarCampos(t) {
    const n = document.getElementById("trat-nombre");
    const d = document.getElementById("trat-descripcion");
    if (n) n.value = t.nombre;
    if (d) d.value = t.descripcion || "";
  }

  function cerrarModalCrear() {
    modalCrear.classList.remove("activo");
    tratamientosActivos = [];
  }


  formCrear.addEventListener("submit", async (e) => {
    e.preventDefault();
    const motivo = document.getElementById("input-motivo").value.trim();
    if (!motivo) { mostrarMensaje(mensajeCrear, "El motivo es obligatorio.", "error"); return; }

    const check = document.getElementById("check-tratamiento");
    const editar = check ? check.checked : false;

    const body = {
      id_mascota:         idMascota,
      motivo,
      diagnostico:        document.getElementById("input-diagnostico").value.trim() || null,
      agregar_dosis:      document.getElementById("check-dosis").checked,
      editar_tratamiento: editar,
    };

    if (editar) {
      const radio = document.querySelector("input[name='trat-sel']:checked")
                 || document.querySelector("input[name='trat-sel'][type='hidden']");
      if (!radio) { mostrarMensaje(mensajeCrear, "Seleccioná el tratamiento a editar.", "error"); return; }
      body.id_tratamiento    = radio.value;
      body.datos_tratamiento = {
        nombre:      document.getElementById("trat-nombre")?.value.trim()      || null,
        descripcion: document.getElementById("trat-descripcion")?.value.trim() || null,
      };
    }

    btnGuardar.disabled = true;
    btnGuardar.textContent = "Guardando...";

    try {
      await api.post("/historial/consultas", body);
      cerrarModalCrear();
      historialCargado = false;
      tratamientosCargados = false;
      seccionHist.style.display = "none";
      seccionTrat.style.display = "none";
      btnHist.textContent = "Historial clínico";
      btnTrat.textContent = "Tratamientos";
    } catch (error) {
      mostrarMensaje(mensajeCrear, error.message, "error");
    } finally {
      btnGuardar.disabled    = false;
      btnGuardar.textContent = "Guardar consulta";
    }
  });


  // ── Modal detalle consulta ─────────────────────────────

  cerrarDetalle.addEventListener("click",   () => cerrarModalDetalle());
  cerrarDetallBtn.addEventListener("click", () => cerrarModalDetalle());
  modalDetalle.addEventListener("click", (e) => { if (e.target === modalDetalle) cerrarModalDetalle(); });

  async function abrirModalDetalle(idConsulta) {
    contenidoDetalle.innerHTML = `<p style="color:#aaa;text-align:center;padding:20px 0">Cargando...</p>`;
    modalDetalle.classList.add("activo");
    try {
      const c = await api.get(`/historial/${idMascota}/detalle/${idConsulta}`);
      renderizarDetalle(c);
    } catch (error) {
      contenidoDetalle.innerHTML = `<p style="color:#c0392b">${error.message}</p>`;
    }
  }

  function cerrarModalDetalle() { modalDetalle.classList.remove("activo"); }

  function renderizarDetalle(c) {
    const fecha = new Date(c.fecha_hora).toLocaleString("es-UY", {
      day: "numeric", month: "long", year: "numeric", hour: "2-digit", minute: "2-digit",
    });
    const secTrat = c.tratamientos?.length > 0
      ? `<hr class="separador"/><p class="detalle-etiqueta">Tratamientos</p><div class="lista-items">${c.tratamientos.map(t => `<div class="item-card"><strong>${t.nombre}</strong><small>${t.descripcion || "Sin descripción"}</small>${t.finalizacion ? `<small>Fin: ${t.finalizacion}</small>` : ""}</div>`).join("")}</div>` : "";
    const secDosis = c.dosis?.length > 0
      ? `<hr class="separador"/><p class="detalle-etiqueta">Vacunas aplicadas</p><div class="lista-items">${c.dosis.map(d => `<div class="item-card"><strong>${d.nombre_vacuna}</strong><small>Dosis ${d.numero_dosis} — ${d.fecha_aplicacion}</small></div>`).join("")}</div>` : "";

    contenidoDetalle.innerHTML = `
      <div class="detalle-campo"><p class="detalle-etiqueta">Fecha</p><p class="detalle-valor">${fecha}</p></div>
      <div class="detalle-campo"><p class="detalle-etiqueta">Motivo</p><p class="detalle-valor">${c.motivo}</p></div>
      <div class="detalle-campo"><p class="detalle-etiqueta">Diagnóstico</p>
        ${c.diagnostico ? `<p class="detalle-valor">${c.diagnostico}</p>` : `<p class="detalle-vacio">No registrado</p>`}
      </div>${secTrat}${secDosis}`;
  }

  function mostrarMensaje(el, texto, tipo) {
    el.textContent = texto;
    el.classList.remove("mensaje-exito", "mensaje-error");
    el.classList.add(tipo === "exito" ? "mensaje-exito" : "mensaje-error");
    el.style.display = "block";
  }

  function ocultarMensaje(el) { el.style.display = "none"; el.textContent = ""; }
});