document.addEventListener("DOMContentLoaded", async () => {

  let idConsultaActual  = null;
  let vacunasCache      = [];
  let carnetCache       = [];
  let vacunasPendientes = new Set();
  let dosisPendientes   = [];
  let historialCargado  = false;
  let modoEdicion = false;
  let tratamientoEditando = null;
  let valoresOriginales = null;

  const idMascota = new URLSearchParams(location.search).get("id");

  const nombreEl  = document.getElementById("nombre");
  const detalleEl = document.getElementById("detalle");
  const fotoEl    = document.getElementById("foto");

  const modalConsulta   = document.getElementById("modal-consulta");
  const modalTratamiento = document.getElementById("modal-tratamiento");
  const formConsulta    = document.getElementById("form-consulta");
  const vacunasDiv      = document.getElementById("vacunas");

  const seccionTrats  = document.getElementById("seccion-tratamientos");
  const panelHistorial = document.getElementById("historial");

  // ───────── MASCOTA ─────────────────────────────────────────────────────────
  try {
    const m = await api.get(`/mascotas/${idMascota}`);
    nombreEl.textContent  = m.nombre;
    detalleEl.textContent = `${m.especie}${m.raza ? " · " + m.raza : ""}`;
    if (m.foto_url) {
      fotoEl.outerHTML = `<img src="${m.foto_url}" style="width:60px;height:60px;border-radius:50%;object-fit:cover;">`;
    } else {
      fotoEl.textContent = m.nombre.charAt(0).toUpperCase();
    }
  } catch (e) {
    console.error("Error cargando mascota", e);
    return;
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
      ? tratamiento.inicio.slice(0, 16)
      : "";

  document.getElementById("trat-finalizacion").value =
    tratamiento.finalizacion
      ? tratamiento.finalizacion.slice(0, 16)
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

    const nombre =
      document.getElementById("trat-nombre").value.trim();

    if (!nombre) {

      errorEl.textContent =
        "El nombre del tratamiento es obligatorio.";

      document.getElementById("trat-nombre").focus();

      return;
    }

    const inicio =
      document.getElementById("trat-inicio").value;

    const finalizacion =
      document.getElementById("trat-finalizacion").value;

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

      descripcion:
        document.getElementById("trat-descripcion")
          .value
          .trim() || null,

      frecuencia:
        document.getElementById("trat-frecuencia")
          .value
          .trim() || null,

      inicio:
        document.getElementById("trat-inicio")
          .value || null,

      finalizacion:
        document.getElementById("trat-finalizacion")
          .value || null,
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
    dosisPendientes   = [];
    idConsultaActual  = null;
    carnetCache       = [];
    vacunasCache      = [];

    modalConsulta.classList.add("activo");

    vacunasCache = await api.get("/vacunas/tipos");
    const response = await api.get(`/vacunas/${idMascota}/carnet`);
    carnetCache = Array.isArray(response) ? response : [];
    renderVacunas();
  };

  document.getElementById("cerrar-modal-consulta").onclick = () =>
    modalConsulta.classList.remove("activo");

  modalConsulta.addEventListener("click", (e) => {
    if (e.target === modalConsulta) modalConsulta.classList.remove("activo");
  });

  // ───────── RENDER VACUNAS ──────────────────────────────────────────────────
  function renderVacunas() {
    const esquema = carnetCache?.[0];
    vacunasDiv.innerHTML = `
      <hr style="margin:14px 0;">
      <h4 style="margin-bottom:8px;">Vacunas</h4>
      <button type="button" id="btn-add-vacuna" class="sec" style="margin-right:6px;">Agregar vacuna</button>
      <button type="button" id="btn-add-dosis"  class="sec">Agregar dosis</button>
      <div id="lista" style="display:flex;flex-wrap:wrap;gap:4px;margin-top:8px;"></div>
    `;
    const lista = document.getElementById("lista");

    document.getElementById("btn-add-vacuna").onclick = () => {
      lista.innerHTML = "";
      const yaTiene     = new Set((esquema?.vacunas || []).map(v => v.id_vacuna));
      const disponibles = vacunasCache.filter(v => !yaTiene.has(v.id_vacuna));
      disponibles.forEach(v => {
        const btn = document.createElement("button");
        btn.type = "button"; btn.textContent = v.nombre; btn.dataset.id = v.id_vacuna;
        btn.style.cssText = "padding:6px 10px;margin:4px;cursor:pointer;border-radius:6px;border:1px solid #ccc;background:white;";
        if (vacunasPendientes.has(v.id_vacuna)) btn.style.background = "#c8f7c5";
        btn.onclick = () => {
          if (vacunasPendientes.has(v.id_vacuna)) { vacunasPendientes.delete(v.id_vacuna); btn.style.background = "white"; }
          else { vacunasPendientes.add(v.id_vacuna); btn.style.background = "#c8f7c5"; }
        };
        lista.appendChild(btn);
      });
    };

    document.getElementById("btn-add-dosis").onclick = () => {
      lista.innerHTML = "";
      const vacunasActivas = carnetCache?.[0]?.vacunas || [];
      vacunasActivas.forEach(v => {
        const btn = document.createElement("button");
        btn.type = "button"; btn.textContent = v.nombre; btn.dataset.id = v.id_esquema_vacuna;
        btn.style.cssText = "padding:6px 10px;margin:4px;cursor:pointer;border-radius:6px;border:1px solid #ccc;background:white;";
        const sel = dosisPendientes.find(d => d.id_esquema_vacuna === v.id_esquema_vacuna);
        if (sel) btn.style.background = "#ffd699";
        btn.onclick = () => {
          const idx = dosisPendientes.findIndex(d => d.id_esquema_vacuna === v.id_esquema_vacuna);
          if (idx >= 0) { dosisPendientes.splice(idx, 1); btn.style.background = "white"; }
          else {
            dosisPendientes.push({ id_esquema_vacuna: v.id_esquema_vacuna, fecha_aplicacion: new Date().toISOString().split("T")[0], id_consulta: null });
            btn.style.background = "#ffd699";
          }
        };
        lista.appendChild(btn);
      });
    };
  }

  // ───────── GUARDAR CONSULTA ────────────────────────────────────────────────
  formConsulta.onsubmit = async (e) => {
    e.preventDefault();
    try {
      const res = await api.post("/historial/consultas", {
        id_mascota:  idMascota,
        motivo:      document.getElementById("motivo").value,
        diagnostico: document.getElementById("diag").value
      });
      idConsultaActual = res?.id_consulta;
      if (!idConsultaActual) throw new Error("No se generó idConsultaActual");

      const esquemaId = carnetCache?.[0]?.id_esquema;
      for (let idVacuna of vacunasPendientes) {
        await api.post(`/vacunas/${esquemaId}/vacunas/${idVacuna}`);
      }
      for (let dosisObj of dosisPendientes) {
        const vetId = localStorage.getItem("veterinaria_id");
        if (!vetId || vetId === "null" || vetId === "undefined") throw new Error("Veterinaria no válida en sesión");
        await api.post("/vacunas/dosis", {
          id_esquema_vacuna: dosisObj.id_esquema_vacuna,
          fecha_aplicacion:  dosisObj.fecha_aplicacion,
          id_consulta:       idConsultaActual
        }, { headers: { "x-veterinaria-id": vetId } });
      }

      modalConsulta.classList.remove("activo");
      vacunasPendientes.clear();
      dosisPendientes = []; vacunasCache = []; carnetCache = [];

      // si el historial estaba abierto, refrescarlo
      if (panelHistorial.style.display === "block") {
        historialCargado = false;
        await cargarHistorial();
      }
    } catch (err) {
      console.error("Error guardando consulta", err);
      alert("Error guardando consulta. Revisá la consola.");
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
  panelHistorial.innerHTML = `<p class="cargando">Cargando...</p>`;
  try {
    const response = await api.get(`/historial/${idMascota}/unificado`);
    const eventos = response.eventos;
    historialCargado = true;

    if (eventos.length === 0) {
      panelHistorial.innerHTML = `<p class="sin-datos">No hay eventos en el historial.</p>`;
      return;
    }

    panelHistorial.innerHTML = eventos.map(e => renderEvento(e)).join("");

    // Hacer consultas clickeables
    panelHistorial.querySelectorAll('[data-tipo="consulta"]').forEach(btn => {
      btn.onclick = async () => {
        // Abrir modal con detalle de consulta
        try {
          const detalle = await api.get(`/historial/${idMascota}/detalle/${btn.dataset.id}`);
          mostrarDetalleConsulta(detalle);
        } catch (err) {
          alert(`Error: ${err.message}`);
        }
      };
    });

  } catch (e) {
    panelHistorial.innerHTML = `<p class="error-panel">${e.message}</p>`;
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
  // implementar modal simple o reutilizar el de consulta
  const html = `
    <p><b>Motivo:</b> ${detalle.motivo}</p>
    <p><b>Diagnóstico:</b> ${detalle.diagnostico || "No registrado"}</p>
    ${detalle.dosis?.length > 0 ? `
      <p><b>Vacunas:</b></p>
      <ul>${detalle.dosis.map(d => `<li>${d.nombre_vacuna} (dosis ${d.numero_dosis})</li>`).join("")}</ul>
    ` : ""}
  `;
  alert(html); 
};
});
