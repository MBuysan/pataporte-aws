document.addEventListener("DOMContentLoaded", async () => {
  const inputMascota = document.getElementById("idMascota");
  const btnBuscar = document.getElementById("btnBuscar");
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

          card.style.border = proximaAVencer
            ? "2px solid #f57c00"
            : "1px solid #ddd";

          card.style.padding = "16px";
          card.style.marginTop = "12px";
          card.style.borderRadius = "8px";
          card.style.backgroundColor = "white";
          card.style.boxShadow = "0 1px 4px rgba(0,0,0,0.06)";

          if (proximaAVencer) {
            card.style.backgroundColor = "#fff3e0";
          }

          card.innerHTML = `
            <h3 style="color:#222; margin-bottom:8px;">Vacuna ${vacuna.nombre}</h3>
            <p style="font-size:14px; margin: 4px 0;"><strong>Fecha de inicio:</strong> ${vacuna.fecha_inicio ? formatearFecha(vacuna.fecha_inicio) : "—"}</p>
            <p style="font-size:14px; margin: 4px 0;"><strong>Próxima dosis:</strong> ${vacuna.fecha_proxima_dosis ? formatearFecha(vacuna.fecha_proxima_dosis) : "No requerida"}</p>
            <p style="font-size:14px; margin: 4px 0;"><strong>Dosis aplicadas:</strong> ${vacuna.dosis ? vacuna.dosis.length : 0}</p>
            ${proximaAVencer ? "<p style='color:#e65100; font-weight:bold; margin-top:8px;'>⚠️ Próxima dosis en menos de 7 días</p>" : ""}
          `;

          resultado.appendChild(card);
        });
      });
    } catch (error) {
      mensaje.textContent = error.message || "Error al obtener el carnet de vacunas.";
    }
  };

  // 4. Escuchar evento click en Buscar
  btnBuscar.addEventListener("click", async () => {
    const idMascota = inputMascota.value.trim();
    await ejecutarBusqueda(idMascota);
  });

  // 5. AUTO-BÚSQUEDA: Si vino un ID por la URL, rellenar y buscar automáticamente
  if (idUrl) {
    inputMascota.value = idUrl;
    await ejecutarBusqueda(idUrl);
  }

  function formatearFecha(fechaStr) {
  return new Date(fechaStr).toLocaleDateString("es-UY", {
    day: "numeric", month: "short", year: "numeric"
  });
  }
});