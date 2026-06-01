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