"""API de Donaria Connect.

Correr (desde la carpeta api/):  uvicorn app.main:app --reload
Documentación interactiva:        http://127.0.0.1:8000/docs
"""
from datetime import datetime

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import settings
from .db import Database, get_db
from .routers import alertas, auth, donantes, instituciones, necesidades, reportes, verificacion

app = FastAPI(
    title="Donaria Connect API",
    version="0.4.0",
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

for r in (auth.router, donantes.router, necesidades.router, reportes.router, alertas.router, instituciones.router,
          verificacion.router):
    app.include_router(r)


@app.get("/health", tags=["estado"], summary="¿La API está viva?")
def health() -> dict:
    ahora = datetime.now().replace(microsecond=0)
    hoy = settings.hoy()
    # "ahora" usa la hora real con la fecha de referencia de la demo (la web calcula plazos con esto)
    ahora = ahora.replace(year=hoy.year, month=hoy.month, day=hoy.day)
    from . import didit

    return {"estado": "ok", "fecha_referencia": hoy.isoformat(), "ahora": ahora.isoformat(),
            "didit": didit.configurado()}


@app.get("/health/db", tags=["estado"], summary="¿La API llega a la base?")
def health_db(db: Database = Depends(get_db)) -> dict:
    fila = db.uno("SELECT DB_NAME() AS base, (SELECT COUNT(*) FROM dbo.DONANTE) AS donantes")
    return {"estado": "ok", **fila}
