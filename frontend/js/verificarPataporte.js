document.addEventListener("DOMContentLoaded", () => {

  const inputHash  = document.getElementById("input-hash");
  const btnVerif   = document.getElementById("btn-verificar");
  const errorForm  = document.getElementById("error-form");
  const divResult  = document.getElementById("resultado");
  const divCarg    = document.getElementById("cargando");
  const cardResult = document.getElementById("card-resultado");

  // ── Verificar al pulsar Enter en el input ──────────────────────────────────
  inputHash.addEventListener("keydown", (e) => {
    if (e.key === "Enter") btnVerif.click();
  });

  btnVerif.addEventListener("click", async () => {
    const hash = inputHash.value.trim();

    errorForm.textContent = "";
    cardResult.style.display = "none";

    if (!hash) {
      errorForm.textContent = "Ingresá el código de verificación.";
      inputHash.focus();
      return;
    }

    btnVerif.disabled     = true;
    btnVerif.textContent  = "Verificando...";
    divResult.style.display = "block";
    divCarg.style.display   = "block";

    try {
      const data = await api.get(`/pataporte/verificar/${encodeURIComponent(hash)}`);
      divCarg.style.display = "none";
      cardResult.style.display = "block";
      cardResult.innerHTML = renderResultado(data);
    } catch (err) {
      divCarg.style.display = "none";
      cardResult.style.display = "block";
      cardResult.innerHTML = renderError(err.message);
    } finally {
      btnVerif.disabled    = false;
      btnVerif.textContent = "Verificar";
    }
  });

  // ── Render resultado ───────────────────────────────────────────────────────

  function renderResultado(d) {
    const claseEstado = { vigente: "vigente", deprecado: "deprecado", revocado: "revocado" }[d.estado] ?? "deprecado";
    const titulos     = { vigente: "Pataporte válido", deprecado: "Pataporte deprecado", revocado: "Pataporte revocado" };
    const subtitulos  = {
      vigente:   "Este certificado es auténtico y se encuentra vigente.",
      deprecado: "Este certificado fue reemplazado por una versión más reciente.",
      revocado:  "Este certificado fue revocado y ya no es válido.",
    };

    const fecha = new Date(d.fecha_emision).toLocaleDateString("es-UY", {
      day: "numeric", month: "long", year: "numeric",
    });

    const mascota = d.mascota ?? {};
    const tutor   = mascota.tutor ?? {};

    // vacunas
    const vacunasHtml = (d.vacunas ?? []).map(v => `
      <div class="vacuna-card">
        <div>
          <span class="vacuna-nombre">${v.nombre}</span>
          <span class="vacuna-estado ${v.esquema_completo ? "completo" : "incompleto"}">
            ${v.esquema_completo ? "Completo" : "Incompleto"}
          </span>
        </div>
        ${v.descripcion ? `<div style="font-size:12px;color:#6B7280;margin-top:2px;">${v.descripcion}</div>` : ""}
        <div class="dosis-lista">
          ${(v.dosis_aplicadas ?? []).map(dos => {
            const vet = dos.veterinario_aplicador ?? {};
            return `
              <div class="dosis-item">
                <span><strong>Dosis #${dos.numero}</strong> — ${dos.fecha}</span>
                <span class="dosis-vet">
                  ${vet.nombre ?? "—"} · Mat. ${vet.matricula ?? "—"} · RUT org. ${vet.organizacion_rut ?? "—"}
                </span>
              </div>`;
          }).join("") || '<div class="dosis-item" style="color:#9CA3AF;">Sin dosis aplicadas.</div>'}
        </div>
      </div>
    `).join("") || '<p style="color:#9CA3AF;font-size:13px;">Sin vacunas registradas.</p>';

    const badgeGeneral = d.esquema_general_completo
      ? `<div class="badge-general completo">Esquema de vacunación general completo</div>`
      : `<div class="badge-general incompleto">Esquema de vacunación general incompleto</div>`;

    return `
      <div class="estado-banner ${claseEstado}">
        <div class="estado-texto">
          <h3>${titulos[d.estado] ?? "Estado desconocido"}</h3>
          <p>${subtitulos[d.estado] ?? ""}</p>
        </div>
      </div>

      <div class="cuerpo">

        <p class="seccion-titulo">Fecha de emisión</p>
        <div class="grilla">
          <div class="dato">
            <div class="etiqueta">Emitido el</div>
            <div class="valor">${fecha}</div>
          </div>
          <div class="dato">
            <div class="etiqueta">Emisor</div>
            <div class="valor">${d.emisor?.nombre ?? "Pataporte"}</div>
          </div>
        </div>

        <p class="seccion-titulo">Mascota</p>
        <div class="grilla">
          <div class="dato"><div class="etiqueta">Nombre</div><div class="valor">${mascota.nombre ?? "—"}</div></div>
          <div class="dato"><div class="etiqueta">Especie</div><div class="valor">${capitalizar(mascota.especie)}</div></div>
          <div class="dato"><div class="etiqueta">Raza</div><div class="valor">${mascota.raza ?? "—"}</div></div>
          <div class="dato">
            <div class="etiqueta">Tutor</div>
            <div class="valor">${tutor.nombre ?? "—"}</div>
          </div>
        </div>

        <p class="seccion-titulo">Vacunas</p>
        ${vacunasHtml}
        ${badgeGeneral}

      </div>
    `;
  }

  function renderError(mensaje) {
    const esNoEncontrado = mensaje?.toLowerCase().includes("no encontrado") || mensaje?.includes("404");
    return `
      <div class="estado-banner revocado">
        <div class="estado-texto">
          <h3>${esNoEncontrado ? "Código no encontrado" : "Error al verificar"}</h3>
          <p>${esNoEncontrado
            ? "No existe ningún Pataporte con ese código. Verificá que lo hayas copiado correctamente."
            : mensaje}</p>
        </div>
      </div>
    `;
  }

  function capitalizar(str) {
    if (!str) return "—";
    return str.charAt(0).toUpperCase() + str.slice(1);
  }

});