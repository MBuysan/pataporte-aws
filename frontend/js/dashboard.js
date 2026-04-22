document.addEventListener("DOMContentLoaded", async () => {
  const bienvenida = document.getElementById("bienvenida");
  const notificacionTutor = document.getElementById("notificacionTutor");
  const listaMascotas = document.getElementById("listaMascotas");

  const tutor = JSON.parse(localStorage.getItem("tutor") || "null");
  const notificacionMock = JSON.parse(
    localStorage.getItem("mock_notificacion_tutor") || "null",
  );

  if (bienvenida) {
    bienvenida.textContent = tutor
      ? `Sesion iniciada como ${tutor.nombre}.`
      : "No hay una sesion de tutor activa.";
  }

  if (notificacionTutor) {
    if (notificacionMock) {
      notificacionTutor.textContent =
        `${notificacionMock.mensaje} (${formatearFecha(notificacionMock.fecha)})`;
    } else {
      notificacionTutor.textContent =
        "No hay notificaciones simuladas pendientes.";
    }
  }

  if (!tutor || !listaMascotas) {
    return;
  }

  try {
    const mascotas = await api.get(`/tutores/${tutor.id_tutor}/mascotas`);

    if (!mascotas.length) {
      listaMascotas.innerHTML = "<p>No tenes mascotas registradas.</p>";
      return;
    }

    const resultados = await Promise.all(
      mascotas.map(async (mascota) => {
        try {
          const tratamientos = await api.get(
            `/tratamientos/${mascota.id_mascota}/activos`,
          );
          return { mascota, tratamientos, error: null };
        } catch (error) {
          return { mascota, tratamientos: [], error: error.message };
        }
      }),
    );

    listaMascotas.innerHTML = resultados
      .map(({ mascota, tratamientos, error }) => renderMascota(mascota, tratamientos, error))
      .join("");
  } catch (error) {
    listaMascotas.innerHTML = `<p>Error al cargar el perfil: ${error.message}</p>`;
  }
});

function renderMascota(mascota, tratamientos, error) {
  if (error) {
    return `
      <article>
        <h3>${mascota.nombre}</h3>
        <p><strong>ID:</strong> ${mascota.id_mascota}</p>
        <p>Error al cargar tratamientos: ${error}</p>
      </article>
      <hr />
    `;
  }

  const tratamientosHtml = tratamientos.length
    ? tratamientos
        .map(
          (tratamiento) => `
            <article>
              <p><strong>Nombre:</strong> ${tratamiento.nombre}</p>
              <p><strong>Indicaciones:</strong> ${tratamiento.indicaciones}</p>
              <p><strong>Fecha de inicio:</strong> ${tratamiento.fecha_inicio}</p>
              <p><strong>Fecha fin estimada:</strong> ${tratamiento.fecha_fin_estimada}</p>
              <p><strong>Estado:</strong> Activo</p>
            </article>
          `,
        )
        .join("<hr />")
    : "<p>No hay tratamientos activos para esta mascota.</p>";

  return `
    <article>
      <h3>${mascota.nombre}</h3>
      <p><strong>ID:</strong> ${mascota.id_mascota}</p>
      <p><strong>Especie:</strong> ${mascota.especie}</p>
      <p><strong>Raza:</strong> ${mascota.raza || "Sin dato"}</p>
      <h4>Tratamientos activos</h4>
      ${tratamientosHtml}
    </article>
    <hr />
  `;
}

function formatearFecha(fechaIso) {
  if (!fechaIso) {
    return "sin fecha";
  }

  const fecha = new Date(fechaIso);
  if (Number.isNaN(fecha.getTime())) {
    return "sin fecha";
  }

  return fecha.toLocaleString("es-UY");
}
