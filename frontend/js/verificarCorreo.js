// Maneja el envío del código de verificación, el reenvío y la lógica de AUTO-LOGIN post-validación
document.addEventListener("DOMContentLoaded", () => {
  // 1. Extraer parámetros de la URL para saber a quién verificar
  const params = new URLSearchParams(window.location.search);
  const email = params.get("email");
  const tipo = params.get("tipo"); // "tutor" o "veterinario"

  // 2. Elementos del DOM
  const mostrarEmail  = document.getElementById("mostrar-email");
  const form          = document.getElementById("form-verificacion");
  const inputCodigo   = document.getElementById("input-codigo");
  const btnVerificar  = document.getElementById("btn-verificar");
  const btnReenviar   = document.getElementById("btn-reenviar");
  const mensajeEl     = document.getElementById("mensaje-verificacion");

  // Seguridad básica: si accedieron sin email/tipo redirigir al login
  if (!email || !tipo) {
    window.location.href = "login.html";
    return;
  }

  // Pintamos el email del destinatario en pantalla
  mostrarEmail.textContent = email;

  // 3. Escuchar el envío del código
  form.addEventListener("submit", async (e) => {
    e.preventDefault();

    const codigo = inputCodigo.value.trim().toUpperCase();

    if (codigo.length !== 6) {
      mostrarMensaje(mensajeEl, "El código debe contener exactamente 6 dígitos.", "error");
      return;
    }

    // Estado cargando en el botón
    btnVerificar.disabled = true;
    btnVerificar.textContent = "Activando cuenta...";

    try {
      // Consumir el nuevo endpoint que verifica la cuenta y genera el JWT
      const response = await api.post("/auth/verificar-email", {
        email: email,
        tipo_usuario: tipo,
        codigo: codigo
      });

      mostrarMensaje(mensajeEl, "¡Felicidades! Tu cuenta ha sido activada con éxito. Iniciando sesión...", "exito");

      // --- 4. LÓGICA DE AUTO-LOGIN AUTOMÁTICA ---
      // Guardamos el Token JWT principal recibido
      localStorage.setItem("access_token", response.access_token);

      if (tipo === "tutor") {
        // Imitando app.js: Traemos el objeto tutor completo y lo guardamos en localStorage
        const tutorCompleto = await api.get(`/tutores/${response.user.id_tutor}`);
        localStorage.setItem("tutor", JSON.stringify(tutorCompleto));

        // Redireccionamos al Dashboard del tutor
        setTimeout(() => {
          window.location.href = "dashboard.html";
        }, 1500);

      } else {
        // Imitando loginVeterinario.js: Guardamos las llaves de contexto necesarias para un veterinario
        localStorage.setItem("user", JSON.stringify(response.user));
        localStorage.setItem("rol", "veterinario");
        localStorage.setItem("veterinario_id", response.user.id_veterinario);

        // Redireccionamos a la pantalla principal del veterinario
        setTimeout(() => {
          window.location.href = "buscar-mascotas.html";
        }, 1500);
      }

    } catch (error) {
      // Si el código falla o expiró, extraemos el texto limpio del JSON
      const msjLimpio = obtenerMensajeError(error);
      mostrarMensaje(mensajeEl, msjLimpio, "error");
    } finally {
      // Reactivar botón
      btnVerificar.disabled = false;
      btnVerificar.textContent = "Activar Cuenta";
    }
  });

  // 5. Escuchar el botón de reenviar código
  btnReenviar.addEventListener("click", async () => {
    btnReenviar.disabled = true;
    btnReenviar.textContent = "Enviando nuevo código...";

    try {
      await api.post("/auth/reenviar-verificacion", {
        email: email,
        tipo_usuario: tipo
      });

      mostrarMensaje(mensajeEl, "¡Te hemos enviado un nuevo código de verificación por email!", "exito");
    } catch (error) {
      const msjLimpio = obtenerMensajeError(error);
      mostrarMensaje(mensajeEl, msjLimpio || "No pudimos reenviar el código.", "error");
    } finally {
      // Para evitar abusos del botón, bloqueamos reenvío por 8 segundos antes de reactivarlo
      setTimeout(() => {
        btnReenviar.disabled = false;
        btnReenviar.textContent = "No me llegó el código, reenviar";
      }, 8000);
    }
  });
});

/**
 * Utilidad compartida para renderizar banners de éxito/error
 */
function mostrarMensaje(elemento, texto, tipo) {
  elemento.textContent = texto;
  elemento.classList.remove("mensaje-exito", "mensaje-error");
  elemento.classList.add(tipo === "exito" ? "mensaje-exito" : "mensaje-error");
  elemento.style.display = "block";
}

/**
 * Parsea el error JSON que devuelve api.js para mostrar solo la frase amigable
 */
function obtenerMensajeError(error) {
  try {
    // api.js hace un throw Error(JSON.stringify(error))
    const parsed = JSON.parse(error.message);
    return parsed.detail || error.message;
  } catch (e) {
    return error.message || "Ocurrió un error inesperado.";
  }
}
