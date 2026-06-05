function limpiarDocumento(valor) {
    return valor.replace(/\D/g, "");
}

function validarCedulaUruguaya(cedula) {
    cedula = limpiarDocumento(cedula);

    if (cedula.length < 7 || cedula.length > 8) {
        return false;
    }

    cedula = cedula.padStart(8, "0");

    const pesos = [2, 9, 8, 7, 6, 3, 4];
    let suma = 0;

    for (let i = 0; i < 7; i++) {
        suma += parseInt(cedula[i]) * pesos[i];
    }

    const digito = (10 - (suma % 10)) % 10;

    return digito === parseInt(cedula[7]);
}

function validarRutUruguayo(rut) {
    rut = limpiarDocumento(rut);

    if (rut.length !== 12) {
        return false;
    }

    const pesos = [4, 3, 2, 9, 8, 7, 6, 3, 4, 5, 2];
    let suma = 0;

    for (let i = 0; i < 11; i++) {
        suma += parseInt(rut[i]) * pesos[i];
    }

    const digito = (10 - (suma % 10)) % 10;

    return digito === parseInt(rut[11]);
} 

function actualizarIndicadores(password) {
    const requisitos = [
        { id: "req-largo",     cumple: password.length >= 6 },
        { id: "req-mayuscula", cumple: /[A-Z]/.test(password) },
        { id: "req-minuscula", cumple: /[a-z]/.test(password) },
        { id: "req-numero",    cumple: /\d/.test(password) },
        { id: "req-especial",  cumple: /[!@#$%^&*?]/.test(password) },
    ];
 
    requisitos.forEach(({ id, cumple }) => {
        const el = document.getElementById(id);
        if (!el) return;
        if (password.length === 0) {
            el.classList.remove("cumplido", "pendiente");
        } else if (cumple) {
            el.classList.add("cumplido");
            el.classList.remove("pendiente");
        } else {
            el.classList.add("pendiente");
            el.classList.remove("cumplido");
        }
    });
}

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