document.addEventListener("DOMContentLoaded", () => {
  const formTratamiento = document.getElementById("formTratamiento");
  const mensajeCrear = document.getElementById("mensajeCrear");

  const idMascotaBusquedaInput = document.getElementById("id_mascota_busqueda");
  const btnBuscarActivos = document.getElementById("btnBuscarActivos");
  const mensajeLista = document.getElementById("mensajeLista");
  const listaTratamientos = document.getElementById("listaTratamientos");

  const seccionEditar = document.getElementById("seccionEditar");
  const formEditarTratamiento = document.getElementById("formEditarTratamiento");
  const mensajeEditar = document.getElementById("mensajeEditar");

  if (formTratamiento) {
    formTratamiento.addEventListener("submit", async (event) => {
      event.preventDefault();

      const data = {
        id_consulta: document.getElementById("id_consulta").value.trim(),
        nombre: document.getElementById("nombre").value.trim(),
        indicaciones: document.getElementById("indicaciones").value.trim(),
        fecha_inicio: document.getElementById("fecha_inicio").value,
        fecha_fin_estimada: document.getElementById("fecha_fin_estimada").value,
      };

      mensajeCrear.textContent = "";

      try {
        const response = await api.post("/tratamientos/", data);
        guardarNotificacionMock(response);

        mensajeCrear.textContent =
          "Tratamiento creado correctamente. La notificacion simulada ya se puede ver en el dashboard del tutor.";

        idMascotaBusquedaInput.value = response.id_mascota;

        formTratamiento.reset();
        await cargarTratamientosActivos(response.id_mascota);
      } catch (error) {
        mensajeCrear.textContent = error.message;
      }
    });
  }

  if (btnBuscarActivos) {
    btnBuscarActivos.addEventListener("click", async () => {
      const idMascota = idMascotaBusquedaInput.value.trim();

      if (!idMascota) {
        mensajeLista.textContent = "Ingresa un ID de mascota.";
        return;
      }

      await cargarTratamientosActivos(idMascota);
    });
  }

  if (formEditarTratamiento) {
    formEditarTratamiento.addEventListener("submit", async (event) => {
      event.preventDefault();

      const idTratamiento = document.getElementById("editar_id_tratamiento").value;

      const data = {
        nombre: document.getElementById("editar_nombre").value.trim(),
        indicaciones: document.getElementById("editar_indicaciones").value.trim(),
        fecha_inicio: document.getElementById("editar_fecha_inicio").value,
        fecha_fin_estimada:
          document.getElementById("editar_fecha_fin_estimada").value,
      };

      mensajeEditar.textContent = "";

      try {
        await api.patch(`/tratamientos/${idTratamiento}`, data);
        mensajeEditar.textContent = "Tratamiento actualizado correctamente.";

        const idMascota = idMascotaBusquedaInput.value.trim();
        await cargarTratamientosActivos(idMascota);

        seccionEditar.style.display = "none";
        formEditarTratamiento.reset();
      } catch (error) {
        mensajeEditar.textContent = error.message;
      }
    });
  }

  async function cargarTratamientosActivos(idMascota) {
    mensajeLista.textContent = "";
    listaTratamientos.innerHTML = "";

    try {
      const tratamientos = await api.get(`/tratamientos/${idMascota}/activos`);

      if (!tratamientos.length) {
        mensajeLista.textContent = "No hay tratamientos activos.";
        return;
      }

      tratamientos.forEach((tratamiento) => {
        const card = document.createElement("div");
        card.style.border = "1px solid #ccc";
        card.style.padding = "10px";
        card.style.marginTop = "10px";

        card.innerHTML = `
          <p><strong>ID:</strong> ${tratamiento.id_tratamiento}</p>
          <p><strong>Nombre:</strong> ${tratamiento.nombre}</p>
          <p><strong>Indicaciones:</strong> ${tratamiento.indicaciones}</p>
          <p><strong>Inicio:</strong> ${tratamiento.fecha_inicio}</p>
          <p><strong>Fin estimada:</strong> ${tratamiento.fecha_fin_estimada}</p>

          <button data-id="${tratamiento.id_tratamiento}" class="btnFinalizar">
            Finalizar tratamiento
          </button>

          <button data-id="${tratamiento.id_tratamiento}" class="btnEditar">
            Editar tratamiento
          </button>
        `;

        listaTratamientos.appendChild(card);
      });

      agregarEventosBotones(idMascota);
    } catch (error) {
      mensajeLista.textContent = error.message;
    }
  }

  function agregarEventosBotones(idMascota) {
    const botonesFinalizar = document.querySelectorAll(".btnFinalizar");
    const botonesEditar = document.querySelectorAll(".btnEditar");

    botonesFinalizar.forEach((boton) => {
      boton.addEventListener("click", async () => {
        const idTratamiento = boton.dataset.id;

        try {
          await api.patch(`/tratamientos/${idTratamiento}/finalizar`, {});
          await cargarTratamientosActivos(idMascota);
        } catch (error) {
          alert(error.message);
        }
      });
    });

    botonesEditar.forEach((boton) => {
      boton.addEventListener("click", async () => {
        const idTratamiento = boton.dataset.id;

        try {
          const tratamientos = await api.get(`/tratamientos/${idMascota}`);
          const tratamiento = tratamientos.find(
            (item) => item.id_tratamiento === idTratamiento,
          );

          if (!tratamiento) {
            alert("Tratamiento no encontrado.");
            return;
          }

          seccionEditar.style.display = "block";
          document.getElementById("editar_id_tratamiento").value =
            tratamiento.id_tratamiento;
          document.getElementById("editar_nombre").value = tratamiento.nombre;
          document.getElementById("editar_indicaciones").value =
            tratamiento.indicaciones;
          document.getElementById("editar_fecha_inicio").value =
            tratamiento.fecha_inicio;
          document.getElementById("editar_fecha_fin_estimada").value =
            tratamiento.fecha_fin_estimada;

          mensajeEditar.textContent = "";
        } catch (error) {
          alert(error.message);
        }
      });
    });
  }
});

function guardarNotificacionMock(tratamiento) {
  const nombreTratamiento = tratamiento.nombre || "Nuevo tratamiento";
  const idMascota = tratamiento.id_mascota || "sin mascota";

  localStorage.setItem(
    "mock_notificacion_tutor",
    JSON.stringify({
      mensaje: `Notificacion simulada: se registro "${nombreTratamiento}" para la mascota ${idMascota}.`,
      fecha: new Date().toISOString(),
    }),
  );
}
