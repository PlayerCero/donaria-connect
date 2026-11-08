"""Prueba de punta a punta contra la API corriendo y la base real (local o Azure).

Uso (con la API ya levantada en otra terminal):
    python scripts/smoke_test.py                 # contra http://127.0.0.1:8000
    python scripts/smoke_test.py https://...     # contra otra URL

Crea datos FICTICIOS en la base: una necesidad O+ de prueba, sus olas y un donante de prueba.
Solo usa la librería estándar de Python.
"""
from __future__ import annotations

import json
import random
import sys
import urllib.error
import urllib.request

BASE = (sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8000").rstrip("/")
ok_total = 0
fallos = 0


def pedir(metodo: str, ruta: str, cuerpo: dict | None = None, token: str | None = None):
    datos = json.dumps(cuerpo).encode() if cuerpo is not None else None
    req = urllib.request.Request(BASE + ruta, data=datos, method=metodo)
    req.add_header("Content-Type", "application/json")
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            texto = r.read().decode()
            return r.status, (json.loads(texto) if texto else None)
    except urllib.error.HTTPError as e:
        texto = e.read().decode()
        try:
            return e.code, json.loads(texto)
        except ValueError:
            return e.code, texto


def paso(nombre: str, condicion: bool, detalle: object = ""):
    global ok_total, fallos
    if condicion:
        ok_total += 1
        print(f"  ✔ {nombre}  {detalle}")
    else:
        fallos += 1
        print(f"  ✘ {nombre}  {detalle}")


print(f"Probando {BASE}\n")

s, r = pedir("GET", "/health/db")
paso("La API llega a la base", s == 200, r)

s, r = pedir("POST", "/auth/token-demo", {"rol": "clinica", "id": 1})
paso("Token de la clínica (usuario 1)", s == 200, f"institución {r.get('id_institucion') if isinstance(r, dict) else r}")
tk_clinica = r["token"] if s == 200 else None

s, r = pedir("POST", "/necesidades", {"tipo_sangre": "O+", "zona": "Prueba automática", "unidades_meta": 3}, tk_clinica)
paso("Declarar una necesidad O+", s == 201, r)
id_nec = r["id_necesidad"] if s == 201 else None

for n in (1, 2, 3):
    s, r = pedir("POST", f"/necesidades/{id_nec}/olas", None, tk_clinica)
    paso(f"Ola {n}", s == 200, f"{r.get('radio_km')} km → {r.get('donantes_notificados')} notificados" if s == 200 else r)

s, r = pedir("POST", f"/necesidades/{id_nec}/olas", None, tk_clinica)
paso("No existe una cuarta ola (409)", s == 409, r)

s, r = pedir("POST", f"/necesidades/{id_nec}/resultado", {"unidades_obtenidas": 2, "cerrar": True}, tk_clinica)
paso("Registrar 2 unidades y cerrar", s == 204, s)

s, r = pedir("GET", "/reportes", None, tk_clinica)
fila = next((x for x in r if x["id_necesidad"] == id_nec), None) if s == 200 else None
paso("El reporte muestra solo cifras", bool(fila) and "nombres" not in fila, fila)

s, r = pedir("POST", "/auth/token-demo", {"rol": "donante", "id": 48})
tk_donante = r["token"] if s == 200 else None
s, r = pedir("GET", "/donantes/me", None, tk_donante)
paso("Perfil del donante 48", s == 200,
     f"{r.get('tipo_sangre')} · puede donar hoy: {r.get('puede_donar_hoy')} · {r.get('motivo_si_no_puede') or ''}" if s == 200 else r)

s, r = pedir("POST", "/necesidades", {"tipo_sangre": "A+", "unidades_meta": 1}, tk_donante)
paso("Un donante no puede declarar necesidades (403)", s == 403, s)

dni = str(random.randint(90000000, 99999999))  # DNI ficticio, fuera del rango de los 500 de prueba
registro = {"dni": dni, "nombres": "Donante de prueba automática", "sexo": "M", "tipo_sangre": "O-",
            "distrito": "Miraflores", "telefono_whatsapp": "9" + str(random.randint(10000000, 99999999)),
            "acepta_consentimiento": True}
s, r = pedir("POST", "/donantes", registro)
paso("Registrar un donante nuevo", s == 201, f"id {r.get('id_donante')}" if s == 201 else r)

s, r = pedir("POST", "/donantes", registro)
paso("El mismo DNI otra vez se rechaza (409) y crea alerta R4", s == 409, r)

s, r = pedir("POST", "/auth/token-demo", {"rol": "equipo", "id": 0})
s, r = pedir("GET", "/alertas", None, r["token"])
paso("El equipo ve las alertas pendientes", s == 200, f"{len(r)} alertas" if s == 200 else r)

print(f"\n{ok_total} correctos, {fallos} con error.")
sys.exit(1 if fallos else 0)
