"""Aplica a la base los scripts de cambios posteriores a 01_*.sql (hoy: 03_fase3_respuestas.sql).

Uso, desde la raíz del repo y con el entorno de la API activo:
    python scripts/migrar.py

Usa la misma conexión que la API (archivo .env). Los scripts son idempotentes: correrlo varias
veces no duplica nada. Separa los lotes por las líneas "GO", igual que SSMS.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "api"))

from app.db import Database  # noqa: E402

SCRIPTS = ["03_fase3_respuestas.sql"]


def lotes(texto: str) -> list[str]:
    partes = re.split(r"^\s*GO\s*$", texto, flags=re.I | re.M)
    return [p.strip() for p in partes if p.strip()]


def main() -> int:
    print("Conectando con la base (si estaba en pausa, Azure tarda hasta 2 minutos en despertarla)...")
    db = Database()
    for nombre in SCRIPTS:
        texto = (RAIZ / "db" / nombre).read_text(encoding="utf-8-sig")
        for lote in lotes(texto):
            if lote.lstrip().upper().startswith("SELECT"):
                for fila in db.consultar(lote):
                    print("   ", fila)
            else:
                db.ejecutar(lote)
        print(f"✔ {nombre} aplicado")
    return 0


if __name__ == "__main__":
    sys.exit(main())
