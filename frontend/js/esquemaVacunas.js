document.addEventListener("DOMContentLoaded", async () => {
  const btnVolver = document.getElementById("btnVolver");
  const resultado = document.getElementById("resultado");
  const mensaje = document.getElementById("mensaje");

  // 1. Leer parámetros de la URL para comportamiento inteligente
  const params = new URLSearchParams(window.location.search);
  const idUrl = params.get("id");
  const fromSource = params.get("from"); // "tutor" o "vet"




  // 2. Configurar dinámicamente el botón "Volver"
  if (fromSource === "tutor") {
    btnVolver.href = `perfil-mascota-tutor.html?id=${encodeURIComponent(idUrl || "")}`;
  } else if (fromSource === "vet") {
    btnVolver.href = `perfil-mascota-vet.html?id=${encodeURIComponent(idUrl || "")}`;
  } else {
    btnVolver.href = "#";
    btnVolver.addEventListener("click", (e) => {
      e.preventDefault();
      if (window.history.length > 1) {
        window.history.back();
      } else {
        window.location.href = "../index.html";
      }
    });
  }

  // 3. Función de búsqueda principal
  const ejecutarBusqueda = async (idMascota) => {
    mensaje.textContent = "Cargando carnet...";
    resultado.innerHTML = "";

    if (!idMascota) {
      mensaje.textContent = "Ingresá un ID de mascota.";
      return;
    }

    try {
      const esquemas = await api.get(`/vacunas/${idMascota}/carnet`);
      mensaje.textContent = "";

      if (!esquemas || !esquemas.length) {
        mensaje.textContent = "No hay esquema de vacunas para esta mascota.";
        return;
      }

      esquemas.forEach((esquema) => {
        // Si el esquema viene vacío o no tiene vacunas
        if (!esquema.vacunas || esquema.vacunas.length === 0) {
          mensaje.textContent = "Esta mascota no tiene vacunas registradas en su esquema.";
          return;
        }

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

          const dosisAplicadas =
            vacuna.dosis_aplicadas !== undefined
              ? vacuna.dosis_aplicadas
              : (vacuna.dosis ? vacuna.dosis.length : 0);

          const dosisRequeridas =
            vacuna.dosis_requeridas !== undefined
              ? vacuna.dosis_requeridas
              : 0;

          const esCompletada =
            dosisAplicadas >= dosisRequeridas ||
            vacuna.estado === "completado";

          card.className = esCompletada
            ? "vacuna-card finalizada"
            : "vacuna-card";

          card.innerHTML = `
  ${esCompletada
              ? `<span class="finalizada-texto">¡Vacuna finalizada!</span>`
              : ""
            }

  <h3 class="vacuna-titulo">
    ${vacuna.nombre}
  </h3>

  <p class="vacuna-meta">
    <strong>Fecha inicio:</strong>
    ${vacuna.fecha_inicio
              ? formatearFecha(vacuna.fecha_inicio)
              : "—"
            }
  </p>

  <p class="vacuna-meta">
    <strong>Fecha próxima dosis:</strong>
    ${vacuna.fecha_proxima_dosis
              ? formatearFecha(vacuna.fecha_proxima_dosis)
              : "No requerida"
            }
  </p>

  <p class="vacuna-meta">
    <strong>Dosis aplicadas:</strong>
    ${dosisAplicadas}
  </p>

  <p class="vacuna-meta">
    <strong>Dosis totales:</strong>
    ${dosisRequeridas}
  </p>

  ${proximaAVencer
              ? `<p class="alerta">
          ⚠ Próxima dosis en menos de 7 días
        </p>`
              : ""
            }
`;

          resultado.appendChild(card);
        });
      });
    } catch (error) {
      mensaje.textContent = error.message || "Error al obtener el carnet de vacunas.";
    }
  };



  // 5. AUTO-BÚSQUEDA: Si vino un ID por la URL, rellenar y buscar automáticamente
  if (idUrl) {
    await ejecutarBusqueda(idUrl);
  }

  function formatearFecha(fechaStr) {
    return new Date(fechaStr).toLocaleDateString("es-UY", {
      day: "numeric", month: "short", year: "numeric"
    });
  }
});