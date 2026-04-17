document.addEventListener("DOMContentLoaded", async () => {
  try {
    await api.get("/");
    console.log("API conectada correctamente.");
  } catch (error) {
    console.error("No se pudo conectar con la API:", error.message);
  }
});

//Verifica que la API este disponible al arrancar, inicializa los modulos de cada pantalla
//hay que crear mascotas.js, tutor.js, etc