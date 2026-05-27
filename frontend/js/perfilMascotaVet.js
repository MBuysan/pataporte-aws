document.addEventListener("DOMContentLoaded", async () => {

  let idConsultaActual = null;
  let vacunasCache = [];
  let carnetCache = [];
  let vacunasPendientes = new Set();
  let dosisPendientes = [];
  let historialCargado = false;
  let modoEdicion = false;
  let tratamientoEditando = null;
  let valoresOriginales = null;
  let especieMascota = null;

  const idMascota = new URLSearchParams(location.search).get("id");

  const nombreEl = document.getElementById("nombre");
  const detalleEl = document.getElementById("detalle");
  const fotoEl = document.getElementById("foto");

  const modalConsulta = document.getElementById("modal-consulta");
  const modalTratamiento = document.getElementById("modal-tratamiento");
  const formConsulta = document.getElementById("form-consulta");
  const vacunasDiv = document.getElementById("vacunas");

  const seccionTrats = document.getElementById("seccion-tratamientos");
  const panelHistorial = document.getElementById("historial");

  const btnVacunas = document.getElementById("btn-vacunas");
  const btnCert = document.getElementById("btn-certificado");

  btnVacunas.onclick = () => {
    window.location.href = `esquema-vacunas.html?id=${encodeURIComponent(idMascota)}&from=vet`;
  };

  btnCert.onclick = async () => {
    if (!confirm("¿Generar el Pataporte...")) return;

    btnCert.disabled    = true;
    btnCert.textContent = "Generando...";

    try {
      const res = await api.post(`/pataporte/${idMascota}`);

      alert(
        `Pataporte generado correctamente...`
      );

    } catch (err) {

      alert(`Error al generar el Pataporte: ${err.message}`);

    } finally {

      btnCert.disabled    = false;
      btnCert.textContent = "Generar Certificado";
    }
  };

  const modalDetalleConsulta = document.getElementById("modal-detalle-consulta");
  const contenidoDetalleConsulta = document.getElementById("contenido-detalle-consulta");
  const cerrarModalDetalleConsulta = document.getElementById("cerrar-modal-detalle-consulta");

  // ───────── MASCOTA ─────────────────────────────────────────────────────────

  let mascotaActual = null;

  try {
    mascotaActual = await api.get(`/mascotas/${idMascota}`);
    nombreEl.textContent = mascotaActual.nombre;
    detalleEl.textContent = `${mascotaActual.especie}${mascotaActual.raza ? " · " + mascotaActual.raza : ""}`;
    if (mascotaActual.foto_url) {
      fotoEl.outerHTML = `<img src="${mascotaActual.foto_url}" style="width:60px;height:60px;border-radius:50%;object-fit:cover;">`;
    } else {
      fotoEl.textContent = mascotaActual.nombre.charAt(0).toUpperCase();
    }
  } catch (e) {
    console.error("Error cargando mascota", e);
    return;
  }

    if (mascotaActual.especie === "otro") {

      btnVacunas.style.display = "none";
      btnCert.style.display = "none";

  }

  // ───────── TRATAMIENTOS — carga automática al abrir el perfil ──────────────
  await cargarTratamientos();

  async function cargarTratamientos() {
    seccionTrats.innerHTML = `<p class="cargando">Cargando...</p>`;
    try {
      const data = await api.get(`/tratamientos/${idMascota}/activos`);
      renderTratamientos(data);
    } catch (e) {
      seccionTrats.innerHTML = `<p class="error-panel">${e.message}</p>`;
    }
  }

  function renderTratamientos(data) {

    if (data.length === 0) {
      seccionTrats.innerHTML =
        `<p class="sin-datos">Esta mascota no tiene tratamientos activos.</p>`;
      return;
    }

    seccionTrats.innerHTML = data.map(t => {

      const inicio = t.inicio
        ? new Date(t.inicio).toLocaleDateString("es-UY", {
          day: "numeric",
          month: "short",
          year: "numeric"
        })
        : "—";

      const fin = t.finalizacion
        ? new Date(t.finalizacion).toLocaleDateString("es-UY", {
          day: "numeric",
          month: "short",
          year: "numeric"
        })
        : "Sin fecha de fin";

      return `
      <div class="card">

        <div style="display:flex;justify-content:space-between;align-items:start;gap:10px;">

          <div style="flex:1;">

            <div class="card-titulo">${t.nombre}</div>

            ${t.descripcion
          ? `<div class="card-desc">${t.descripcion}</div>`
          : ""}

            ${t.frecuencia
          ? `<div class="card-freq">🕐 ${t.frecuencia}</div>`
          : ""}

            <div class="card-meta">
              Inicio: ${inicio} &nbsp;·&nbsp; Fin: ${fin}
            </div>

          </div>

          <button
            class="sec btn-editar-trat"
            data-id="${t.id_tratamiento}"
          >
            Editar
          </button>

        </div>

      </div>
    `;

    }).join("");

    // listeners despues de renderizar

    document.querySelectorAll(".btn-editar-trat").forEach(btn => {

      btn.onclick = () => {

        const tratamiento = data.find(
          t => t.id_tratamiento === btn.dataset.id
        );

        abrirModalEdicion(tratamiento);
      };
    });
  }

  function convertirUTCALocalInput(fechaUTC) {

    const fecha = new Date(fechaUTC);

    const year = fecha.getFullYear();
    const month = String(fecha.getMonth() + 1).padStart(2, "0");
    const day = String(fecha.getDate()).padStart(2, "0");

    const hours = String(fecha.getHours()).padStart(2, "0");
    const minutes = String(fecha.getMinutes()).padStart(2, "0");

    return `${year}-${month}-${day}T${hours}:${minutes}`;
  }

  function abrirModalEdicion(tratamiento) {

    modoEdicion = true;
    tratamientoEditando = tratamiento;

    document.querySelector("#modal-tratamiento h3").textContent =
      "Editar tratamiento";

    document.getElementById("btn-guardar-trat").textContent =
      "Guardar cambios";

    document.getElementById("trat-nombre").value =
      tratamiento.nombre || "";

    document.getElementById("trat-descripcion").value =
      tratamiento.descripcion || "";

    document.getElementById("trat-frecuencia").value =
      tratamiento.frecuencia || "";

    document.getElementById("trat-inicio").value =
      tratamiento.inicio
        ? convertirUTCALocalInput(tratamiento.inicio)
        : "";

    document.getElementById("trat-finalizacion").value =
      tratamiento.finalizacion
        ? convertirUTCALocalInput(tratamiento.finalizacion)
        : "";

    valoresOriginales = obtenerValoresFormulario();

    document.getElementById("trat-error").textContent = "";

    modalTratamiento.classList.add("activo");
  }

  function obtenerValoresFormulario() {

    return {
      nombre: document.getElementById("trat-nombre").value.trim(),

      descripcion:
        document.getElementById("trat-descripcion").value.trim(),

      frecuencia:
        document.getElementById("trat-frecuencia").value.trim(),

      inicio:
        document.getElementById("trat-inicio").value,

      finalizacion:
        document.getElementById("trat-finalizacion").value
    };
  }

  function huboCambios() {

    const actuales = obtenerValoresFormulario();

    return JSON.stringify(actuales)
      !== JSON.stringify(valoresOriginales);
  }

  // ───────── MODAL TRATAMIENTO ───────────────────────────────────────────────
  document.getElementById("btn-nuevo-tratamiento").onclick = () => {

    modoEdicion = false;
    tratamientoEditando = null;
    valoresOriginales = null;

    document.querySelector("#modal-tratamiento h3").textContent =
      "Nuevo tratamiento";

    document.getElementById("btn-guardar-trat").textContent =
      "Guardar tratamiento";

    // limpiar formulario
    document.getElementById("trat-nombre").value = "";
    document.getElementById("trat-descripcion").value = "";
    document.getElementById("trat-frecuencia").value = "";
    document.getElementById("trat-inicio").value = "";
    document.getElementById("trat-finalizacion").value = "";

    document.getElementById("trat-error").textContent = "";

    modalTratamiento.classList.add("activo");

    document.getElementById("trat-nombre").focus();
  };

  document.getElementById("cerrar-modal-tratamiento").onclick = () => {
    modalTratamiento.classList.remove("activo");
  };

  // cerrar haciendo click fuera

  modalTratamiento.addEventListener("click", (e) => {

    if (e.target === modalTratamiento) {
      modalTratamiento.classList.remove("activo");
    }
  });

  document.getElementById("btn-guardar-trat").onclick = async () => {

    const errorEl = document.getElementById("trat-error");

    errorEl.textContent = "";

    const nombre = document.getElementById("trat-nombre").value.trim();
    const descripcion = document.getElementById("trat-descripcion").value.trim();
    const frecuencia = document.getElementById("trat-frecuencia").value.trim();
    const inicio = document.getElementById("trat-inicio").value;
    const finalizacion = document.getElementById("trat-finalizacion").value;

    if (!nombre) {
      errorEl.textContent = "El nombre del tratamiento es obligatorio.";
      document.getElementById("trat-nombre").focus();
      return;
    }

    if (!descripcion) {
      errorEl.textContent = "La descripción del tratamiento es obligatoria.";
      document.getElementById("trat-descripcion").focus();
      return;
    }

    if (!frecuencia) {
      errorEl.textContent = "La frecuencia del tratamiento es obligatoria.";
      document.getElementById("trat-frecuencia").focus();
      return;
    }

    if (!inicio) {
      errorEl.textContent = "La fecha de inicio es obligatoria.";
      document.getElementById("trat-inicio").focus();
      return;
    }

    // validacion frontend fechas

    if (inicio && finalizacion) {

      const fechaInicio = new Date(inicio);
      const fechaFin = new Date(finalizacion);

      if (fechaFin < fechaInicio) {

        errorEl.textContent =
          "La fecha de finalización no puede ser anterior a la fecha de inicio.";

        return;
      }
    }

    // validar cambios en modo edicion

    if (modoEdicion && !huboCambios()) {

      errorEl.textContent =
        "No se realizaron cambios en el tratamiento.";

      return;
    }

    const payload = {
      nombre,
      descripcion,
      frecuencia,
      inicio: inicio ? new Date(inicio).toISOString() : null,
      finalizacion: finalizacion ? new Date(finalizacion).toISOString() : null,
    };

    try {

      // EDITAR

      if (modoEdicion) {

        await api.patch(
          `/tratamientos/${tratamientoEditando.id_tratamiento}`,
          payload
        );

      }

      // CREAR

      else {

        await api.post(
          `/tratamientos/${idMascota}`,
          payload
        );
      }

      modalTratamiento.classList.remove("activo");

      await cargarTratamientos();

    } catch (err) {

      errorEl.textContent =
        err.message || "Error al guardar el tratamiento.";
    }
  };

  // ───────── MODAL CONSULTA ──────────────────────────────────────────────────
  document.getElementById("btn-consulta").onclick = async () => {
    vacunasPendientes = new Set();
    dosisPendientes = [];
    idConsultaActual = null;
    carnetCache = [];
    vacunasCache = [];

    // limpia formulario
    formConsulta.reset();
    vacunasDiv.innerHTML = "";

    modalConsulta.classList.add("activo");

    if (mascotaActual.especie !== "otro") {
      vacunasCache = await api.get(`/vacunas/tipos?especie=${mascotaActual.especie}`);
      const response = await api.get(`/vacunas/${idMascota}/carnet`);
      carnetCache = Array.isArray(response) ? response : [];
      renderVacunas();
    }
  };

  document.getElementById("cerrar-modal-consulta").onclick = () =>
    modalConsulta.classList.remove("activo");

  modalConsulta.addEventListener("click", (e) => {
    if (e.target === modalConsulta) modalConsulta.classList.remove("activo");
  });

  if (modalDetalleConsulta && cerrarModalDetalleConsulta) {
    cerrarModalDetalleConsulta.onclick = () =>
      modalDetalleConsulta.classList.remove("activo");

    modalDetalleConsulta.addEventListener("click", (e) => {
      if (e.target === modalDetalleConsulta) {
        modalDetalleConsulta.classList.remove("activo");
      }
    });
  }

  // ───────── RENDER VACUNAS ──────────────────────────────────────────────────
  function renderVacunas() {
    const esquema = carnetCache?.[0];
    const vacunasEsquema = esquema?.vacunas || [];
    const hayVacunasActivas = vacunasEsquema.some(v => v.dosis_aplicadas < v.dosis_requeridas);

    vacunasDiv.innerHTML = `
      <hr style="margin:14px 0;">
      <h4 style="margin-bottom:10px;">Vacunas</h4>
      <button type="button" id="btn-add-vacuna" class="sec" style="margin-right:6px;">+ Agregar vacuna</button>
      ${hayVacunasActivas ? `<button type="button" id="btn-add-dosis" class="sec">+ Registrar dosis</button>` : ""}
      <div id="lista-vacunas-nuevas" style="margin-top:10px;"></div>
      <div id="lista-dosis" style="margin-top:4px;"></div>
    `;

    document.getElementById("btn-add-vacuna").onclick = () => {
      const contenedor = document.getElementById("lista-vacunas-nuevas");
      contenedor.innerHTML = "";

      const yaTiene = new Set(vacunasEsquema.map(v => v.id_vacuna));
      const disponibles = vacunasCache.filter(v => !yaTiene.has(v.id_vacuna));

      if (disponibles.length === 0) {
        contenedor.innerHTML = `<p style="color:#888;font-size:13px;">Esta mascota ya tiene todas las vacunas disponibles.</p>`;
        return;
      }

      const titulo = document.createElement("p");
      titulo.textContent = "Seleccioná las vacunas a agregar:";
      titulo.style.cssText = "font-size:12px;color:#888;margin-bottom:6px;";
      contenedor.appendChild(titulo);

      disponibles.forEach(v => {
        const btn = document.createElement("button");
        btn.type = "button";
        btn.textContent = v.nombre;
        btn.dataset.id = v.id_vacuna;
        btn.style.cssText = "padding:6px 10px;margin:3px;cursor:pointer;border-radius:6px;border:1px solid #ccc;background:white;font-size:13px;";

        if (vacunasPendientes.has(v.id_vacuna)) {
          btn.style.background = "#c8f7c5";
          btn.style.borderColor = "#7bc67b";
        }

        btn.onclick = () => {
          if (vacunasPendientes.has(v.id_vacuna)) {
            vacunasPendientes.delete(v.id_vacuna);
            btn.style.background = "white";
            btn.style.borderColor = "#ccc";
            // si tenía dosis pendiente asociada, quitarla también
            const idx = dosisPendientes.findIndex(d => d.id_vacuna_nueva === v.id_vacuna);
            if (idx >= 0) dosisPendientes.splice(idx, 1);
          } else {
            vacunasPendientes.add(v.id_vacuna);
            btn.style.background = "#c8f7c5";
            btn.style.borderColor = "#7bc67b";

            // mostrar "registrar dosis" si todavía no está visible
            if (!document.getElementById("btn-add-dosis")) {
              const btnDosis = document.createElement("button");
              btnDosis.type = "button";
              btnDosis.id = "btn-add-dosis";
              btnDosis.className = "sec";
              btnDosis.textContent = "+ Registrar dosis";
              btnDosis.style.marginLeft = "6px";
              document.getElementById("btn-add-vacuna").insertAdjacentElement("afterend", btnDosis);
              _bindBtnAddDosis(vacunasEsquema);
            }
          }
        };

        contenedor.appendChild(btn);
      });
    };

    // ── Bind inicial del botón dosis (si ya había vacunas activas) ───────────
    if (hayVacunasActivas) {
      _bindBtnAddDosis(vacunasEsquema);
    }
  }

  function _bindBtnAddDosis(vacunasEsquema) {
    const btnDosis = document.getElementById("btn-add-dosis");
    if (!btnDosis) return;

    btnDosis.onclick = () => {
      const contenedor = document.getElementById("lista-dosis");
      contenedor.innerHTML = "";

    
      const vacunasActivas = vacunasEsquema.filter(v => v.dosis_aplicadas < v.dosis_requeridas);

      // vacunas nuevas seleccionadas en esta misma consulta
      const vacunasNuevas = vacunasCache
        .filter(v => vacunasPendientes.has(v.id_vacuna))
        .map(v => ({
          ...v,
          id_esquema_vacuna: null,
          dosis_aplicadas: 0,
          dosis_requeridas: v.cantidad_dosis_requeridas,
          esNueva: true,
        }));

      const todas = [...vacunasActivas, ...vacunasNuevas];

      if (todas.length === 0) {
        contenedor.innerHTML = `<p style="color:#888;font-size:13px;">No hay vacunas activas para registrar dosis.</p>`;
        return;
      }

      const titulo = document.createElement("p");
      titulo.textContent = "Seleccioná las dosis a registrar hoy:";
      titulo.style.cssText = "font-size:12px;color:#888;margin-bottom:6px;";
      contenedor.appendChild(titulo);

      todas.forEach(v => {
        const clave = v.esNueva ? `nueva:${v.id_vacuna}` : v.id_esquema_vacuna;

        const esUltimaDosis = v.dosis_aplicadas + 1 >= v.dosis_requeridas;

        const wrapper = document.createElement("div");
        wrapper.style.cssText = "display:flex;align-items:center;gap:8px;margin:4px 0;flex-wrap:wrap;";

        const btn = document.createElement("button");
        btn.type = "button";
        btn.textContent = v.esNueva
          ? `${v.nombre} (primera dosis)`
          : `${v.nombre} (${v.dosis_aplicadas}/${v.dosis_requeridas})`;
        btn.style.cssText = "padding:6px 10px;cursor:pointer;border-radius:6px;border:1px solid #ccc;background:white;font-size:13px;";

        const inputFecha = document.createElement("input");
        inputFecha.type = "date";
        inputFecha.style.cssText = "display:none;padding:5px 8px;border:1px solid #ddd;border-radius:6px;font-size:13px;";

        const labelFecha = document.createElement("span");
        labelFecha.textContent = esUltimaDosis ? "" : "Próxima dosis:";
        labelFecha.style.cssText = "display:none;font-size:12px;color:#888;";

        // restaurar estado si ya estaba seleccionada
        const selExistente = dosisPendientes.find(d => d._clave === clave);
        if (selExistente) {
          btn.style.background = "#ffd699";
          btn.style.borderColor = "#f0a500";

          if (!esUltimaDosis) {
            inputFecha.style.display = "block";
            labelFecha.style.display = "inline";
          }
          if (selExistente.fecha_proxima_dosis) inputFecha.value = selExistente.fecha_proxima_dosis;
        }

        btn.onclick = () => {
          const idx = dosisPendientes.findIndex(d => d._clave === clave);
          if (idx >= 0) {
            dosisPendientes.splice(idx, 1);
            btn.style.background = "white";
            btn.style.borderColor = "#ccc";
            inputFecha.style.display = "none";
            labelFecha.style.display = "none";
            inputFecha.value = "";
          } else {
            dosisPendientes.push({
              _clave: clave,
              id_esquema_vacuna: v.esNueva ? null : v.id_esquema_vacuna,
              id_vacuna_nueva: v.esNueva ? v.id_vacuna : null,
              fecha_aplicacion: new Date().toISOString().split("T")[0],
              fecha_proxima_dosis: null,
            });
            btn.style.background = "#ffd699";
            btn.style.borderColor = "#f0a500";
            if (!esUltimaDosis) {
            inputFecha.style.display = "block";
            labelFecha.style.display = "inline";
            }
          }
        };

        inputFecha.onchange = () => {
          const idx = dosisPendientes.findIndex(d => d._clave === clave);
          if (idx >= 0) dosisPendientes[idx].fecha_proxima_dosis = inputFecha.value || null;
        };

        wrapper.appendChild(btn);
        wrapper.appendChild(labelFecha);
        wrapper.appendChild(inputFecha);
        contenedor.appendChild(wrapper);
      });
    };
  }

  // ───────── GUARDAR CONSULTA ────────────────────────────────────────────────
  formConsulta.onsubmit = async (e) => {
    e.preventDefault();

    const vetId = localStorage.getItem("veterinario_id");
    if (!vetId || vetId === "null" || vetId === "undefined") {
      alert("Veterinario no válido en sesión.");
      return;
    }

    const consultaErrorEl = document.getElementById("consulta-error");
    if (consultaErrorEl) consultaErrorEl.textContent = "";

    const listaVacunasNuevas = document.getElementById("lista-vacunas-nuevas");
    if (listaVacunasNuevas && listaVacunasNuevas.children.length > 0) {
      if (vacunasPendientes.size === 0) {
        if (consultaErrorEl) {
          consultaErrorEl.textContent = "Debe seleccionar al menos una vacuna de la lista.";
        }
        return;
      }
    }

    const listaDosis = document.getElementById("lista-dosis");
    if (listaDosis && listaDosis.children.length > 0) {
      if (dosisPendientes.length === 0) {
        if (consultaErrorEl) {
          consultaErrorEl.textContent = "Debe seleccionar al menos una dosis a registrar.";
        }
        return;
      }
    }

    try {
      const payload = {
        id_mascota: idMascota,
        motivo: document.getElementById("motivo").value,
        diagnostico: document.getElementById("diag").value || null,
        nuevas_vacunas: [...vacunasPendientes],
        dosis: dosisPendientes.map(d => ({
          ...(d.id_vacuna_nueva
            ? { id_vacuna_nueva: d.id_vacuna_nueva }
            : { id_esquema_vacuna: d.id_esquema_vacuna }
          ),
          fecha_aplicacion: d.fecha_aplicacion,
          fecha_proxima_dosis: d.fecha_proxima_dosis || null,
        })),
      };

      await api.post("/historial/consultas", payload);

      modalConsulta.classList.remove("activo");
      vacunasPendientes = new Set();
      dosisPendientes = [];
      vacunasCache = [];
      carnetCache = [];

      if (panelHistorial.style.display === "block") {
        historialCargado = false;
        await cargarHistorial();
      }

    } catch (err) {
      console.error("Error guardando consulta", err);
      alert(err.message || "Error guardando consulta.");
    }
  };

  // ───────── PANEL HISTORIAL (toggle) ────────────────────────────────────────
  document.getElementById("btn-historial").onclick = async () => {
    const abierto = panelHistorial.style.display === "block";
    panelHistorial.style.display = abierto ? "none" : "block";
    document.getElementById("btn-historial").textContent = abierto ? "Historial" : "Cerrar historial";
    if (!abierto && !historialCargado) await cargarHistorial();
  };

  async function cargarHistorial() {
    panelHistorial.innerHTML =
      `<p class="cargando">Cargando...</p>`;

    try {

      const response =
        await api.get(`/historial/${idMascota}/unificado`);

      const eventos = response.eventos;

      historialCargado = true;

      if (eventos.length === 0) {

        panelHistorial.innerHTML =
          `<p class="sin-datos">No hay eventos en el historial.</p>`;

        return;
      }

      panelHistorial.innerHTML =
        eventos.map(e => renderEvento(e)).join("");

      // consultas clickeables

      panelHistorial
        .querySelectorAll('[data-tipo="consulta"]')
        .forEach(btn => {

          btn.onclick = async () => {

            try {

              const detalle = await api.get(
                `/historial/${idMascota}/detalle/${btn.dataset.id}`
              );

              mostrarDetalleConsulta(detalle);

            } catch (err) {

              panelHistorial.innerHTML += `
                <p class="error-panel">
                  No se pudo cargar el detalle:
                  ${err.message}
                </p>
              `;
            }
          };
        });

    } catch (e) {

      panelHistorial.innerHTML =
        `<p class="error-panel">${e.message}</p>`;
    }
  }

  function renderEvento(e) {
    const fecha = new Date(e.fecha).toLocaleDateString("es-UY", {
      day: "numeric", month: "short", year: "numeric"
    });
    const hora = new Date(e.fecha).toLocaleTimeString("es-UY", {
      hour: "2-digit", minute: "2-digit"
    });

    if (e.tipo === "consulta") {
      return `
      <button class="fila" data-tipo="consulta" data-id="${e.id}" style="display:flex;align-items:center;gap:10px;width:100%;">
        <span style="background:#e3f2fd;color:#1976d2;padding:4px 8px;border-radius:6px;font-size:10px;font-weight:bold;white-space:nowrap;">CONSULTA</span>
        <span style="flex:1;text-align:left;"><b>${fecha}, ${hora}</b> — ${e.motivo}</span>
        <span style="color:#ccc;font-size:18px;">›</span>
      </button>`;
    } else {
      // tratamiento
      const fin = e.finalizacion
        ? new Date(e.finalizacion).toLocaleDateString("es-UY", { day: "numeric", month: "short", year: "numeric" })
        : "Sin fecha de fin";
      const estado = e.finalizacion && new Date(e.finalizacion) < new Date()
        ? "FINALIZADO"
        : "ACTIVO";
      const colorEstado = estado === "FINALIZADO" ? "#bbb" : "#f57c00";

      return `
      <div class="card">
        <div style="display:flex;align-items:center;gap:8px;margin-bottom:6px;">
          <span style="background:#fff3e0;color:${colorEstado};padding:4px 8px;border-radius:6px;font-size:10px;font-weight:bold;">TRATAMIENTO · ${estado}</span>
          <span style="font-size:12px;color:#aaa;">${fecha}</span>
        </div>
        <div class="card-titulo">${e.nombre}</div>
        ${e.descripcion ? `<div class="card-desc">${e.descripcion}</div>` : ""}
        ${e.frecuencia ? `<div class="card-freq">🕐 ${e.frecuencia}</div>` : ""}
        <div class="card-meta">Finalización: ${fin}</div>
      </div>`;
    }
  }

  function mostrarDetalleConsulta(detalle) {
    const fecha = new Date(detalle.fecha_hora).toLocaleString("es-UY", {
      day: "numeric",
      month: "long",
      year: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });

    const vacunas = detalle.dosis?.length > 0
      ? `
      <hr style="border:none;border-top:1px solid #eee;margin:16px 0;" />
      <p style="font-size:12px;font-weight:bold;color:#999;text-transform:uppercase;letter-spacing:0.5px;margin-bottom:8px;">
        Vacunas aplicadas
      </p>
      ${detalle.dosis.map(d => `
        <div class="card">
          <div class="card-titulo">${d.nombre_vacuna}</div>
          <div class="card-meta">Dosis ${d.numero_dosis} — ${d.fecha_aplicacion}</div>
        </div>
      `).join("")}
    `
      : "";

    contenidoDetalleConsulta.innerHTML = `
    <div style="margin-bottom:14px;">
      <p style="font-size:12px;font-weight:bold;color:#999;text-transform:uppercase;letter-spacing:0.5px;margin-bottom:4px;">Fecha</p>
      <p style="font-size:15px;color:#222;">${fecha}</p>
    </div>

    <div style="margin-bottom:14px;">
      <p style="font-size:12px;font-weight:bold;color:#999;text-transform:uppercase;letter-spacing:0.5px;margin-bottom:4px;">Motivo</p>
      <p style="font-size:15px;color:#222;">${detalle.motivo}</p>
    </div>

    <div style="margin-bottom:14px;">
      <p style="font-size:12px;font-weight:bold;color:#999;text-transform:uppercase;letter-spacing:0.5px;margin-bottom:4px;">Diagnóstico</p>
      <p style="font-size:15px;color:#222;">
        ${detalle.diagnostico || "No registrado"}
      </p>
    </div>

    ${vacunas}
  `;

    modalDetalleConsulta.classList.add("activo");
  }
});
