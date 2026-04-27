document.addEventListener("DOMContentLoaded", () => {
  const inputMascota = document.getElementById("idMascota");
  const btnBuscar = document.getElementById("btnBuscar");
  const resultado = document.getElementById("resultado");
  const mensaje = document.getElementById("mensaje");

  btnBuscar.addEventListener("click", async () => {
    const idMascota = inputMascota.value.trim();

    mensaje.textContent = "";
    resultado.innerHTML = "";

    if (!idMascota) {
      mensaje.textContent = "Ingresá un ID de mascota.";
      return;
    }

    try {
      const esquemas = await api.get(`/vacunas/${idMascota}/carnet`);

      if (!esquemas.length) {
        mensaje.textContent = "No hay esquema de vacunas para esta mascota.";
        return;
      }

      esquemas.forEach((esquema) => {
        esquema.vacunas.forEach((vacuna) => {
          const card = document.createElement("div");

          const proxima = vacuna.fecha_proxima_dosis
            ? new Date(vacuna.fecha_proxima_dosis)
            : null;

          const hoy = new Date();
          const enSieteDias = new Date();
          enSieteDias.setDate(hoy.getDate() + 7);

          const proximaAVencer =
            proxima && proxima >= hoy && proxima <= enSieteDias;

          card.style.border = proximaAVencer
            ? "2px solid orange"
            : "1px solid gray";

          card.style.padding = "12px";
          card.style.marginTop = "12px";

          if (proximaAVencer) {
            card.style.backgroundColor = "#fff3cd";
          }

          card.innerHTML = `
            <h3>Vacuna ${vacuna.nombre}</h3>
            <p><strong>Fecha de primera aplicación:</strong> ${vacuna.fecha_inicio}</p>
            <p><strong>Próxima dosis:</strong> ${vacuna.fecha_proxima_dosis || "No definida"}</p>
            <p><strong>Dosis aplicadas:</strong> ${vacuna.dosis.length}</p>
            ${
              proximaAVencer
                ? "<p><strong>Atención:</strong> vacuna próxima a vencer</p>"
                : ""
            }
          `;

          resultado.appendChild(card);
        });
      });
    } catch (error) {
      mensaje.textContent = error.message;
    }
  });
});