"""Envío de avisos por WhatsApp Cloud API (Meta), con el número de prueba (fase 5).

Reglas de la demo:
- Solo se escribe a los celulares de WHATSAPP_NUMEROS_PRUEBA (los que registraste en Meta como
  destinatarios de prueba). Los 500 donantes ficticios tienen números inventados: a ellos nunca
  se les envía nada; su notificación queda solo en la base, como antes.
- Fuera de una conversación abierta, WhatsApp solo deja enviar plantillas aprobadas. Por defecto
  se usa la plantilla propia (WHATSAPP_PLANTILLA) con tres datos: institución, tipo de sangre y
  distancia. Con la plantilla "hello_world" de Meta se envía sin datos (sirve para probar la conexión).
- El mensaje nunca lleva el nombre del donante ni datos de pacientes.
Documentación: https://developers.facebook.com/docs/whatsapp/cloud-api/guides/send-message-templates
"""
from __future__ import annotations

import json
import urllib.error
import urllib.request

from .config import Settings, settings


class ErrorWhatsApp(Exception):
    pass


def configurado(cfg: Settings = settings) -> bool:
    return bool(cfg.whatsapp_token and cfg.whatsapp_phone_number_id and cfg.whatsapp_numeros_prueba)


def numero_internacional(celular: str) -> str:
    """'987654321' → '51987654321' (Perú). Deja igual un número que ya trae código de país."""
    d = "".join(c for c in str(celular) if c.isdigit())
    return "51" + d if len(d) == 9 and d.startswith("9") else d


def es_de_prueba(celular: str, cfg: Settings = settings) -> bool:
    return numero_internacional(celular) in {numero_internacional(n) for n in cfg.whatsapp_numeros_prueba}


def _cuerpo(destino: str, datos: list[str], cfg: Settings) -> dict:
    plantilla: dict = {"name": cfg.whatsapp_plantilla, "language": {"code": cfg.whatsapp_idioma}}
    if cfg.whatsapp_plantilla != "hello_world" and datos:
        plantilla["components"] = [{"type": "body", "parameters": [{"type": "text", "text": str(t)} for t in datos]}]
    return {"messaging_product": "whatsapp", "to": numero_internacional(destino), "type": "template", "template": plantilla}


def enviar_plantilla(destino: str, datos: list[str], cfg: Settings = settings) -> str:
    """Envía la plantilla y devuelve el id del mensaje (wamid). Lanza ErrorWhatsApp si Meta lo rechaza."""
    url = f"https://graph.facebook.com/{cfg.whatsapp_version}/{cfg.whatsapp_phone_number_id}/messages"
    req = urllib.request.Request(url, data=json.dumps(_cuerpo(destino, datos, cfg)).encode(), method="POST")
    req.add_header("Authorization", f"Bearer {cfg.whatsapp_token}")
    req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            respuesta = json.loads(r.read().decode() or "{}")
    except urllib.error.HTTPError as e:
        try:
            err = json.loads(e.read().decode()).get("error", {})
        except ValueError:
            err = {}
        msg = err.get("message") or f"HTTP {e.code}"
        if e.code == 401 or err.get("code") == 190:
            msg = "El token de WhatsApp venció o no es válido (el temporal dura 24 h). " + msg
        raise ErrorWhatsApp(msg) from e
    except urllib.error.URLError as e:
        raise ErrorWhatsApp(f"No se pudo conectar con Meta: {e.reason}") from e
    mensajes = respuesta.get("messages") or [{}]
    return str(mensajes[0].get("id", ""))
