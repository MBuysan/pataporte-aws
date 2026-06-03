// maneja la pantalla donde el usuario ingresa su email para recibir el código.

// espera a que el HTML esté completamente cargado antes de buscar elementos.
// sin esto, document.getElementById podría devolver null si el script corre antes que el HTML.
document.addEventListener("DOMContentLoaded", () => {

  // obtiene referencias a los elementos del HTML por su id.
  // se guardan en variables para no buscarlo en el DOM cada vez que se necesitan.
  const form = document.getElementById("form-recuperar");
  const inputEmail = document.getElementById("input-email");
  const btnEnviar = document.getElementById("btn-enviar");
  const mensajeEl = document.getElementById("mensaje-recuperar");

  // addEventListener("submit") escucha cuando el usuario envía el formulario
  form.addEventListener("submit", async (e) => {

    // e.preventDefault() evita que el formulario recargue la página,
    // que es el comportamiento por defecto de HTML. Como manejamos el
    // envío con JavaScript, se evita esa recarga.
    e.preventDefault();

    // .trim() elimina espacios en blanco al inicio y al final.
    // Evita que un usuario envíe "  " (solo espacios) como email.
    const email = inputEmail.value.trim();

    if (!email) {
      mostrarMensaje(mensajeEl, "Por favor ingresá tu email.", "error");
      return; // sale de la función y no continúa con el fetch
    }

    // estado del botón
    // se desactiva mientras espera la respuesta para evitar
    // que el usuario haga click varias veces y genere múltiples códigos.
    btnEnviar.disabled = true;
    btnEnviar.textContent = "Enviando...";

    try {
      // api.post viene de api.js — hace el POST a /auth/recuperar
      // y devuelve el JSON de respuesta, o lanza un error.
      await api.post("/auth/recuperar", { email });

      // si llegó acá, el request fue exitoso (status 200).
      mostrarMensaje(
        mensajeEl,
        "Si el email está registrado, recibirás un código en tu correo.",
        "exito"
      );

      // redirige a la pantalla de ingresar código después de 2 segundos,
      // pasando el email como parámetro en la URL para pre-rellenarlo.
      // encodeURIComponent convierte caracteres especiales del email (como @)
      // a su forma válida para url (40% en este caso).
      setTimeout(() => {
        window.location.href = `reset-password.html?email=${encodeURIComponent(email)}`;
      }, 2000);

    } catch (error) {
      // api.js lanza un Error con el mensaje que devolvió la API.
      // error.message contiene el texto del campo "detail" del JSON de error.
      mostrarMensaje(
        mensajeEl,
        "Servidor no disponible, reintente nuevamente en unos minutos.",
        "error"
      );


    } finally {
      // finally se ejecuta siempre, haya o no error.
      // Reactiva el botón para que el usuario pueda intentar de nuevo.
      btnEnviar.disabled = false;
      btnEnviar.textContent = "Enviar código";
    }
  });
});


/**
 * Muestra un mensaje de feedback al usuario en el elemento dado.
 * @param {HTMLElement} elemento - el div donde mostrar el mensaje
 * @param {string} texto         - el mensaje a mostrar
 * @param {"exito"|"error"} tipo - determina el estilo visual
 */
function mostrarMensaje(elemento, texto, tipo) {
  elemento.textContent = texto;

  // Resetea clases anteriores y aplica la nueva.
  // classList.remove quita las dos posibles clases de estado,
  // classList.add agrega solo la que corresponde.
  elemento.classList.remove("mensaje-exito", "mensaje-error");
  elemento.classList.add(tipo === "exito" ? "mensaje-exito" : "mensaje-error");

  // Hace visible el elemento (por defecto está oculto con display:none en el CSS)
  elemento.style.display = "block";
}