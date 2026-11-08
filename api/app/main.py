"""API de Donaria Connect.

Correr (desde la carpeta api/):  uvicorn app.main:app --reload
Documentación interactiva:        http://127.0.0.1:8000/docs
"""
from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import settings
from .db import Database, get_db
from .routers import alertas, auth, donantes, necesidades, reportes

app = FastAPI(
    title="Donaria Connect API",
    version="0.2.0",
    description=(
        "Convocatoria de donantes voluntarios de sangre por olas (3 → 6 → 10 km).\n\n"
        "**Demo con datos ficticios.** Para probar: pide un token en `/auth/token-demo`, "
        "pulsa **Authorize** y pega el token.\n\n"
        "Reglas: ninguna necesidad lleva datos de pacientes; la clínica solo ve cifras; "
        "el DNI se guarda como hash."
    ),
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)

for r in (auth.router, donantes.router, necesidades.router, reportes.router, alertas.router):
    app.include_router(r)


@app.get("/health", tags=["estado"], summary="¿La API está viva?")
def health() -> dict:
    return {"estado": "ok", "fecha_referencia": settings.hoy().isoformat()}


@app.get("/health/db", tags=["estado"], summary="¿La API llega a la base?")
def health_db(db: Database = Depends(get_db)) -> dict:
    fila = db.uno("SELECT DB_NAME() AS base, (SELECT COUNT(*) FROM dbo.DONANTE) AS donantes")
    return {"estado": "ok", **fila}
