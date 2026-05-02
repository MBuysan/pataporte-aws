document.addEventListener("DOMContentLoaded", () => {
  const formTratamiento = document.getElementById("formTratamiento");
  const mensajeCrear = document.getElementById("mensajeCrear");

  const inputBusqueda = document.getElementById("id_mascota_busqueda");
  const btnBuscarActivos = document.getElementById("btnBuscarActivos");
  const mensajeLista = document.getElementById("mensajeLista");
  const listaTratamientos = document.getElementById("listaTratamientos");

  formTratamiento.addEventListener("submit", async (e) => {
    e.preventDefault();

    const data = {
      id_mascota: document.getElementById("id_mascota").value.trim(),
      nombre: document.getElementById("nombre").value.trim(),
      descripcion: document.getElementById("descripcion").value.trim() || null,
      finalizacion: null,
    };

    try {
      const response = await api.post("/tratamientos/", data);

      mensajeCrear.textContent = "Tratamiento creado correctamente.";
      inputBusqueda.value = response.id_mascota;

      formTratamiento.reset();
      await cargarTratamientosActivos(response.id_mascota);
    } catch (error) {
      mensajeCrear.textContent = error.message;
    }
  });

  btnBuscarActivos.addEventListener("click", async () => {
    const idMascota = inputBusqueda.value.trim();

    if (!idMascota) {
      mensajeLista.textContent = "Ingresá un ID de mascota.";
      return;
    }

    await cargarTratamientosActivos(idMascota);
  });

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
          <p><strong>Descripción:</strong> ${tratamiento.descripcion || "Sin descripción"}</p>
          <p><strong>Creación:</strong> ${tratamiento.creacion}</p>

          <button data-id="${tratamiento.id_tratamiento}" class="btnFinalizar">
            Tratamiento finalizado
          </button>
        `;

        listaTratamientos.appendChild(card);
      });

      agregarEventosFinalizar(idMascota);
    } catch (error) {
      mensajeLista.textContent = error.message;
    }
  }

  function agregarEventosFinalizar(idMascota) {
    const botonesFinalizar = document.querySelectorAll(".btnFinalizar");

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
  }
});