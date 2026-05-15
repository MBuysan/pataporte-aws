// Vista del tutor — solo lectura.

document.addEventListener("DOMContentLoaded", async () => {

  const params    = new URLSearchParams(window.location.search);
  const idMascota = params.get("id");

  const nombreEl      = document.getElementById("nombre-mascota");
  const detalleEl     = document.getElementById("detalle-mascota");
  const fotoEl        = document.getElementById("foto-mascota");
  const mensajePagina = document.getElementById("mensaje-pagina");
  const seccionTrat   = document.getElementById("seccion-tratamientos");
  const seccionHist   = document.getElementById("seccion-historial");
  const btnHist       = document.getElementById("btn-historial");
  const btnVacunas    = document.getElementById("btn-vacunas");
  const btnCert       = document.getElementById("btn-certificado");
  const modalDetalle     = document.getElementById("modal-detalle");
  const contenidoDetalle = document.getElementById("contenido-detalle");
  const cerrarDetalle    = document.getElementById("cerrar-modal-detalle");
  const cerrarDetallBtn  = document.getElementById("cerrar-detalle-btn");

  let historialCargado = false;

  if (!idMascota) {
    mostrarMensaje(mensajePagina, "No se especificó una mascota.", "error");
    return;
  }

  // ── Listeners de Acciones Adicionales ─────────────────────────────────────
  
  btnVacunas.addEventListener("click", () => {
    window.location.href = `esquema-vacunas.html?id=${encodeURIComponent(idMascota)}&from=tutor`;
  });

  btnCert.addEventListener("click", () => {
    alert("Funcionalidad de descarga de certificado estará disponible próximamente.");
  });

  // Carga en paralelo: datos de mascota + tratamientos activos
  await Promise.all([cargarMascota(), cargarTratamientos()]);


  // ── Datos de la mascota ───────────────────────────────────────────────────

  async function cargarMascota() {
    try {
      const m = await api.get(`/mascotas/${idMascota}`);
      nombreEl.textContent  = m.nombre;
      detalleEl.textContent = [m.especie, m.raza, m.sexo !== "desconocido" ? m.sexo : null]
                              .filter(Boolean).join(" · ");
      if (m.foto_url) {
        fotoEl.outerHTML = `<img src="${m.foto_url}" alt="${m.nombre}" class="foto-mascota" />`;
      } else {
        fotoEl.textContent = m.nombre.charAt(0).toUpperCase();
      }
    } catch (error) {
      mostrarMensaje(mensajePagina, `No se pudo cargar la mascota: ${error.message}`, "error");
    }
  }


  // ── Tratamientos activos — carga automática ───────────────────────────────

  async function cargarTratamientos() {
    seccionTrat.innerHTML = `<p class="cargando">Cargando...</p>`;
    try {
      const trats = await api.get(`/tratamientos/${idMascota}/activos`);

      if (trats.length === 0) {
        seccionTrat.innerHTML = `<p class="sin-datos">Esta mascota no tiene tratamientos activos.</p>`;
        return;
      }

      seccionTrat.innerHTML = trats.map(t => {
        const inicio = t.inicio
          ? new Date(t.inicio).toLocaleDateString("es-UY", { day: "numeric", month: "short", year: "numeric" })
          : "—";
        const fin = t.finalizacion
          ? new Date(t.finalizacion).toLocaleDateString("es-UY", { day: "numeric", month: "short", year: "numeric" })
          : "Sin fecha de fin";
        return `
          <div class="item-card">
            <strong>${t.nombre}</strong>
            ${t.descripcion ? `<small>${t.descripcion}</small>` : ""}
            ${t.frecuencia  ? `<small style="color:#4a90e2;">🕐 ${t.frecuencia}</small>` : ""}
            <small>Inicio: ${inicio} &nbsp;·&nbsp; Fin: ${fin}</small>
          </div>`;
      }).join("");

    } catch (e) {
      seccionTrat.innerHTML = `<p class="error-seccion">${e.message}</p>`;
    }
  }


  // ── Historial clínico — toggle con lazy load ──────────────────────────────

  btnHist.addEventListener("click", async () => {
    const abierto = seccionHist.style.display === "block";
    seccionHist.style.display = abierto ? "none" : "block";
    btnHist.textContent = abierto ? "Historial clínico" : "Cerrar historial";

    if (!abierto && !historialCargado) {
      seccionHist.innerHTML = `<p class="cargando">Cargando...</p>`;
      try {
        const consultas  = await api.get(`/historial/${idMascota}/consultas`);
        historialCargado = true;

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
      } catch (e) {
        seccionHist.innerHTML = `<p class="error-seccion">${e.message}</p>`;
      }
    }
  });

  // delegación de eventos para filas generadas dinámicamente
  seccionHist.addEventListener("click", async (e) => {
    const fila = e.target.closest(".fila-consulta");
    if (fila) await abrirModalDetalle(fila.dataset.id);
  });


  // ── Modal detalle consulta (solo lectura) ─────────────────────────────────

  cerrarDetalle.addEventListener("click",   () => cerrarModalDetalle());
  cerrarDetallBtn.addEventListener("click", () => cerrarModalDetalle());
  modalDetalle.addEventListener("click", (e) => {
    if (e.target === modalDetalle) cerrarModalDetalle();
  });

  async function abrirModalDetalle(idConsulta) {
    contenidoDetalle.innerHTML = `<p style="color:#aaa;text-align:center;padding:20px 0">Cargando...</p>`;
    modalDetalle.classList.add("activo");
    try {
      const c = await api.get(`/historial/${idMascota}/detalle/${idConsulta}`);
      const fecha = new Date(c.fecha_hora).toLocaleString("es-UY", {
        day: "numeric", month: "long", year: "numeric", hour: "2-digit", minute: "2-digit",
      });
      const secDosis = c.dosis?.length > 0
        ? `<hr class="separador"/>
           <p class="detalle-etiqueta">Vacunas aplicadas</p>
           <div class="lista-items">
             ${c.dosis.map(d => `
               <div class="item-card">
                 <strong>${d.nombre_vacuna}</strong>
                 <small>Dosis ${d.numero_dosis} — ${d.fecha_aplicacion}</small>
               </div>`).join("")}
           </div>` : "";

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
        ${secDosis}`;
    } catch (error) {
      contenidoDetalle.innerHTML = `<p style="color:#c0392b">${error.message}</p>`;
    }
  }

  function cerrarModalDetalle() { modalDetalle.classList.remove("activo"); }


  // ── Utilidades ────────────────────────────────────────────────────────────

  function mostrarMensaje(el, texto, tipo) {
    el.textContent = texto;
    el.classList.remove("mensaje-exito", "mensaje-error");
    el.classList.add(tipo === "exito" ? "mensaje-exito" : "mensaje-error");
    el.style.display = "block";
  }

});