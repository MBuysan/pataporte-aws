document.addEventListener("DOMContentLoaded", async () => {

  let idConsultaActual = null;
  let vacunasCache     = [];
  let carnetCache      = [];
  let vacunasPendientes = new Set();
  let dosisPendientes   = [];

  let tratamientosCargados = false;
  let historialCargado     = false;

  const idMascota = new URLSearchParams(location.search).get("id");

  const nombreEl  = document.getElementById("nombre");
  const detalleEl = document.getElementById("detalle");
  const fotoEl    = document.getElementById("foto");
  const modal     = document.getElementById("modal");
  const form      = document.getElementById("form");
  const vacunasDiv = document.getElementById("vacunas");

  const panelHistorial    = document.getElementById("historial");
  const panelTratamientos = document.getElementById("panel-tratamientos");
  const listaTrats        = document.getElementById("lista-tratamientos");

  const formTratContainer = document.getElementById("form-trat-container");
  const inputNombre       = document.getElementById("trat-nombre");
  const inputDesc         = document.getElementById("trat-descripcion");
  const inputFrecuencia   = document.getElementById("trat-frecuencia");
  const inputInicio       = document.getElementById("trat-inicio");
  const inputFin          = document.getElementById("trat-finalizacion");
  const errorTrat         = document.getElementById("trat-error");

  // ───────── MASCOTA ─────────────────────────────────────────────────────────
  try {
    const m = await api.get(`/mascotas/${idMascota}`);
    nombreEl.textContent  = m.nombre;
    detalleEl.textContent = `${m.especie} · ${m.raza || ""}`;
    if (m.foto_url) {
      fotoEl.outerHTML = `<img src="${m.foto_url}" style="width:60px;height:60px;border-radius:50%;object-fit:cover;">`;
    } else {
      fotoEl.textContent = m.nombre.charAt(0).toUpperCase();
    }
  } catch (e) {
    console.error("Error cargando mascota", e);
    return;
  }

  // ───────── MODAL CONSULTA ──────────────────────────────────────────────────
  document.getElementById("btn-consulta").onclick = async () => {
    vacunasPendientes = new Set();
    dosisPendientes   = [];
    idConsultaActual  = null;
    carnetCache       = [];
    vacunasCache      = [];

    modal.classList.add("activo");

    vacunasCache = await api.get("/vacunas/tipos");
    const response = await api.get(`/vacunas/${idMascota}/carnet`);
    carnetCache = Array.isArray(response) ? response : [];
    renderVacunas();
  };

  document.getElementById("cerrar-modal").onclick = () => modal.classList.remove("activo");

  // ───────── RENDER VACUNAS ──────────────────────────────────────────────────
  function renderVacunas() {
    const esquema = carnetCache?.[0];
    vacunasDiv.innerHTML = `
      <hr style="margin:12px 0;">
      <h4 style="margin-bottom:8px;">Vacunas</h4>
      <button type="button" id="btn-add-vacuna" class="sec">Agregar vacuna</button>
      <button type="button" id="btn-add-dosis"  class="sec" style="margin-left:6px;">Agregar dosis</button>
      <div id="lista" style="display:flex;flex-wrap:wrap;gap:4px;margin-top:8px;"></div>
    `;
    const lista = document.getElementById("lista");

    document.getElementById("btn-add-vacuna").onclick = () => {
      lista.innerHTML = "";
      const yaTiene    = new Set((esquema?.vacunas || []).map(v => v.id_vacuna));
      const disponibles = vacunasCache.filter(v => !yaTiene.has(v.id_vacuna));
      disponibles.forEach(v => {
        const btn = document.createElement("button");
        btn.type = "button"; btn.textContent = v.nombre; btn.dataset.id = v.id_vacuna;
        btn.style.cssText = "padding:6px 10px;margin:4px;cursor:pointer;border-radius:6px;border:1px solid #ccc;";
        if (vacunasPendientes.has(v.id_vacuna)) btn.style.background = "#c8f7c5";
        btn.onclick = () => {
          if (vacunasPendientes.has(v.id_vacuna)) { vacunasPendientes.delete(v.id_vacuna); btn.style.background = ""; }
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
        btn.style.cssText = "padding:6px 10px;margin:4px;cursor:pointer;border-radius:6px;border:1px solid #ccc;";
        const seleccionado = dosisPendientes.find(d => d.id_esquema_vacuna === v.id_esquema_vacuna);
        if (seleccionado) btn.style.background = "#ffd699";
        btn.onclick = () => {
          const index = dosisPendientes.findIndex(d => d.id_esquema_vacuna === v.id_esquema_vacuna);
          if (index >= 0) { dosisPendientes.splice(index, 1); btn.style.background = ""; }
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
  form.onsubmit = async (e) => {
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
      modal.classList.remove("activo");
      vacunasPendientes.clear();
      dosisPendientes = []; vacunasCache = []; carnetCache = [];

      // refrescar historial si estaba abierto
      if (panelHistorial.style.display === "block") {
        historialCargado = false;
        await cargarHistorial();
      }
    } catch (err) {
      console.error("Error guardando consulta", err);
      alert("Error guardando consulta. Revisá la consola.");
    }
  };

  // ───────── PANEL HISTORIAL ─────────────────────────────────────────────────
  document.getElementById("btn-historial").onclick = async () => {
    const abierto = panelHistorial.style.display === "block";
    panelHistorial.style.display = abierto ? "none" : "block";
    document.getElementById("btn-historial").textContent = abierto ? "Historial" : "Cerrar historial";
    if (!abierto && !historialCargado) await cargarHistorial();
  };

  async function cargarHistorial() {
    panelHistorial.innerHTML = `<p class="cargando">Cargando...</p>`;
    try {
      const data = await api.get(`/historial/${idMascota}/consultas`);
      historialCargado = true;
      panelHistorial.innerHTML = data.length === 0
        ? `<p class="sin-datos">No hay consultas registradas.</p>`
        : data.map(c => {
            const f = new Date(c.fecha_hora);
            const fecha = f.toLocaleDateString("es-UY", { day: "numeric", month: "short", year: "numeric" })
                        + ", " + f.toLocaleTimeString("es-UY", { hour: "2-digit", minute: "2-digit" });
            return `<div class="fila"><b>${fecha}</b> — ${c.motivo}</div>`;
          }).join("");
    } catch (e) {
      panelHistorial.innerHTML = `<p class="error-panel">${e.message}</p>`;
    }
  }

  // ───────── PANEL TRATAMIENTOS ──────────────────────────────────────────────
  document.getElementById("btn-tratamientos").onclick = async () => {
    const abierto = panelTratamientos.style.display === "block";
    panelTratamientos.style.display = abierto ? "none" : "block";
    document.getElementById("btn-tratamientos").textContent = abierto ? "Tratamientos" : "Cerrar tratamientos";

    // cerrar el formulario si estaba abierto
    if (abierto) { formTratContainer.style.display = "none"; }

    if (!abierto && !tratamientosCargados) await cargarTratamientos();
  };

  async function cargarTratamientos() {
    listaTrats.innerHTML = `<p class="cargando">Cargando...</p>`;
    try {
      const data = await api.get(`/tratamientos/${idMascota}/activos`);
      tratamientosCargados = true;
      renderTratamientos(data);
    } catch (e) {
      listaTrats.innerHTML = `<p class="error-panel">${e.message}</p>`;
    }
  }

  function renderTratamientos(data) {
    if (data.length === 0) {
      listaTrats.innerHTML = `<p class="sin-datos">Esta mascota no tiene tratamientos registrados.</p>`;
      return;
    }
    listaTrats.innerHTML = data.map(t => {
      const inicio = t.inicio
        ? new Date(t.inicio).toLocaleDateString("es-UY", { day: "numeric", month: "short", year: "numeric" })
        : "—";
      const fin = t.finalizacion
        ? new Date(t.finalizacion).toLocaleDateString("es-UY", { day: "numeric", month: "short", year: "numeric" })
        : "Sin fecha de fin";
      return `
        <div class="card">
          <div class="card-titulo">${t.nombre}</div>
          ${t.descripcion ? `<div class="card-desc">${t.descripcion}</div>` : ""}
          ${t.frecuencia  ? `<div class="card-freq">🕐 ${t.frecuencia}</div>` : ""}
          <div class="card-meta">Inicio: ${inicio} · Fin: ${fin}</div>
        </div>`;
    }).join("");
  }

  // ── Abrir / cerrar formulario inline ──
  document.getElementById("btn-nuevo-tratamiento").onclick = () => {
    const visible = formTratContainer.style.display === "block";
    formTratContainer.style.display = visible ? "none" : "block";
    if (!visible) {
      // limpiar formulario al abrir
      inputNombre.value = ""; inputDesc.value = "";
      inputFrecuencia.value = ""; inputInicio.value = "";
      inputFin.value = ""; errorTrat.textContent = "";
      inputNombre.focus();
    }
  };

  document.getElementById("btn-cancelar-trat").onclick = () => {
    formTratContainer.style.display = "none";
    errorTrat.textContent = "";
  };

  // ── Guardar nuevo tratamiento ──
  document.getElementById("btn-guardar-trat").onclick = async () => {
    errorTrat.textContent = "";

    if (!inputNombre.value.trim()) {
      errorTrat.textContent = "El nombre del tratamiento es obligatorio.";
      inputNombre.focus();
      return;
    }

    const payload = {
      nombre:       inputNombre.value.trim(),
      descripcion:  inputDesc.value.trim()       || null,
      frecuencia:   inputFrecuencia.value.trim() || null,
      inicio:       inputInicio.value            || null,
      finalizacion: inputFin.value               || null,
    };

    try {
      await api.post(`/tratamientos/${idMascota}`, payload);

      // cerrar form, forzar recarga de la lista
      formTratContainer.style.display = "none";
      tratamientosCargados = false;
      await cargarTratamientos();

    } catch (err) {
      errorTrat.textContent = err.message || "Error al guardar el tratamiento.";
    }
  };

});