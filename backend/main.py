from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse


from routers import (
    mascotas,
    tutores,
    veterinarios,
    historial,
    tratamientos,
    vacunas,
    auth,
)

from config.database import create_tables
from contextlib import asynccontextmanager


@asynccontextmanager
async def lifespan(app: FastAPI):
    create_tables()
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
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# se agregan prefijos a los router y se vinculan a la aplicación
app.include_router(mascotas.router, prefix="/mascotas", tags=["Mascotas"])
app.include_router(tutores.router, prefix="/tutores", tags=["Tutores"])
app.include_router(veterinarios.router, prefix="/veterinarios", tags=["Veterinarios"])
app.include_router(historial.router, prefix="/historial", tags=["Historial"])
app.include_router(tratamientos.router, prefix="/tratamientos", tags=["Tratamientos"])
app.include_router(vacunas.router, prefix="/vacunas", tags=["Vacunas"])
app.include_router(auth.router, prefix="/auth", tags=["Auth"])


# endpoint health check de verificación, convencion para verificar que el servidor esta vivo
@app.get("/", tags=["Health"])
def health_check():
    return {"status": "ok", "app": "Pataporte API v1.0.0"}
