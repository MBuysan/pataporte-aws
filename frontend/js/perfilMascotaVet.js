document.addEventListener("DOMContentLoaded", async () => {

  let idConsultaActual = null;
  let vacunasCache = [];
  let carnetCache = [];

  let vacunasPendientes = new Set();
  let dosisPendientes = []; // ahora es un array de objetos completos

  const idMascota = new URLSearchParams(location.search).get("id");

  const nombre = document.getElementById("nombre");
  const detalle = document.getElementById("detalle");
  const foto = document.getElementById("foto");

  const modal = document.getElementById("modal");
  const form = document.getElementById("form");

  const historial = document.getElementById("historial");
  const tratamientos = document.getElementById("tratamientos");

  const vacunasDiv = document.getElementById("vacunas");

  // ───────── MASCOTA ─────────
  try {
    const m = await api.get(`/mascotas/${idMascota}`);
    nombre.textContent = m.nombre;
    detalle.textContent = `${m.especie} · ${m.raza}`;
    if (m.foto_url) {
      foto.outerHTML = `<img src="${m.foto_url}" style="width:60px;height:60px;border-radius:50%;">`;
    }
  } catch (e) {
    console.error("Error cargando mascota", e);
    return;
  }

  // ───────── ABRIR CONSULTA ─────────
  document.getElementById("btn-consulta").onclick = async () => {

    vacunasPendientes = new Set();
    dosisPendientes = [];
    idConsultaActual = null;
    carnetCache = [];
    vacunasCache = [];

    modal.classList.add("activo");

    if (!document.getElementById("cerrar-modal")) {
      const btnCerrar = document.createElement("button");
      btnCerrar.id = "cerrar-modal";
      btnCerrar.textContent = "✕";
      btnCerrar.style.position = "absolute";
      btnCerrar.style.top = "10px";
      btnCerrar.style.right = "10px";
      btnCerrar.style.background = "none";
      btnCerrar.style.border = "none";
      btnCerrar.style.fontSize = "20px";
      btnCerrar.style.cursor = "pointer";
      modal.appendChild(btnCerrar);
      btnCerrar.onclick = () => modal.classList.remove("activo");
    }

    vacunasCache = await api.get("/vacunas/tipos");

    const response = await api.get(`/vacunas/${idMascota}/carnet`);
    carnetCache = Array.isArray(response) ? response : [];
    renderVacunas();
  };

  // ───────── RENDER VACUNAS ─────────
  function renderVacunas() {
    const esquema = carnetCache?.[0];
    vacunasDiv.innerHTML = `
      <hr>
      <h4>Vacunas</h4>
      <button type="button" id="btn-add-vacuna">Agregar vacuna</button>
      <button type="button" id="btn-add-dosis">Agregar dosis</button>
      <div id="lista" style="display:flex; flex-wrap:wrap; gap:4px;"></div>
    `;
    const lista = document.getElementById("lista");

    // ── AGREGAR VACUNA
    document.getElementById("btn-add-vacuna").onclick = () => {
      lista.innerHTML = "";
      const yaTiene = new Set((esquema?.vacunas || []).map(v => v.id_vacuna));
      const disponibles = vacunasCache.filter(v => !yaTiene.has(v.id_vacuna));

      disponibles.forEach(v => {
        const btn = document.createElement("button");
        btn.type = "button";
        btn.textContent = v.nombre;
        btn.dataset.id = v.id_vacuna;
        btn.style.padding = "6px";
        btn.style.margin = "4px";
        btn.style.cursor = "pointer";
        if (vacunasPendientes.has(v.id_vacuna)) btn.style.background = "#c8f7c5";

        btn.onclick = () => {
          if (vacunasPendientes.has(v.id_vacuna)) {
            vacunasPendientes.delete(v.id_vacuna);
            btn.style.background = "";
          } else {
            vacunasPendientes.add(v.id_vacuna);
            btn.style.background = "#c8f7c5";
          }
        };

        lista.appendChild(btn);
      });
    };

    // ── AGREGAR DOSIS
    document.getElementById("btn-add-dosis").onclick = () => {
      lista.innerHTML = "";
      const vacunasActivas = carnetCache?.[0]?.vacunas || [];

      vacunasActivas.forEach(v => {
        const btn = document.createElement("button");
        btn.type = "button";
        btn.textContent = v.nombre;
        btn.dataset.id = v.id_esquema_vacuna;
        btn.style.padding = "6px";
        btn.style.margin = "4px";
        btn.style.cursor = "pointer";

        const seleccionado = dosisPendientes.find(d => d.id_esquema_vacuna === v.id_esquema_vacuna);
        if (seleccionado) btn.style.background = "#ffd699";

        btn.onclick = () => {
          const index = dosisPendientes.findIndex(d => d.id_esquema_vacuna === v.id_esquema_vacuna);
          if (index >= 0) {
            dosisPendientes.splice(index, 1);
            btn.style.background = "";
          } else {
            dosisPendientes.push({
              id_esquema_vacuna: v.id_esquema_vacuna,
              fecha_aplicacion: new Date().toISOString().split("T")[0],
              id_consulta: null
            });
            btn.style.background = "#ffd699";
          }
        };

        lista.appendChild(btn);
      });
    };
  }

  // ───────── GUARDAR CONSULTA ─────────
  form.onsubmit = async (e) => {
    e.preventDefault();

    try {
      // 1️⃣ Crear consulta
      const res = await api.post("/historial/consultas", {
        id_mascota: idMascota,
        motivo: document.getElementById("motivo").value,
        diagnostico: document.getElementById("diag").value
      });

      idConsultaActual = res?.id_consulta;
      if (!idConsultaActual) throw new Error("No se generó idConsultaActual");

      const esquemaId = carnetCache?.[0]?.id_esquema;

      // 2️⃣ Guardar vacunas
      for (let idVacuna of vacunasPendientes) {
        await api.post(`/vacunas/${esquemaId}/vacunas/${idVacuna}`);
      }

            // 3️⃣ Guardar dosis
      for (let dosisObj of dosisPendientes) {

          const vetId = localStorage.getItem("veterinaria_id");

          if (!vetId || vetId === "null" || vetId === "undefined") {
              console.error("VET ID INVALIDO:", vetId);
              throw new Error("Veterinaria no válida en sesión");
          }

          const payload = {
              id_esquema_vacuna: dosisObj.id_esquema_vacuna,
              fecha_aplicacion: dosisObj.fecha_aplicacion,
              id_consulta: idConsultaActual
          };

          await api.post("/vacunas/dosis", payload, {
              headers: {
                  "x-veterinaria-id": vetId
              }
          });
      }

      modal.classList.remove("activo");
      vacunasPendientes.clear();
      dosisPendientes = [];
      vacunasCache = [];
      carnetCache = [];

    } catch (err) {
      console.error("Error guardando consulta", err);
      alert("Error guardando consulta. Revisa la consola.");
    }
  };

  // ───────── HISTORIAL ─────────
  document.getElementById("btn-historial").onclick = async () => {
    const data = await api.get(`/historial/${idMascota}/consultas`);
    historial.style.display = "block";
    historial.innerHTML = data.map(c => `<div class="fila">${c.fecha_hora} - ${c.motivo}</div>`).join("");
  };

  // ───────── TRATAMIENTOS ─────────
  const modalTrat      = document.getElementById("modal-tratamiento");
  const formTrat       = document.getElementById("form-tratamiento");
  const mensajeTrat    = document.getElementById("trat-mensaje");
  let tratamientosCargados = false;

  document.getElementById("btn-nuevo-tratamiento").onclick = () => {
    formTrat.reset();
    mensajeTrat.textContent = "";
    modalTrat.classList.add("activo");
  };

  document.getElementById("cerrar-modal-tratamiento").onclick = () =>
    modalTrat.classList.remove("activo");

  document.getElementById("btn-tratamientos").onclick = async () => {
    const abierto = tratamientos.style.display === "block";
    tratamientos.style.display = abierto ? "none" : "block";
    if (!abierto) await renderTratamientos();
  };

  async function renderTratamientos() {
    tratamientos.innerHTML = `<p style="color:#aaa;padding:8px">Cargando...</p>`;
    try {
      const data = await api.get(`/tratamientos/${idMascota}/activos`);
      tratamientosCargados = true;
      tratamientos.innerHTML = data.length === 0
        ? `<p style="color:#aaa;padding:8px">Sin tratamientos activos.</p>`
        : data.map(t => `
            <div class="card">
              <b>${t.nombre}</b>
              <div style="font-size:13px;color:#555;margin-top:4px">${t.descripcion || ""}</div>
              ${t.frecuencia ? `<div style="font-size:13px;color:#777;margin-top:2px">🕐 ${t.frecuencia}</div>` : ""}
              ${t.finalizacion ? `<div style="font-size:12px;color:#999;margin-top:4px">Finaliza: ${new Date(t.finalizacion).toLocaleDateString("es-UY")}</div>` : ""}
            </div>`).join("");
    } catch (e) {
      tratamientos.innerHTML = `<p style="color:red;padding:8px">${e.message}</p>`;
    }
  }

  formTrat.onsubmit = async (e) => {
  e.preventDefault();
  mensajeTrat.textContent = "";

  const payload = {
    nombre:       document.getElementById("trat-nombre").value.trim(),
    descripcion:  document.getElementById("trat-descripcion").value.trim() || null,
    frecuencia:   document.getElementById("trat-frecuencia").value.trim() || null,
    inicio:       document.getElementById("trat-inicio").value || null,
    finalizacion: document.getElementById("trat-finalizacion").value || null,
  };

  try {
    await api.post(`/tratamientos/${idMascota}`, payload);  // nueva URL
    modalTrat.classList.remove("activo");
    tratamientosCargados = false;
    if (tratamientos.style.display === "block") await renderTratamientos();
  } catch (err) {
    mensajeTrat.textContent = err.message || "Error al guardar el tratamiento.";
  }
  }
});