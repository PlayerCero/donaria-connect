"""Cliente mínimo de Didit (verificación de identidad: DNI + prueba de vida + comparación de rostro).

Documentación: https://docs.didit.me/sessions-api/create-session
Solo usa la librería estándar. La API nunca recibe la foto ni los datos del DNI: Didit los procesa y
nosotros solo guardamos el id de la sesión y su estado.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import time
import urllib.error
import urllib.request

from .config import Settings, settings

# Estados de Didit que ya no van a cambiar
FINALES = {"Approved", "Declined", "Expired", "Abandoned", "Kyc Expired"}
# Cómo se refleja cada estado en DONANTE.estado_verificacion
A_ESTADO_DONANTE = {"Approved": "verificado", "Declined": "rechazado"}


class ErrorDidit(Exception):
    pass


def configurado(cfg: Settings = settings) -> bool:
    return bool(cfg.didit_api_key and cfg.didit_workflow_id)


def _pedir(metodo: str, ruta: str, cuerpo: dict | None = None, cfg: Settings = settings) -> dict:
    datos = json.dumps(cuerpo).encode() if cuerpo is not None else None
    req = urllib.request.Request(cfg.didit_base_url.rstrip("/") + ruta, data=datos, method=metodo)
    req.add_header("x-api-key", cfg.didit_api_key)
    req.add_header("Content-Type", "application/json")
    req.add_header("Accept", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            texto = r.read().decode()
            return json.loads(texto) if texto else {}
    except urllib.error.HTTPError as e:
        detalle = e.read().decode(errors="replace")[:300]
        raise ErrorDidit(f"Didit respondió {e.code}: {detalle}") from e
    except urllib.error.URLError as e:
        raise ErrorDidit(f"No se pudo conectar con Didit: {e.reason}") from e


def crear_sesion(vendor_data: str, cfg: Settings = settings) -> dict:
    """Crea (o reutiliza, si sigue abierta) la sesión de verificación. Devuelve session_id, url y status."""
    return _pedir("POST", "/v3/session/", {"workflow_id": cfg.didit_workflow_id, "vendor_data": vendor_data,
                                          "language": "es"}, cfg)


def estado_sesion(session_id: str, cfg: Settings = settings) -> str:
    """Estado actual de la sesión ('Not Started', 'In Progress', 'Approved', 'Declined', …)."""
    return str(_pedir("GET", f"/v3/session/{session_id}/decision/", cfg=cfg).get("status", ""))


def _sin_decimales_enteros(d):
    if isinstance(d, dict):
        return {k: _sin_decimales_enteros(v) for k, v in d.items()}
    if isinstance(d, list):
        return [_sin_decimales_enteros(x) for x in d]
    if isinstance(d, float) and d.is_integer():
        return int(d)
    return d


def firma_valida(cuerpo: dict, firma_v2: str, marca_tiempo: str, secreto: str, ahora: float | None = None) -> bool:
    """Valida el webhook como indica Didit: HMAC-SHA256 del JSON canónico, con 5 minutos de tolerancia."""
    if not (firma_v2 and marca_tiempo and secreto):
        return False
    try:
        if abs((ahora or time.time()) - int(marca_tiempo)) > 300:
            return False
    except ValueError:
        return False
    canonico = json.dumps(_sin_decimales_enteros(cuerpo), sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    esperado = hmac.new(secreto.encode(), canonico.encode(), hashlib.sha256).hexdigest()
    return hmac.compare_digest(esperado, firma_v2)


def qr_svg(texto: str) -> str:
    """Código QR en SVG (para abrir el enlace de Didit en el celular)."""
    import qrcode
    import qrcode.image.svg

    img = qrcode.make(texto, image_factory=qrcode.image.svg.SvgPathImage, box_size=8, border=2)
    return img.to_string(encoding="unicode")
