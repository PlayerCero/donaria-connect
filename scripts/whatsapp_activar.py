"""Revisa y activa (registra) el número de WhatsApp de la demo con el token del archivo .env.

Uso, desde la raíz del repo con el entorno de la API:
    python scripts/whatsapp_activar.py

Hace dos cosas con la API de Meta (Graph API):
1. Muestra el estado del número (WHATSAPP_PHONE_NUMBER_ID): debe decir CONNECTED para poder enviar.
2. Si no está conectado, lo registra (POST /<id>/register) con un PIN de 6 dígitos
   (WHATSAPP_PIN en .env; si no hay, usa 246810). Es el PIN de verificación en dos pasos del número.
El token nunca se imprime.
"""
from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "api"))

from app.config import settings  # noqa: E402  (carga .env)


def graph(metodo: str, ruta: str, cuerpo: dict | None = None) -> tuple[int, dict]:
    url = f"https://graph.facebook.com/{settings.whatsapp_version}/{ruta}"
    req = urllib.request.Request(url, data=json.dumps(cuerpo).encode() if cuerpo else None, method=metodo)
    req.add_header("Authorization", f"Bearer {settings.whatsapp_token}")
    req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return r.status, json.loads(r.read().decode() or "{}")
    except urllib.error.HTTPError as e:
        try:
            return e.code, json.loads(e.read().decode())
        except ValueError:
            return e.code, {}


def main() -> int:
    pid = settings.whatsapp_phone_number_id
    if not (settings.whatsapp_token and pid):
        print("Falta WHATSAPP_TOKEN o WHATSAPP_PHONE_NUMBER_ID en .env")
        return 1
    s, r = graph("GET", f"{pid}?fields=display_phone_number,verified_name,status,code_verification_status")
    if s != 200:
        err = r.get("error", {})
        print(f"✘ No se pudo leer el número ({s}): {err.get('message', r)}")
        print("  Si dice 'does not exist' o 'missing permissions', el token no tiene acceso a la cuenta de WhatsApp:")
        print("  usa un token de usuario del sistema con acceso a la app y a la cuenta (ver docs/PLAN.md, fase 5).")
        return 1
    print(f"Número {r.get('display_phone_number')} ({r.get('verified_name')}): estado {r.get('status')}")
    if str(r.get("status", "")).upper() == "CONNECTED":
        print("✔ Ya está conectado: se pueden enviar mensajes.")
        return 0
    pin = os.getenv("WHATSAPP_PIN", "246810")
    s, r = graph("POST", f"{pid}/register", {"messaging_product": "whatsapp", "pin": pin})
    if s == 200 and r.get("success"):
        print("✔ Número registrado. En 1 o 2 minutos debería pasar a CONNECTED.")
        return 0
    print(f"✘ No se pudo registrar ({s}): {r.get('error', {}).get('message', r)}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
