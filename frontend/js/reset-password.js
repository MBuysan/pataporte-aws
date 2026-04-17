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

      // Redirige al login después de 2 segundos
      setTimeout(() => {
        window.location.href = "index.html";
      }, 2000);

    } catch (error) {
      mostrarMensaje(mensajeEl, error.message, "error");

    } finally {
      btnReset.disabled = false;
      btnReset.textContent = "Guardar nueva contraseña";
    }
  });


  /**
   * actualiza los indicadores visuales de requisitos de contraseña en tiempo real.
   * cada requisito tiene su propio elemento en el HTML que se marca como cumplido o no.
   * @param {string} password - el valor actual del campo contraseña
   */
  function actualizarIndicadores(password) {
    // cada requisito: [id del elemento HTML, función que evalúa si se cumple]
    const requisitos = [
      { id: "req-largo",    cumple: password.length >= 6 },
      { id: "req-mayuscula", cumple: /[A-Z]/.test(password) },   // test() devuelve true si la regex matchea
      { id: "req-minuscula", cumple: /[a-z]/.test(password) },
      { id: "req-numero",   cumple: /\d/.test(password) },
      { id: "req-especial", cumple: /[!@#$%^&*(),.?]/.test(password) },
    ];

    requisitos.forEach(({ id, cumple }) => {
      const el = document.getElementById(id);
      if (!el) return;

      // agrega o quita la clase "cumplido" según si el requisito se cumple.
      // el CSS se encarga del estilo visual (verde/rojo, tachado, etc.)
      if (cumple) {
        el.classList.add("cumplido");
        el.classList.remove("pendiente");
      } else {
        el.classList.add("pendiente");
        el.classList.remove("cumplido");
      }
    });
  }


  /**
   * valida una contraseña contra los requisitos del sistema.
   * duplica la lógica del backend intencionalmente para dar feedback
   * inmediato sin necesitar un request al servidor.
   * @param {string} password
   * @returns {string|null} mensaje de error, o null si es válida
   */
  function validarPassword(password) {
    if (password.length < 6)
      return "La contraseña debe tener al menos 6 caracteres.";
    if (!/[A-Z]/.test(password))
      return "La contraseña debe tener al menos una mayúscula.";
    if (!/[a-z]/.test(password))
      return "La contraseña debe tener al menos una minúscula.";
    if (!/\d/.test(password))
      return "La contraseña debe tener al menos un número.";
    if (!/[!@#$%^&*?]/.test(password))
      return "La contraseña debe tener al menos un carácter especial. (!@#$%^&*?)";
    return null; 
  }

});


function mostrarMensaje(elemento, texto, tipo) {
  elemento.textContent = texto;
  elemento.classList.remove("mensaje-exito", "mensaje-error");
  elemento.classList.add(tipo === "exito" ? "mensaje-exito" : "mensaje-error");
  elemento.style.display = "block";
}