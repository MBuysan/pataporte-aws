from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import os


from routers import (
    mascotas,
    tutores,
    veterinarios,
    historial,
    tratamientos,
    vacunas,
    pataporte,
    auth,
)

from config.database import engine
from config.migrate import assert_schema_current
from sqlalchemy import text
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager


@asynccontextmanager
async def lifespan(app: FastAPI):
    assert_schema_current(engine)
    os.makedirs("uploads/mascotas", exist_ok=True)
    yield


# crea la instancia principal aplicacion, lo de adentro es mera documentacion
app = FastAPI(
    title="Pataporte API",
    description="API REST para la gestión de salud de mascotas en Uruguay.",
    version="1.0.0",
    lifespan=lifespan,
)

# agrega permisos de donde se ppuede acceder a la api y demas configuraciones
# allow_origins se debe cambiar para produccion
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost",
        "http://localhost:3000",
        "http://127.0.0.1",
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# se monta la carpeta de uploads para servir archivos estaticos, en este caso las fotos de mascotas
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")

# se agregan prefijos a los router y se vinculan a la aplicación
app.include_router(mascotas.router, prefix="/mascotas", tags=["Mascotas"])
app.include_router(tutores.router, prefix="/tutores", tags=["Tutores"])
app.include_router(veterinarios.router, prefix="/veterinarios", tags=["Veterinarios"])
app.include_router(historial.router, prefix="/historial", tags=["Historial"])
app.include_router(tratamientos.router, prefix="/tratamientos", tags=["Tratamientos"])
app.include_router(vacunas.router, prefix="/vacunas", tags=["Vacunas"])
app.include_router(pataporte.router, prefix="/pataporte", tags=["Pataporte"])  
app.include_router(auth.router, prefix="/auth", tags=["Auth"])


# endpoint health check de verificación, convencion para verificar que el servidor esta vivo
@app.get("/", tags=["Health"])
def health_check():
    return {"status": "ok", "app": "Pataporte API v1.0.0"}


@app.get("/health/live", tags=["Health"])
def live():
    return {"status": "ok"}


@app.get("/health/ready", tags=["Health"])
def ready():
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
    except Exception:
        return JSONResponse(status_code=503, content={"status": "unavailable"})
    return {"status": "ready"}
