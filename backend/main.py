import logging

from fastapi import APIRouter, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from config.settings import settings
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

logging.basicConfig(level=settings.LOG_LEVEL)

# crea la instancia principal aplicacion, lo de adentro es mera documentacion
# las tablas y el seed los crea scripts/init_db.py (se corre antes de cada deploy)
app = FastAPI(
    title="Pataporte API",
    description="API REST para la gestión de salud de mascotas en Uruguay.",
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
)

# agrega permisos de donde se ppuede acceder a la api y demas configuraciones
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in settings.CORS_ORIGINS.split(",") if o.strip()],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# todo cuelga de /api para que CloudFront enrute /api/* al ALB
api = APIRouter(prefix="/api")
api.include_router(mascotas.router, prefix="/mascotas", tags=["Mascotas"])
api.include_router(tutores.router, prefix="/tutores", tags=["Tutores"])
api.include_router(veterinarios.router, prefix="/veterinarios", tags=["Veterinarios"])
api.include_router(historial.router, prefix="/historial", tags=["Historial"])
api.include_router(tratamientos.router, prefix="/tratamientos", tags=["Tratamientos"])
api.include_router(vacunas.router, prefix="/vacunas", tags=["Vacunas"])
api.include_router(pataporte.router, prefix="/pataporte", tags=["Pataporte"])
api.include_router(auth.router, prefix="/auth", tags=["Auth"])


# health check para el ALB: no toca la base de datos
@api.get("/health", tags=["Health"])
def health_check():
    return {"status": "ok"}


app.include_router(api)
