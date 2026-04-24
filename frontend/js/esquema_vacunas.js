document.addEventListener("DOMContentLoaded", () => {
  const inputMascota = document.getElementById("id_mascota");
  const btnBuscar = document.getElementById("btnBuscarEsquema");
  const mensaje = document.getElementById("mensaje");
  const listaEsquemas = document.getElementById("listaEsquemas");

  btnBuscar.addEventListener("click", async () => {
    const idMascota = inputMascota.value.trim();

    mensaje.textContent = "";
    listaEsquemas.innerHTML = "";

    if (!idMascota) {
      mensaje.textContent = "Ingresá el ID de la mascota.";
      return;
    }

    try {
      const esquemas = await api.get(`/vacunas/${idMascota}/carnet`);

      if (!esquemas.length) {
        mensaje.textContent = "No hay esquemas de vacunación registrados.";
        return;
      }

      esquemas.forEach((esquema) => {
        const card = document.createElement("div");

        card.style.border = esquema.proxima_a_vencer
          ? "2px solid orange"
          : "1px solid #ccc";

        card.style.padding = "12px";
        card.style.marginTop = "12px";

        if (esquema.proxima_a_vencer) {
          card.style.backgroundColor = "#fff3cd";
        }

        let contenido = `
          <h3>Vacuna ${esquema.nombre_vacuna}</h3>
          <p><strong>Fecha de primera aplicación:</strong> ${formatearFecha(esquema.fecha_inicio)}</p>
          <p><strong>Fecha estimada de fin:</strong> ${formatearFecha(esquema.fecha_estimada_fin)}</p>
        `;

        if (esquema.esquema_completo) {
          contenido += `
            <p><strong>Total dosis aplicadas:</strong> ${esquema.dosis_dadas}</p>
          `;
        } else {
          contenido += `
            <p><strong>Dosis totales:</strong> ${esquema.dosis_totales}</p>
            <p><strong>Dosis dadas:</strong> ${esquema.dosis_dadas}</p>
            <p><strong>Próxima dosis:</strong> ${formatearFecha(esquema.fecha_proxima_dosis)}</p>
          `;

          if (esquema.proxima_a_vencer) {
            contenido += `<p><strong>Atención:</strong> la próxima dosis está próxima a vencer.</p>`;
          }
        }

        card.innerHTML = contenido;
        listaEsquemas.appendChild(card);
      });
    } catch (error) {
      mensaje.textContent = error.message;
    }
  });

  function formatearFecha(fecha) {
    if (!fecha) return "No definida";
    return fecha;
  }
});