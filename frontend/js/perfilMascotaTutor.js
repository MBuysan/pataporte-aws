// Vista del tutor — solo lectura.

document.addEventListener("DOMContentLoaded", async () => {

  const params = new URLSearchParams(window.location.search);
  const idMascota = params.get("id");

  const nombreEl = document.getElementById("nombre-mascota");
  const detalleEl = document.getElementById("detalle-mascota");
  const fotoEl = document.getElementById("foto-mascota");
  const mensajePagina = document.getElementById("mensaje-pagina");
  const seccionTrat = document.getElementById("seccion-tratamientos");
  const seccionHist = document.getElementById("seccion-historial");
  const btnHist = document.getElementById("btn-historial");
  const btnVacunas = document.getElementById("btn-vacunas");
  const btnCert = document.getElementById("btn-certificado");
  const btnEliminar = document.getElementById("btn-eliminar");
  const modalDetalle = document.getElementById("modal-detalle");
  const contenidoDetalle = document.getElementById("contenido-detalle");
  const cerrarDetalle = document.getElementById("cerrar-modal-detalle");
  const cerrarDetallBtn = document.getElementById("cerrar-detalle-btn");

  let historialCargado = false;
  const tutor = JSON.parse(localStorage.getItem("tutor"));

  if (!idMascota) {
    mostrarMensaje(mensajePagina, "No se especificó una mascota.", "error");
    return;
  }

  // ── Listeners de Acciones Adicionales ─────────────────────────────────────

  btnVacunas.addEventListener("click", () => {
    window.location.href = `esquema-vacunas.html?id=${encodeURIComponent(idMascota)}&from=tutor`;
  });

  btnCert.addEventListener("click", async () => {

    if (!confirm("¿Generar el Pataporte de vacunación de esta mascota?\n\nEl certificado PDF se enviará al correo registrado del tutor.")) return;

    btnCert.disabled = true;
    btnCert.textContent = "Generando...";

    try {
      const res = await api.post(`/pataporte/${idMascota}`);

      alert(
        `Pataporte generado correctamente.\n\n` +
        `El certificado PDF fue enviado al correo del tutor.\n\n`
      );

    } catch (err) {

      alert(`Error al generar el Pataporte: ${err.message}`);

    } finally {
      
      btnCert.disabled = false;
      btnCert.textContent = "Generar Pataporte";
    }
  });

  btnEliminar.addEventListener("click", async () => {
    const nombreMascota = nombreEl.textContent;
    const textoEsperado = `eliminar perfil ${nombreMascota}`;

    const confirmacion = prompt(
      `Esta acción eliminará definitivamente el perfil de ${nombreMascota}.\n\nAntes de eliminarlo, se enviará un respaldo clínico por correo.\n\nPara confirmar, escribí exactamente:\n${textoEsperado}`
    );

    if (confirmacion !== textoEsperado) {
      alert("Confirmación incorrecta. No se eliminó la mascota.");
      return;
    }

    try {
      await api.delete(`/mascotas/${idMascota}`);
      alert("Mascota eliminada correctamente. Se envió el respaldo clínico por correo.");
      window.location.href = "dashboard.html";
    } catch (error) {
      alert(`No se pudo eliminar la mascota: ${error.message}`);
    }
  });

  // Carga en paralelo: datos de mascota + tratamientos activos
  if (!tutor || !tutor.id_tutor) {
    mostrarMensaje(mensajePagina, "Debés iniciar sesión para ver esta mascota.", "error");
    return;
  }

  const tieneAcceso = await validarAccesoTutor();

  if (!tieneAcceso) {
    return;
  }

  // Carga en paralelo: datos de mascota + tratamientos activos
  await Promise.all([cargarMascota(), cargarTratamientos()]);

  async function validarAccesoTutor() {
    try {
      const mascotas = await api.get(`/tutores/${tutor.id_tutor}/mascotas`);

      const puedeVer = mascotas.some((m) => m.id_mascota === idMascota);

      if (!puedeVer) {
        nombreEl.textContent = "Acceso denegado";
        detalleEl.textContent = "";
        seccionTrat.innerHTML = "";
        seccionHist.innerHTML = "";
        btnHist.style.display = "none";

        mostrarMensaje(
          mensajePagina,
          "No tenés permisos para ver la información de esta mascota.",
          "error"
        );

        return false;
      }

      return true;
    } catch (error) {
      mostrarMensaje(
        mensajePagina,
        `No se pudo validar el acceso: ${error.message}`,
        "error"
      );

      return false;
    }
  }

  // ── Datos de la mascota ───────────────────────────────────────────────────

  async function cargarMascota() {
    try {
      const m = await api.get(`/mascotas/${idMascota}`);
      nombreEl.textContent = m.nombre;
      detalleEl.textContent = [m.especie, m.raza, m.sexo !== "desconocido" ? m.sexo : null]
        .filter(Boolean).join(" · ");
      if (m.foto_url) {
        fotoEl.outerHTML = `<img src="${m.foto_url}" alt="${m.nombre}" class="foto-mascota" />`;
      } else {
        fotoEl.textContent = m.nombre.charAt(0).toUpperCase();
      }

      if (m.especie !== "perro" && m.especie !== "gato") {
        btnVacunas.style.display = "none";
        btnCert.style.display = "none";
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
            ${t.frecuencia ? `<small style="color:#4a90e2;">🕐 ${t.frecuencia}</small>` : ""}
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

    btnHist.textContent =
      abierto
        ? "Historial clínico"
        : "Cerrar historial";

    if (!abierto && !historialCargado) {
      await cargarHistorial();
    }
  });

  async function cargarHistorial() {

    seccionHist.innerHTML =
      `<p class="cargando">Cargando historial de consultas...</p>`;

    try {

      const response =
        await api.get(`/historial/${idMascota}/unificado`);

      const eventos = response.eventos;

      historialCargado = true;

      if (!eventos || eventos.length === 0) {

        seccionHist.innerHTML =
          `<p class="sin-datos">No hay consultas registradas.</p>`;

        return;
      }

      eventos.sort(
        (a, b) =>
          new Date(b.fecha) - new Date(a.fecha)
      );

      seccionHist.innerHTML = `
      <p style="
        font-size: 14px;
        font-weight: 700;
        color: #a6a6a6;
        margin: 16px 0 10px 2px;
        letter-spacing: 0.5px;
      ">
        CONSULTAS
      </p>

      ${eventos.map(renderEvento).join("")}
    `;

    } catch (e) {

      seccionHist.innerHTML = `
      <p class="error-seccion">
        No se pudo cargar el historial:
        ${e.message}
      </p>
    `;
    }
  }

  seccionHist.addEventListener("click", async (e) => {

    const fila = e.target.closest(".fila-consulta");

    if (!fila) return;

    await abrirModalDetalle(fila.dataset.id);
  });

  function renderEvento(e) {


    const fecha = new Date(e.fecha).toLocaleDateString("es-UY", {
      day: "numeric",
      month: "short",
      year: "numeric"
    });

    const hora = new Date(e.fecha).toLocaleTimeString("es-UY", {
      hour: "2-digit",
      minute: "2-digit"
    });

    // CONSULTA

    if (e.tipo === "consulta") {

      return `
      <button
        class="fila-consulta"
        data-id="${e.id}"
      >

        <span style="
          background:#e3f2fd;
          color:#1976d2;
          padding:4px 8px;
          border-radius:6px;
          font-size:10px;
          font-weight:bold;
          white-space:nowrap;
        ">
          CONSULTA
        </span>

        <span class="consulta-motivo">
          <b>${fecha}, ${hora}</b> — ${e.motivo}
        </span>

        <span class="consulta-flecha">›</span>

      </button>
    `;
    }

    // TRATAMIENTO

    const fin = e.finalizacion
      ? new Date(e.finalizacion).toLocaleDateString("es-UY", {
        day: "numeric",
        month: "short",
        year: "numeric"
      })
      : "Sin fecha de fin";

    const estado =
      e.finalizacion &&
        new Date(e.finalizacion) < new Date()
        ? "FINALIZADO"
        : "ACTIVO";

    const colorEstado =
      estado === "FINALIZADO"
        ? "#bbb"
        : "#f57c00";

    return `
    <div class="item-card">

      <div style="
        display:flex;
        align-items:center;
        gap:8px;
        margin-bottom:6px;
      ">

        <span style="
          background:#fff3e0;
          color:${colorEstado};
          padding:4px 8px;
          border-radius:6px;
          font-size:10px;
          font-weight:bold;
        ">
          TRATAMIENTO · ${estado}
        </span>

        <span style="
          font-size:12px;
          color:#aaa;
        ">
          ${fecha}
        </span>

      </div>

      <strong>${e.nombre}</strong>

      ${e.descripcion
        ? `<small>${e.descripcion}</small>`
        : ""}

      ${e.frecuencia
        ? `<small style="color:#4a90e2;">🕐 ${e.frecuencia}</small>`
        : ""}

      <small>
        Finalización: ${fin}
      </small>

    </div>
  `;
  }


  // ── Modal detalle consulta (solo lectura) ─────────────────────────────────

  if (cerrarDetalle) {
    cerrarDetalle.addEventListener("click", cerrarModalDetalle);
  }

  if (cerrarDetallBtn) {
    cerrarDetallBtn.addEventListener("click", cerrarModalDetalle);
  }

  if (modalDetalle) {
    modalDetalle.addEventListener("click", (e) => {
      if (e.target === modalDetalle) {
        cerrarModalDetalle();
      }
    });
  }

  async function abrirModalDetalle(idConsulta) {

    if (!modalDetalle || !contenidoDetalle) { return; }
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