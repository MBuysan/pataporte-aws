// maneja la pantalla donde el usuario ingresa el código recibido y su nueva contraseña.

document.addEventListener("DOMContentLoaded", () => {

  const form               = document.getElementById("form-reset");
  const inputCodigo        = document.getElementById("input-codigo");
  const inputPassword      = document.getElementById("input-nueva-password");
  const inputConfirmar     = document.getElementById("input-confirmar-password");
  const btnReset           = document.getElementById("btn-reset");
  const mensajeEl          = document.getElementById("mensaje-reset");
  const indicadoresEl      = document.getElementById("indicadores-password");

  // lee el email de los parámetros de la URL.
  // URLSearchParams parsea la query string de la URL actual.
  // ej: si la URL es "...?email=juan%40email.com", params.get("email") devuelve "juan@email.com"
  const params = new URLSearchParams(window.location.search);
  const email  = params.get("email") || "";

  // escucha cada tecla en el campo de nueva contraseña para mostrar
  // los indicadores de requisitos en tiempo real, sin esperar a que envíe el form, brindadndo buen ux.
  inputPassword.addEventListener("input", () => {
    actualizarIndicadores(inputPassword.value);
  });

  form.addEventListener("submit", async (e) => {
    e.preventDefault();

    const codigo    = inputCodigo.value.trim().toUpperCase(); // normaliza a mayúsculas
    const password  = inputPassword.value;
    const confirmar = inputConfirmar.value;

    // validaciones del lado del cliente — evitan un round-trip innecesario al servidor
    if (!codigo || !password || !confirmar) {
      mostrarMensaje(mensajeEl, "Por favor completá todos los campos.", "error");
      return;
    }

    // valida la contraseña localmente antes de enviar.
    // validarPassword devuelve un string con el error, o null si está bien.
    const errorPassword = validarPassword(password);
    if (errorPassword) {
      mostrarMensaje(mensajeEl, errorPassword, "error");
      return;
    }

    if (password !== confirmar) {
      mostrarMensaje(mensajeEl, "Las contraseñas no coinciden.", "error");
      return;
    }

    btnReset.disabled = true;
    btnReset.textContent = "Guardando...";

    try {
      await api.post("/auth/reset", {
        codigo,
        nueva_password:     password,
        confirmar_password: confirmar,
      });

      mostrarMensaje(mensajeEl, "¡Contraseña actualizada correctamente!", "exito");

      // Redirige al dashboard después de 2 segundos
      setTimeout(() => {
        window.location.href = "dashboard.html";
      }, 2000);

    } catch (error) {
      mostrarMensaje(mensajeEl, error.message, "error");

    } finally {
      btnReset.disabled = false;
      btnReset.textContent = "Guardar nueva contraseña";
    }
  });

});


function mostrarMensaje(elemento, texto, tipo) {
  elemento.textContent = texto;
  elemento.classList.remove("mensaje-exito", "mensaje-error");
  elemento.classList.add(tipo === "exito" ? "mensaje-exito" : "mensaje-error");
  elemento.style.display = "block";
}