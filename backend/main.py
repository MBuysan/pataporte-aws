from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from routers import mascotas, tutores, veterinarios, historial, tratamientos, vacunas, pataporte, auth

app = FastAPI(
    title="Pataporte API",
    description="API REST para la gestión de salud de mascotas en Uruguay.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(mascotas.router,      prefix="/mascotas",      tags=["Mascotas"])
app.include_router(tutores.router,       prefix="/tutores",       tags=["Tutores"])
app.include_router(veterinarios.router,  prefix="/veterinarios",  tags=["Veterinarios"])
app.include_router(historial.router,     prefix="/historial",     tags=["Historial"])
app.include_router(tratamientos.router,  prefix="/tratamientos",  tags=["Tratamientos"])
app.include_router(vacunas.router,       prefix="/vacunas",       tags=["Vacunas"])
app.include_router(pataporte.router,     prefix="/pataporte",     tags=["Pataporte"])
app.include_router(auth.router,          prefix="/auth",          tags=["Auth"])


@app.get("/", tags=["Health"])
def health_check():
    return {"status": "ok", "app": "Pataporte API v1.0.0"}